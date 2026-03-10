import http.server
import json
import os
import re
import socketserver
import threading
import time
import webbrowser
from datetime import datetime, timedelta
import signal
import sys
from dotenv import load_dotenv

import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_sdk.errors import SlackApiError

from core import run_analysis_pipeline

# ---------------------------------------------------------------------------
# Slack API ヘルパー: Rate limit リトライ
# ---------------------------------------------------------------------------

MAX_RETRIES = 3

def slack_api_call(api_method, **kwargs):
    """Slack API をリトライ付きで呼び出す。429 (rate limit) 時に Retry-After を尊重。"""
    for attempt in range(MAX_RETRIES):
        try:
            return api_method(**kwargs)
        except SlackApiError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 5))
                print(f"Rate limited. Retrying after {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(retry_after)
            else:
                raise
    # 最後の試行
    return api_method(**kwargs)


# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からトークンを取得
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

# トークンが設定されているか確認
if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
    print("エラー: SLACK_BOT_TOKEN または SLACK_APP_TOKEN が設定されていません。")
    print(".envファイルに以下の形式で設定してください：")
    print("SLACK_BOT_TOKEN=xoxb-your-token")
    print("SLACK_APP_TOKEN=xapp-your-token")
    sys.exit(1)

# Slackアプリの初期化
app = App(token=SLACK_BOT_TOKEN)

# メンションを抽出する正規表現パターン
mention_pattern = re.compile(r"<@([A-Z0-9]+)>")

# HTTPサーバーのポート
HTTP_PORT = 8000

# データ保存用のグローバル変数
global_data = {
    "channel_name": None,
    "days": 30,
    "timestamp": None,
    "dataframe": None,        # Dot-connect 互換 DataFrame
    "user_cache": {},         # user_id → display_name キャッシュ
    "vis_data": None,         # vis.js 用 JSON (network graph)
}

# 分析パイプラインの排他ロック（同時実行防止）
_analysis_lock = threading.Lock()


# ---------------------------------------------------------------------------
# HTTP サーバー
# ---------------------------------------------------------------------------

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """ダッシュボード配信用 HTTP ハンドラー"""

    def log_message(self, format, *args):
        """リクエストログを標準出力に出力"""
        print(f"[HTTP] {args[0]}" if args else "")

    def do_GET(self):
        if self.path == "/":
            self._serve_template()
        elif self.path == "/vis-data":
            self._serve_vis_data()
        else:
            # セキュリティ: 許可されたパス以外は 404 を返す (.env 漏洩防止)
            self.send_error(404, "Not Found")

    def _serve_template(self):
        """template.html を配信"""
        try:
            with open("template.html", "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            print(f"Error serving template: {e}")
            self.send_error(500, str(e))

    def _serve_vis_data(self):
        """vis.js ネットワークグラフ用 JSON を配信"""
        try:
            vis_data = global_data.get("vis_data")
            if not vis_data:
                self._send_json(404, {"error": "No data available. Run /mention-map first."})
                return

            response_data = {
                **vis_data,
                "channel_name": global_data.get("channel_name", ""),
                "days": global_data.get("days", 30),
                "timestamp": global_data.get("timestamp"),
            }
            self._send_json(200, response_data)
        except Exception as e:
            print(f"Error serving vis-data: {e}")
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status, data):
        """JSON レスポンスを送信するヘルパー"""
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)


class _ReusableTCPServer(socketserver.TCPServer):
    """SO_REUSEADDR を有効にした TCPServer"""
    allow_reuse_address = True


class DashboardServer:
    """ダッシュボード用 HTTP サーバー"""

    def __init__(self, port=HTTP_PORT):
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False

    def start(self):
        """サーバーを起動する（ポートを順に試行、TOCTOU レース回避）"""
        last_err = None
        for port in range(self.port, self.port + 10):
            try:
                self.server = _ReusableTCPServer(("", port), DashboardHandler)
                self.port = port
                break
            except OSError as e:
                last_err = e
                continue
        else:
            raise OSError(f"使用可能なポートが見つかりませんでした: {last_err}")

        try:
            self.running = True
            print(f"サーバーを起動しました: http://localhost:{self.port}")
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
        except Exception as e:
            print(f"サーバー起動エラー: {e}")
            sys.exit(1)

    def stop(self):
        """サーバーを停止する"""
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            print("サーバーを停止しました")


def signal_handler(signum, frame):
    """シグナルハンドラー"""
    print("\nアプリケーションを終了します...")
    if dashboard_server:
        dashboard_server.stop()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Slack コマンドハンドラー
# ---------------------------------------------------------------------------

