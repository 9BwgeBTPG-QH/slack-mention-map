def create_html_template():
    """HTMLテンプレートを生成する関数"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Slackメンション関係 サンキーダイアグラム</title>
    <script src="https://cdn.plot.ly/plotly-2.29.1.min.js"></script>
    <style>
        body {
            font-family: "Hiragino Kaku Gothic Pro", "メイリオ", Meiryo, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1250px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1D9BD1;
            text-align: center;
        }
        .info {
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 4px;
        }
        #sankey {
            width: 100%;
            height: 750px;
        }
        .button-container {
            margin-top: 20px;
            text-align: center;
        }
        .btn {
            background-color: #1D9BD1;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 0 10px;
        }
        .btn:hover {
            background-color: #0F7AB7;
        }
        .btn-help {
            background-color: #5cb85c;
        }
        .btn-help:hover {
            background-color: #449d44;
        }
        .legend {
            display: flex;
            justify-content: center;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 0 15px;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            margin-right: 5px;
            border: 1px solid #ddd;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Slackメンション関係 サンキーダイアグラム</h1>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(100, 149, 237, 0.8);"></div>
                <span>送信者</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(147, 112, 219, 0.8);"></div>
                <span>送受信両方</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(255, 165, 0, 0.8);"></div>
                <span>受信者</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: rgba(180, 180, 180, 0.8);"></div>
                <span>メンションなし</span>
            </div>
        </div>
        <div class="info" id="info">データを読み込み中...</div>
        <div id="sankey"></div>
        <div class="button-container">
            <button id="download" class="btn">画像をダウンロード</button>
            <button id="help" class="btn btn-help">使い方を見る</button>
        </div>
        <div class="footer">
            このサンキーダイアグラムは対話型です。ノードをドラッグして移動したり、ホバーして詳細を表示できます。
        </div>
    </div>

    <script>
        // ヘルプモーダルを表示する関数
        const showGuide = () => {
            const modal = document.createElement('div');
            modal.style.position = 'fixed';
            modal.style.top = '50%';
            modal.style.left = '50%';
            modal.style.transform = 'translate(-50%, -50%)';
            modal.style.background = 'white';
            modal.style.padding = '20px';
            modal.style.borderRadius = '8px';
            modal.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            modal.style.zIndex = '1000';
            modal.style.maxWidth = '600px';
            modal.style.maxHeight = '80vh';
            modal.style.overflow = 'auto';
            
            modal.innerHTML = `
                <h3 style="margin-top:0">サンキーダイアグラムの使い方</h3>
                <p><strong>ノードの色分け</strong>:</p>
                <ul>
                    <li><span style="color:cornflowerblue">青色</span>: 主に送信者（メンションをした人）</li>
                    <li><span style="color:blueviolet">紫色</span>: 送信と受信の両方を行った人</li>
                    <li><span style="color:orange">オレンジ色</span>: 主に受信者（メンションされた人）</li>
                    <li><span style="color:gray">グレー</span>: メンションなし（N/A）</li>
                </ul>
                <p><strong>操作方法</strong>:</p>
                <ul>
                    <li>ノードをドラッグして自由に配置できます</li>
                    <li>マウスを重ねると詳細情報が表示されます</li>
                    <li>「画像をダウンロード」ボタンで保存できます</li>
                </ul>
                <p><strong>ヒント</strong>:</p>
                <ul>
                    <li>見やすい配置になるようノードを整理してみましょう</li>
                    <li>関連性の強いノード同士を近くに配置すると分かりやすくなります</li>
                    <li>特に太い線に注目すると主要なコミュニケーションの流れが分かります</li>
                </ul>
                <button id="close-modal" style="padding:8px 16px; background:#1D9BD1; color:white; border:none; border-radius:4px; cursor:pointer; float:right">閉じる</button>
                <div style="clear:both"></div>
            `;
            
            document.body.appendChild(modal);
            
            document.getElementById('close-modal').addEventListener('click', () => {
                modal.remove();
            });
            
            // 任意の場所をクリックしても閉じられるように
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                }
            });
        };
    
        // データをフェッチする
        fetch('/data')
            .then(response => response.json())
            .then(data => {
                // 情報テキストを更新
                document.getElementById('info').textContent = 
                    `チャンネル: #${data.channel_name} / 期間: 過去${data.days}日間 / 生成日時: ${new Date(data.timestamp * 1000).toLocaleString()}`;
                
                const mentionData = data.mention_data;
                
                // 送信者と受信者のリストを作成
                const senders = new Set();
                const receivers = new Set();
                const links = [];
                const values = [];
                const colors = [];

                // カラーパレットの生成（送信者ごとに異なる色を割り当て）
                function generateColor(index, total) {
                    const hue = (index / total) * 360;
                    return `hsla(${hue}, 70%, 50%, 0.6)`;
                }

                // データの整理
                Object.entries(mentionData).forEach(([sender, receiverData]) => {
                    senders.add(sender);
                    Object.entries(receiverData).forEach(([receiver, count]) => {
                        receivers.add(receiver);
                        links.push([sender, receiver]);
                        values.push(count);
                    });
                });

                // 送信者と受信者の配列を作成
                const senderArray = Array.from(senders);
                const receiverArray = Array.from(receivers);

                // ノードの作成
                const nodes = [
                    ...senderArray.map(name => ({ name: name })),
                    ...receiverArray.map(name => ({ name: name }))
                ];

                // リンクの作成とカラーの割り当て
                const link_data = links.map(([source, target], i) => ({
                    source: senderArray.indexOf(source),
                    target: senderArray.length + receiverArray.indexOf(target),
                    value: values[i],
                    color: generateColor(senderArray.indexOf(source), senderArray.length)
                }));

                // Sankeyダイアグラムのデータ
                const plotData = [{
                    type: "sankey",
                    orientation: "h",
                    node: {
                        pad: 15,
                        thickness: 20,
                        line: {
                            color: "black",
                            width: 0.5
                        },
                        label: nodes.map(n => n.name),
                        x: [...Array(senderArray.length).fill(0), ...Array(receiverArray.length).fill(1)],
                        y: [
                            ...Array(senderArray.length).fill().map((_, i) => i / (senderArray.length - 1 || 1)),
                            ...Array(receiverArray.length).fill().map((_, i) => i / (receiverArray.length - 1 || 1))
                        ],
                        color: nodes.map((_, i) => 
                            i < senderArray.length ? "rgba(100, 149, 237, 0.8)" : "rgba(255, 165, 0, 0.8)"
                        )
                    },
                    link: {
                        source: link_data.map(d => d.source),
                        target: link_data.map(d => d.target),
                        value: link_data.map(d => d.value),
                        color: link_data.map(d => d.color)
                    }
                }];

                // レイアウトの設定
                const layout = {
                    title: {
                        text: `チャンネル #${data.channel_name} のメンション関係（過去${data.days}日間）`,
                        font: {
                            size: 20,
                            family: "Hiragino Kaku Gothic Pro, メイリオ, sans-serif"
                        }
                    },
                    width: 1200,
                    height: 800,
                    font: {
                        size: 12,
                        family: "Hiragino Kaku Gothic Pro, メイリオ, sans-serif"
                    },
                    paper_bgcolor: 'rgba(255,255,255,1)',
                    plot_bgcolor: 'rgba(255,255,255,1)',
                };

                // プロット作成
                Plotly.newPlot('sankey', plotData, layout);
                
                // ダウンロードボタンの設定
                document.getElementById('download').addEventListener('click', function() {
                    Plotly.downloadImage('sankey', {
                        format: 'png',
                        filename: `slack_mentions_${data.channel_name}`,
                        width: 1200,
                        height: 800,
                        scale: 2
                    });
                });
                
                // ヘルプボタンの設定
                document.getElementById('help').addEventListener('click', showGuide);
                
                // 最初にガイドを表示
                setTimeout(showGuide, 1000);
            })
            .catch(error => {
                console.error('データ取得エラー:', error);
                document.getElementById('info').textContent = 'エラー: データの読み込みに失敗しました';
            });
    </script>
</body>
</html>
"""
    # テンプレートファイルを保存
    with open("template.html", "w", encoding="utf-8") as f:
        f.write(html_content)

