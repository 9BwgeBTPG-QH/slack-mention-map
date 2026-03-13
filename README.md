# Slack メンション分析ダッシュボード

Slackチャンネル内のメンション関係をネットワークグラフで可視化するツールです。
メンション・スレッド応答・リアクションからコミュニケーション構造を分析し、コミュニティ検出やキーパーソン特定を行います。

## 特徴

- `/mention-map [日数]` スラッシュコマンドで分析をトリガー（デフォルト30日、最大730日）
- **Network ビュー**: vis.js によるフォース有向ネットワークグラフ
  - ノードクリックで接続関係にドリルダウン（パンくずナビ付き）
  - ダブルクリックでコミュニティの折りたたみ/展開
  - Convex Hull によるコミュニティ境界の描画
- **Word Cloud ビュー**: メンション頻度に応じた人名クラウド
- **コミュニティ検出**: Louvain 法による自動グループ分け
- **ハブ検出**: Degree + Betweenness centrality によるキーパーソン特定
- **Passive Observer 検出**: リアクションのみで参加する人物の検出
- サイドパネルで詳細統計（Mentions / Mentioned / Reactions）
- PNG 画像エクスポート
- HTML エクスポート（スタンドアロン、オフライン閲覧可能）

## アーキテクチャ

```
Slack API (messages + threads + reactions)
    │
    ▼
build_dataframe()        ← Slack → Dot-connect 互換 DataFrame に変換
    │
    ▼
run_analysis_pipeline()  ← NetworkX: グラフ構築 → Louvain → Centrality
    │
    ▼
/vis-data (JSON)         ← HTTP サーバーで配信
    │
    ▼
template.html            ← vis.js + wordcloud2.js で描画
```

### データ変換マッピング

| Slack の概念 | 分析上の概念 | マッピング |
|-------------|-------------|-----------|
| メッセージ投稿者 | from (送信者) | `user_id` → `from_email` |
| @メンション先 | to (受信者) | `<@USER_ID>` をパース |
| スレッド参加者 | to (受信者) | スレッド内の他の投稿者全員 |
| リアクション | cc (受動的参加) | リアクションしたユーザー |

## 必要要件

- Python 3.10以上
- Slack Bot Token (`SLACK_BOT_TOKEN`)
- Slack App Token (`SLACK_APP_TOKEN`)

### Python パッケージ