@app.command("/mention-map")
def mention_map_command(ack, command, client):
    """スラッシュコマンド `/mention-map` のハンドラー"""
    ack()

    channel_id = command["channel_id"]
    user_id = command["user_id"]

    # コマンドのテキストを解析して期間を取得
    text = command.get("text", "").strip()
    days = 30

    if text:
        try:
            days = int(text)
            if days <= 0:
                days = 30
            elif days > 730:
                days = 730
        except ValueError:
            pass

    # 処理を開始する旨のメッセージをエフェメラルとして送信
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=f"過去{days}日間のメンション関係を分析します。DMで進捗状況をお知らせします。",
    )

    # DMで進捗報告用のメッセージを送信
    dm_channel = client.conversations_open(users=user_id)
    dm_channel_id = dm_channel["channel"]["id"]

    progress_msg = client.chat_postMessage(
        channel=dm_channel_id,
        text=f"過去{days}日間のメンション関係分析を開始しました。",
    )
    thread_ts = progress_msg["ts"]

    # 排他ロックで同時実行を防止
    if not _analysis_lock.acquire(blocking=False):
        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text="別の分析が実行中です。完了後に再度お試しください。",
        )
        return

    try:
        # チャンネル内のメッセージを取得（指定した日数分）
        time_from = datetime.now() - timedelta(days=days)
        timestamp_from = time_from.timestamp()

        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text="メッセージ履歴とスレッド応答を取得中...",
        )

        # メッセージ履歴 + スレッド応答を取得
        messages, thread_messages = fetch_messages_with_threads(
            client, channel_id, timestamp_from, thread_ts, dm_channel_id,
        )

        if not messages:
            client.chat_postMessage(
                channel=dm_channel_id, thread_ts=thread_ts,
                text="チャンネル内のメッセージを取得できませんでした。",
            )
            return

        thread_reply_count = sum(len(v) for v in thread_messages.values())
        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text=f"取得完了！メッセージ {len(messages)} 件 + スレッド応答 {thread_reply_count} 件。DataFrame に変換中...",
        )

        # Slack メッセージ → Dot-connect 互換 DataFrame に変換
        user_cache = {}
        df = build_dataframe(
            messages, thread_messages, client, user_cache,
            thread_ts, dm_channel_id,
        )

        if df.empty:
            client.chat_postMessage(
                channel=dm_channel_id, thread_ts=thread_ts,
                text="分析対象のメッセージが見つかりませんでした。",
            )
            return

        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text=f"変換完了！{len(df)} レコードからネットワーク分析を実行中...",
        )

        # Dot-connect 分析パイプライン実行
        vis_data = run_analysis_pipeline(df)
        n_nodes = vis_data["analysis"]["total_nodes"]
        n_edges = vis_data["analysis"]["total_edges"]
        n_communities = len(vis_data["communities"])
        n_hubs = len(vis_data["analysis"]["hubs"])

        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text=(
                f"ネットワーク分析完了！"
                f"ノード {n_nodes} / エッジ {n_edges} / "
                f"コミュニティ {n_communities} / ハブ {n_hubs} 人検出。"
                f"ダッシュボードを準備中..."
            ),
        )

        # チャンネル名を取得
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]

        # グローバル変数にデータを格納
        global_data["channel_name"] = channel_name
        global_data["days"] = days
        global_data["timestamp"] = datetime.now().timestamp()
        global_data["dataframe"] = df
        global_data["user_cache"] = user_cache
        global_data["vis_data"] = vis_data

        browser_url = f"http://localhost:{HTTP_PORT}"

        message = f"""分析が完了しました！ネットワーク分析ダッシュボードを表示するには以下のリンクを開いてください：

<{browser_url}|ブラウザで表示>

このダッシュボードでは：
• *Network ビュー*: メンション関係をネットワークグラフで可視化。ノードクリックで接続関係にドリルダウン
• *Word Cloud ビュー*: 人名をメンション頻度に応じたサイズで表示
• *コミュニティ検出*: Louvain 法で自動グループ分け、ダブルクリックで折りたたみ
• *ハブ検出*: Centrality 分析で組織のキーパーソンを特定
• *PNG ダウンロード*: ツールバーから画像を保存

分析対象チャンネル: <#{channel_id}>
分析結果: ノード {n_nodes} / エッジ {n_edges} / コミュニティ {n_communities} / ハブ {n_hubs} 人

※ ローカルサーバーはこのアプリケーションが実行されている間のみ利用可能です。"""

        client.chat_postMessage(channel=dm_channel_id, text=message)

        # ブラウザを自動的に開く
        webbrowser.open(browser_url)

    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        client.chat_postMessage(channel=dm_channel_id, text=error_message)
        print(error_message)
    finally:
        _analysis_lock.release()


# ---------------------------------------------------------------------------
# Slack API データ取得
# ---------------------------------------------------------------------------