import base64
import http.server
import json
import os
import re
import socketserver
import tempfile
import threading
import time
import webbrowser
from datetime import datetime, timedelta
import signal
import sys

import plotly.graph_objects as go
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# 環境変数からトークンを取得
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

# Slackアプリの初期化
app = App(token=SLACK_BOT_TOKEN)

# メンションを抽出する正規表現パターン
mention_pattern = re.compile(r"<@([A-Z0-9]+)>")

# HTTPサーバーのポート
HTTP_PORT = 8000

# データ保存用のグローバル変数
global_data = {
    "mention_data": None,
    "channel_name": None,
    "days": 30,
    "timestamp": None,
}


# シンプルなHTTPハンドラー
class SankeyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"Received request for path: {self.path}")  # リクエストパスのログ
        
        if self.path == "/":
            print("Serving HTML template")  # HTMLテンプレート提供のログ
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            # HTMLテンプレートを送信
            try:
                with open("template.html", "rb") as file:
                    self.wfile.write(file.read())
                print("HTML template sent successfully")  # 成功ログ
            except Exception as e:
                print(f"Error serving HTML template: {str(e)}")  # エラーログ

        elif self.path == "/data":
            print("Serving data")  # データ提供のログ
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()

            # メンションデータをJSON形式で送信
            try:
                data = {
                    "mention_data": global_data["mention_data"],
                    "channel_name": global_data["channel_name"],
                    "days": global_data["days"],
                    "timestamp": global_data["timestamp"],
                }
                print(f"Data to be sent: {json.dumps(data, ensure_ascii=False)[:200]}...")  # データの一部をログ出力
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
                print("Data sent successfully")  # 成功ログ
            except Exception as e:
                print(f"Error serving data: {str(e)}")  # エラーログ
        else:
            # その他のファイルはデフォルト処理
            print(f"Serving other file: {self.path}")  # その他のファイルのログ
            super().do_GET()