```
slack-bolt
slack-sdk
python-dotenv
pandas
networkx
```

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/9BwgeBTPG-QH/slack-mention-map.git
cd slack-mention-map
```

2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

## Slack App のセットアップ

### 方法1: App Manifest を使う（推奨）

1. [Slack API](https://api.slack.com/apps) にアクセスし、「Create New App」をクリック
2. 「From an app manifest」を選択
3. ワークスペースを選択
4. リポジトリに含まれる `manifest.json` の内容を貼り付けて「Create」をクリック

### 方法2: 手動で設定する

<details>
<summary>手動設定の手順を表示</summary>

1. [Slack API](https://api.slack.com/apps) にアクセスし、「Create New App」→「From scratch」を選択
2. アプリ名（例: "mention-map"）とワークスペースを選択して「Create App」をクリック

**Bot Token Scopes**（「OAuth & Permissions」セクション）:
- `channels:history` - チャンネルのメッセージ履歴を読み取る
- `channels:read` - チャンネル情報を読み取る
- `chat:write` - メッセージを送信する
- `im:write` - DMを送信する
- `users:read` - ユーザー情報を読み取る
- `commands` - スラッシュコマンドを使用する

**Slash Commands**:
- Command: `/mention-map`
- Short Description: チャンネル内のメンション関係を可視化します
- Usage Hint: [日数]（省略可能）

**Socket Mode**: 「Socket Mode」セクションで有効化
</details>

### トークンの取得

1. 「Socket Mode」→「Enable Socket Mode」をオン
2. 「Basic Information」→「App-Level Tokens」で新しいトークンを生成
   - トークン名を入力（例：`socket-token`）
   - 必要なスコープ（`connections:write`）を選択
3. 生成された App Token（`xapp-` で始まる）をメモ
4. 「Install App」→「Install to Workspace」をクリック
5. Bot User OAuth Token（`xoxb-` で始まる）をメモ

### 環境変数の設定

`.env.example` をコピーしてトークンを設定:

```bash
cp .env.example .env
```

`.env` を編集して実際のトークンを設定:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

分析パラメータのオプションについては `.env.example` 内のコメントを参照してください。

## 使い方

1. アプリケーションを起動:
```bash
python slack-mention-map.py
```

2. Slack で bot を招待してコマンドを実行:
```
/invite @mention-map
/mention-map [日数]
```

3. DM で進捗状況が通知され、分析完了後にブラウザが自動的に開きます

4. ダッシュボードの操作:

| 操作 | 動作 |
|------|------|
| ノードをクリック | 接続関係にドリルダウン + サイドパネル表示 |
| 空白をクリック | 全体表示にリセット |
| ノードをダブルクリック | コミュニティの折りたたみ/展開 |
| 凡例のコミュニティをクリック | コミュニティメンバーを選択してフィット表示 |
| Network / Word Cloud ボタン | ビュー切り替え |
| PNG ボタン | ネットワークグラフを画像としてダウンロード |
| HTML ボタン | ダッシュボードをスタンドアロン HTML としてエクスポート |
| Word Cloud の名前をクリック | Network ビューの該当ノードにジャンプ |

## HTML エクスポート

ツールバーの「HTML」ボタンをクリックすると、現在の分析結果をスタンドアロン HTML ファイルとしてダウンロードできます。

- **オフライン閲覧**: サーバー不要でブラウザで直接開ける（vis.js / wordcloud2.js は CDN 参照）
- **データ内蔵**: 分析 JSON がファイル内に埋め込まれるため、共有・アーカイブに便利
- **ダークテーマ**: ライブビューと同じ Dark Obsidian テーマをインラインスタイルで保持
- **全機能対応**: ノードクリック、コミュニティ折りたたみ、Convex Hull、Word Cloud 切り替えなどすべて動作

ファイル名形式: `slack_network_{チャンネル名}_{日数}days_{日付}.html`

## ファイル構成

```
slack-mention-map/
├── slack-mention-map.py   Slack Bot + HTTP サーバー + データ変換
├── core.py                分析パイプライン (NetworkX + Louvain + Centrality)
├── template.html          ダッシュボード UI (vis.js + wordcloud2.js)
├── manifest.json          Slack App Manifest（セットアップ用）
├── requirements.txt       Python パッケージ一覧
├── .env.example           環境変数テンプレート
└── .env                   Slack トークン + 分析パラメータ（要作成）
```

## 技術スタック

- **バックエンド**: Python, slack-bolt, slack-sdk
- **分析**: NetworkX (グラフ構築, Louvain コミュニティ検出, Centrality), pandas
- **フロントエンド**: vis.js (ネットワークグラフ), wordcloud2.js (ワードクラウド), Canvas API (Convex Hull)
- **サーバー**: Python http.server (Socket Mode)

## トラブルシューティング

| 症状 | 解決方法 |
|------|---------|
| `not_allowed_token_type` エラー | App Token が `xapp-` で始まることを確認 |
| トークン未設定エラー | `.env` ファイルが正しく設定されているか確認 |
| ブラウザが開かない | DM に表示された URL を手動でブラウザにコピー |
| メッセージ取得エラー | bot に `channels:history` 権限が付与されているか確認 |
| 「別の分析が実行中です」 | 前の分析が完了するまで待機してください |
| 分析が遅い | `MENTION_MAP_MIN_EDGE_WEIGHT` を上げてノイズを除去 |

## 注意事項

- ローカルサーバー（デフォルト: ポート 8000）を使用します
- アプリケーション実行中のみダッシュボードにアクセス可能です
- Slack API の Rate Limit に自動対応しますが、大量のメッセージ取得には時間がかかる場合があります
- セキュリティ: HTTP サーバーは `/` と `/vis-data` のみ配信し、`.env` 等のファイルは公開されません
- トークンは安全に管理し、GitHub などに公開しないように注意してください

## ライセンス

MIT