def get_channel_history(
    client, channel_id, timestamp_from, thread_ts=None, dm_channel_id=None,
):
    """チャンネルの履歴を取得（rate limit リトライ付き）"""
    messages = []
    cursor = None
    progress_count = 0
    last_progress_report = 0

    while True:
        try:
            params = {
                "channel": channel_id,
                "limit": 100,
                "oldest": timestamp_from,
            }
            if cursor:
                params["cursor"] = cursor

            response = slack_api_call(client.conversations_history, **params)
            current_batch = response["messages"]
            messages.extend(current_batch)
            progress_count += len(current_batch)

            if (
                thread_ts and dm_channel_id
                and (progress_count - last_progress_report) >= 100
            ):
                client.chat_postMessage(
                    channel=dm_channel_id, thread_ts=thread_ts,
                    text=f"現在 {progress_count} 件のメッセージを取得中...",
                )
                last_progress_report = progress_count

            if not response["has_more"]:
                break

            cursor = response["response_metadata"]["next_cursor"]

        except SlackApiError as e:
            # リトライ後も失敗した場合は中断
            error_msg = f"履歴取得エラー: {e.response['error']}"
            print(error_msg)
            if thread_ts and dm_channel_id:
                client.chat_postMessage(
                    channel=dm_channel_id, thread_ts=thread_ts,
                    text=f"エラー発生: {error_msg}",
                )
            break
        except Exception as e:
            error_msg = f"履歴取得エラー: {str(e)}"
            print(error_msg)
            if thread_ts and dm_channel_id:
                client.chat_postMessage(
                    channel=dm_channel_id, thread_ts=thread_ts,
                    text=f"エラー発生: {error_msg}",
                )
            break

    return messages


def fetch_messages_with_threads(
    client, channel_id, timestamp_from, thread_ts=None, dm_channel_id=None,
):
    """チャンネル履歴とスレッド応答を一括取得する。

    Returns:
        messages: トップレベルのメッセージ一覧
        thread_messages: {parent_ts: [reply, ...]} スレッド応答のマップ
    """
    messages = get_channel_history(
        client, channel_id, timestamp_from, thread_ts, dm_channel_id,
    )

    thread_messages = {}
    thread_count = 0
    threads_to_fetch = [m for m in messages if m.get("reply_count", 0) > 0]

    for idx, msg in enumerate(threads_to_fetch):
        try:
            # ページネーション対応: 長いスレッドの全応答を取得
            all_replies = []
            reply_cursor = None
            while True:
                params = {"channel": channel_id, "ts": msg["ts"]}
                if reply_cursor:
                    params["cursor"] = reply_cursor

                response = slack_api_call(client.conversations_replies, **params)
                # 親メッセージ (ts == msg["ts"]) を除外
                batch = [r for r in response["messages"] if r["ts"] != msg["ts"]]
                all_replies.extend(batch)

                if not response.get("has_more", False):
                    break
                reply_cursor = response["response_metadata"]["next_cursor"]

            if all_replies:
                thread_messages[msg["ts"]] = all_replies
                thread_count += len(all_replies)

        except Exception as e:
            print(f"Warning: Could not fetch thread replies for {msg['ts']}: {e}")

    if thread_ts and dm_channel_id:
        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text=f"スレッド応答 {thread_count} 件を取得しました。",
        )

    return messages, thread_messages


# ---------------------------------------------------------------------------
# Dot-connect 互換データ変換
# ---------------------------------------------------------------------------

def resolve_user(client, user_id, user_cache):
    """Slack user ID からユーザー名を解決（キャッシュ + rate limit リトライ付き）"""
    if user_id in user_cache:
        return user_cache[user_id]
    try:
        user_info = slack_api_call(client.users_info, user=user_id)
        name = user_info["user"]["real_name"]
    except Exception as e:
        print(f"Warning: Could not get user info for {user_id}: {e}")
        name = f"User {user_id}"
    user_cache[user_id] = name
    return name