class SankeyServer:
    def __init__(self, port=HTTP_PORT):
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False

    def find_available_port(self, max_attempts=10):
        """使用可能なポートを探す"""
        for port in range(self.port, self.port + max_attempts):
            try:
                with socketserver.TCPServer(("", port), SankeyHandler) as test_server:
                    test_server.server_close()
                    return port
            except OSError:
                continue
        raise OSError("使用可能なポートが見つかりませんでした")

    def start(self):
        """サーバーを起動する"""
        try:
            self.port = self.find_available_port()
            self.server = socketserver.TCPServer(("", self.port), SankeyHandler)
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
    if sankey_server:
        sankey_server.stop()
    sys.exit(0)


@app.command("/mention-map")
def mention_map_command(ack, command, client):
    """スラッシュコマンド `/mention-map` のハンドラー"""
    ack()  # コマンドを受け付けたことを確認

    channel_id = command["channel_id"]
    user_id = command["user_id"]

    # コマンドのテキストを解析して期間を取得
    text = command.get("text", "").strip()
    days = 30  # デフォルト値

    if text:
        try:
            days = int(text)
            if days <= 0:
                days = 30
            elif days > 365:  # 最大1年に制限
                days = 365
        except ValueError:
            # 数値でない場合はデフォルト値を使用
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

    try:
        # チャンネル内のメッセージを取得（指定した日数分）
        time_from = datetime.now() - timedelta(days=days)
        timestamp_from = time_from.timestamp()

        # 進捗報告を開始
        client.chat_postMessage(
            channel=dm_channel_id, thread_ts=thread_ts, text="メッセージ履歴を取得中..."
        )

        # メッセージ履歴を取得（進捗報告機能付き）
        result = get_channel_history(
            client, channel_id, timestamp_from, thread_ts, dm_channel_id
        )

        if not result:
            client.chat_postMessage(
                channel=dm_channel_id,
                thread_ts=thread_ts,
                text=f"チャンネル内のメッセージを取得できませんでした。",
            )
            return

        # 進捗報告
        client.chat_postMessage(
            channel=dm_channel_id,
            thread_ts=thread_ts,
            text=f"取得完了！合計 {len(result)} 件のメッセージを取得しました。メンション関係を分析中...",
        )

        # メンション関係を分析
        mention_data = analyze_mentions(result, client, thread_ts, dm_channel_id)

        # 進捗報告
        client.chat_postMessage(
            channel=dm_channel_id,
            thread_ts=thread_ts,
            text="分析完了！サンキーダイアグラムを準備中...",
        )

        # チャンネル名を取得
        channel_info = client.conversations_info(channel=channel_id)
        channel_name = channel_info["channel"]["name"]

        # グローバル変数にデータを格納
        global_data["mention_data"] = mention_data
        global_data["channel_name"] = channel_name
        global_data["days"] = days
        global_data["timestamp"] = datetime.now().timestamp()

        # ブラウザでサンキーダイアグラムを表示するURLを生成
        browser_url = f"http://localhost:{HTTP_PORT}"

        # 完了メッセージ
        message = f"""
分析が完了しました！サンキーダイアグラムを表示するには以下のリンクを開いてください：

<{browser_url}|ブラウザでサンキーダイアグラムを表示>

このブラウザでは：
• ダイアグラムを自由に操作できます（ノードのドラッグ、ホバー表示など）
• 「画像をダウンロード」ボタンから高解像度画像を保存できます
• 保存した画像をSlackにアップロードして共有できます

ブラウザが自動的に開かない場合は、上記のリンクをクリックするか、手動でブラウザを開いて次のURLにアクセスしてください：
{browser_url}

※ ローカルサーバーはこのアプリケーションが実行されている間のみ利用可能です。
"""
        client.chat_postMessage(channel=dm_channel_id, text=message)

        # ブラウザを自動的に開く
        webbrowser.open(browser_url)

    except Exception as e:
        error_message = f"エラーが発生しました: {str(e)}"
        client.chat_postMessage(channel=dm_channel_id, text=error_message)
        print(error_message)


def get_channel_history(
    client, channel_id, timestamp_from, thread_ts=None, dm_channel_id=None
):
    """チャンネルの履歴を取得、進捗も報告"""
    messages = []
    cursor = None
    progress_count = 0
    last_progress_report = 0

    while True:
        try:
            params = {
                "channel": channel_id,
                "limit": 100,  # 一度に取得する最大メッセージ数
                "oldest": timestamp_from,
            }

            if cursor:
                params["cursor"] = cursor

            response = client.conversations_history(**params)
            current_batch = response["messages"]
            messages.extend(current_batch)
            progress_count += len(current_batch)

            # 進捗報告（100件ごと）
            if (
                thread_ts
                and dm_channel_id
                and (progress_count - last_progress_report) >= 100
            ):
                client.chat_postMessage(
                    channel=dm_channel_id,
                    thread_ts=thread_ts,
                    text=f"現在 {progress_count} 件のメッセージを取得中...",
                )
                last_progress_report = progress_count

            if not response["has_more"]:
                break

            cursor = response["response_metadata"]["next_cursor"]

        except Exception as e:
            error_msg = f"履歴取得エラー: {str(e)}"
            print(error_msg)
            if thread_ts and dm_channel_id:
                client.chat_postMessage(
                    channel=dm_channel_id,
                    thread_ts=thread_ts,
                    text=f"エラー発生: {error_msg}",
                )
            break

    return messages


def analyze_mentions(messages, client, thread_ts=None, dm_channel_id=None):
    """メッセージからメンション関係を分析、進捗も報告"""
    mention_count = {}  # {送信者: {メンション先: 回数}}

    # ユーザー情報のキャッシュ
    user_cache = {}
    total_messages = len(messages)
    progress_interval = max(1, total_messages // 10)  # 10%ごとに進捗報告

    for i, message in enumerate(messages):
        # 進捗報告
        if thread_ts and dm_channel_id and (i % progress_interval == 0):
            progress_percent = (i / total_messages) * 100
            client.chat_postMessage(
                channel=dm_channel_id,
                thread_ts=thread_ts,
                text=f"分析進捗: {i}/{total_messages} メッセージ処理済み ({progress_percent:.1f}%)",
            )

        # botのメッセージは無視
        if message.get("subtype") == "bot_message" or not message.get("user"):
            continue

        sender_id = message["user"]

        # ユーザー名をキャッシュから取得（なければAPI呼び出し）
        if sender_id not in user_cache:
            try:
                user_info = client.users_info(user=sender_id)
                user_cache[sender_id] = user_info["user"]["real_name"]
            except:
                user_cache[sender_id] = f"User {sender_id}"

        sender_name = user_cache[sender_id]

        # このユーザーのメンションカウントを初期化
        if sender_name not in mention_count:
            mention_count[sender_name] = {}

        # メッセージ本文からメンションを抽出
        if "text" in message:
            mentions = mention_pattern.findall(message["text"])

            # メンションがない場合はN/Aを追加
            if not mentions:
                if "N/A" not in mention_count[sender_name]:
                    mention_count[sender_name]["N/A"] = 0
                mention_count[sender_name]["N/A"] += 1
            else:
                for mention_id in mentions:
                    # メンション先のユーザー名を取得
                    if mention_id not in user_cache:
                        try:
                            user_info = client.users_info(user=mention_id)
                            user_cache[mention_id] = user_info["user"]["real_name"]
                        except:
                            user_cache[mention_id] = f"User {mention_id}"

                    mention_name = user_cache[mention_id]

                    # メンションカウントを更新
                    if mention_name not in mention_count[sender_name]:
                        mention_count[sender_name][mention_name] = 0
                    mention_count[sender_name][mention_name] += 1

    # 最終進捗報告
    if thread_ts and dm_channel_id:
        client.chat_postMessage(
            channel=dm_channel_id,
            thread_ts=thread_ts,
            text=f"分析完了: 全 {total_messages} メッセージの処理が終了しました！",
        )

    return mention_count


# メインアプリ起動
if __name__ == "__main__":
    print("Starting application...")
    
    # グローバルデータの初期状態を確認
    print("Initial global data state:", global_data)
    
    # HTMLテンプレートを生成
    create_html_template()
    print("HTML template created")

    # シグナルハンドラーを設定（メインスレッドで）
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # サーバーインスタンスを作成
    sankey_server = SankeyServer(HTTP_PORT)
    
    try:
        # サーバーを起動
        sankey_server.start()
        print("HTTP server started")

        # Slackアプリを起動
        print("Starting Slack app...")
        handler = SocketModeHandler(app, SLACK_APP_TOKEN)
        handler.start()
        print("Slack app started successfully")

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
        sankey_server.stop()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        if sankey_server:
            sankey_server.stop()
        sys.exit(1)