def build_dataframe(
    messages, thread_messages, client, user_cache,
    thread_ts=None, dm_channel_id=None,
):
    """Slack メッセージを Dot-connect 互換の DataFrame に変換する。

    カラム: date, from_email, from_name, to, cc, subject
    - from_email: Slack user ID
    - to: メンション先 + スレッド参加者 (案B) — "Name <user_id>; ..." 形式
    - cc: リアクションしたユーザー — 同上
    - subject: メッセージ先頭 50 文字
    """
    records = []
    total = len(messages)
    progress_interval = max(1, total // 10)

    # スレッド内の全参加者マップを事前構築
    thread_participants = {}
    for parent_ts, replies in thread_messages.items():
        participants = set()
        parent_msg = next((m for m in messages if m["ts"] == parent_ts), None)
        if parent_msg and parent_msg.get("user"):
            participants.add(parent_msg["user"])
        for reply in replies:
            if reply.get("user"):
                participants.add(reply["user"])
        thread_participants[parent_ts] = participants

    # トップレベルメッセージの変換
    for i, msg in enumerate(messages):
        if thread_ts and dm_channel_id and i > 0 and (i % progress_interval == 0):
            pct = (i / total) * 100
            client.chat_postMessage(
                channel=dm_channel_id, thread_ts=thread_ts,
                text=f"DataFrame 変換中: {i}/{total} ({pct:.0f}%)",
            )

        if msg.get("subtype") == "bot_message" or not msg.get("user"):
            continue

        sender_id = msg["user"]
        sender_name = resolve_user(client, sender_id, user_cache)

        try:
            date_str = datetime.fromtimestamp(float(msg["ts"])).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        text = msg.get("text", "")

        # To: メンション先
        mention_ids = mention_pattern.findall(text)
        to_entries = []
        seen_to = set()
        for mid in mention_ids:
            if mid != sender_id and mid not in seen_to:
                mname = resolve_user(client, mid, user_cache)
                to_entries.append(f"{mname} <{mid}>")
                seen_to.add(mid)

        # To: スレッド参加者（このメッセージがスレッド親の場合）
        if msg["ts"] in thread_participants:
            for tid in thread_participants[msg["ts"]]:
                if tid != sender_id and tid not in seen_to:
                    tname = resolve_user(client, tid, user_cache)
                    to_entries.append(f"{tname} <{tid}>")
                    seen_to.add(tid)

        # CC: リアクションしたユーザー
        cc_entries = []
        seen_cc = set()
        for reaction in msg.get("reactions", []):
            for uid in reaction.get("users", []):
                if uid != sender_id and uid not in seen_to and uid not in seen_cc:
                    rname = resolve_user(client, uid, user_cache)
                    cc_entries.append(f"{rname} <{uid}>")
                    seen_cc.add(uid)

        subject = text[:50].replace("\n", " ") if text else ""

        records.append({
            "date": date_str,
            "from_email": sender_id,
            "from_name": sender_name,
            "to": "; ".join(to_entries),
            "cc": "; ".join(cc_entries),
            "subject": subject,
        })

    # スレッド応答の変換
    for parent_ts, replies in thread_messages.items():
        all_users = thread_participants.get(parent_ts, set())
        parent_msg = next((m for m in messages if m["ts"] == parent_ts), None)
        parent_text = ""
        if parent_msg:
            parent_text = parent_msg.get("text", "")[:50].replace("\n", " ")

        for reply in replies:
            if reply.get("subtype") == "bot_message" or not reply.get("user"):
                continue

            reply_sender_id = reply["user"]
            reply_sender_name = resolve_user(client, reply_sender_id, user_cache)

            try:
                reply_date = datetime.fromtimestamp(float(reply["ts"])).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                continue

            reply_text = reply.get("text", "")

            # To: メンション先
            reply_mention_ids = mention_pattern.findall(reply_text)
            reply_to = []
            seen_to = set()
            for mid in reply_mention_ids:
                if mid != reply_sender_id and mid not in seen_to:
                    mname = resolve_user(client, mid, user_cache)
                    reply_to.append(f"{mname} <{mid}>")
                    seen_to.add(mid)

            # To: スレッド内の他の参加者全員 (案B)
            for tid in all_users:
                if tid != reply_sender_id and tid not in seen_to:
                    tname = resolve_user(client, tid, user_cache)
                    reply_to.append(f"{tname} <{tid}>")
                    seen_to.add(tid)

            # CC: リアクション
            reply_cc = []
            seen_cc = set()
            for reaction in reply.get("reactions", []):
                for uid in reaction.get("users", []):
                    if uid != reply_sender_id and uid not in seen_to and uid not in seen_cc:
                        rname = resolve_user(client, uid, user_cache)
                        reply_cc.append(f"{rname} <{uid}>")
                        seen_cc.add(uid)

            records.append({
                "date": reply_date,
                "from_email": reply_sender_id,
                "from_name": reply_sender_name,
                "to": "; ".join(reply_to),
                "cc": "; ".join(reply_cc),
                "subject": parent_text,
            })

    df = pd.DataFrame(records)

    if thread_ts and dm_channel_id:
        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts,
            text=f"DataFrame 変換完了: {len(df)} レコード生成",
        )

    return df


# ---------------------------------------------------------------------------
# メインアプリ起動
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting application...")

    # シグナルハンドラーを設定（メインスレッドで）
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # サーバーインスタンスを作成
    dashboard_server = DashboardServer(HTTP_PORT)

    try:
        dashboard_server.start()
        print("HTTP server started")

        print("Starting Slack app...")
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
        print("Slack app started successfully")

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
        dashboard_server.stop()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        if dashboard_server:
            dashboard_server.stop()
        sys.exit(1)
