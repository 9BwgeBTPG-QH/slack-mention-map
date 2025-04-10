# Slack Mention Map

Slackチャンネル内のメンション関係をPlotlyで可視化するツールです。
チャンネル内のメンバー間のメンション（@メンション）の関係性をサンキーダイアグラムとして表示します。
Slack Bolt SDKでSlack APIとの連携を行っています。メンションがない場合は「N/A」として表示されるため、すべての投稿者の活動を把握できます。

## 特徴

- スラッシュコマンドでトリガー(`/mention-map`)
- 数値入力で日数指定可能、標準は30日、最大365日
- 指定したチャンネルの過去のメンション関係を分析
- ブラウザでインタラクティブなサンキーダイアグラムで表示
- メンバー間の関係性を視覚的に把握可能
- メンション頻度に基づいた関係の強さを表現
- 高解像度の画像としてエクスポート可能(PNG画像)
- 使い方ガイドの表示機能

## 機能

- **期間指定**: 過去1年以内の任意の期間を指定可能（デフォルト: 30日）
- **ユーザー分類**:
  - 送信者（青色）: 主にメンションを送る人
  - 送受信者（紫色）: メンションを送受信する人
  - 受信者（オレンジ色）: 主にメンションを受ける人
  - メンションなし（グレー）: メンション関係のないメッセージ
- **インタラクティブ機能**:
  - ノードのドラッグ＆ドロップで自由に配置可能
  - ホバーで詳細情報を表示
  - 画像としてダウンロード可能
  - 使い方ガイドの表示（初回表示時および「使い方を見る」ボタンクリック時）

## 必要要件

- Python 3.10以上
- Slack Bot Token (`SLACK_BOT_TOKEN`)
- Slack App Token (`SLACK_APP_TOKEN`)

## インストール

1. 必要なパッケージをインストール:
```bash
pip install slack-bolt plotly
```

## Slack APIでアプリを作成

1. [Slack API](https://api.slack.com/apps) にアクセスし、「Create New App」をクリック
2. 「From scratch」を選択
3. アプリ名（例: "mention-map"）とワークスペースを選択して「Create App」をクリック

## アプリの権限設定

「OAuth & Permissions」セクションで以下のBot Token Scopesを追加:

- `channels:history` - チャンネルのメッセージ履歴を読み取る
- `channels:read` - チャンネル情報を読み取る
- `chat:write` - メッセージを送信する
- `im:write` - DMを送信する
- `users:read` - ユーザー情報を読み取る
- `commands` - スラッシュコマンドを使用する

「Save Changes」をクリックして保存。

## スラッシュコマンドの設定

「Slash Commands」セクションで「Create New Command」をクリック:

- Command: `/mention-map`
- Request URL: Socket Modeを使用するため不要
- Short Description: チャンネル内のメンション関係を可視化します
- Usage Hint: [日数]（省略可能）

## Socket Modeの有効化

1. 「Socket Mode」セクションで「Enable Socket Mode」をオン
2. App Tokenが生成されるのでメモ（`xapp-` で始まる）
3. 「Basic Information」でApp-Level Tokensを確認可能

## アプリをワークスペースにインストール

1. 「Install App」セクションで「Install to Workspace」をクリック
2. インストール後、Bot User OAuth Token（`xoxb-` で始まる）をメモ

## 環境変数の設定

### 一時的な設定

Linux/Mac:
```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_APP_TOKEN="xapp-your-app-token"
```

Windows (コマンドプロンプト):
```cmd
set SLACK_BOT_TOKEN=xoxb-your-bot-token
set SLACK_APP_TOKEN=xapp-your-app-token
```

Windows (PowerShell):
```powershell
$env:SLACK_BOT_TOKEN = "xoxb-your-bot-token"
$env:SLACK_APP_TOKEN = "xapp-your-app-token"
```

### 永続的な環境変数設定（Windows）

1. スタートメニュー → システム環境変数の編集
2. 「環境変数」ボタンをクリック
3. 「新規」をクリックして以下を追加:
   - 変数名: `SLACK_BOT_TOKEN`、値: 取得したBot Token
   - 変数名: `SLACK_APP_TOKEN`、値: 取得したApp Token
4. 「OK」をクリックして保存

## 使い方

1. アプリケーションを起動:
```bash
python slack-mention-map.py
```

2. Slackでbotを招待してコマンドを実行:
```slack
# botをチャンネルに招待
/invite @mention-map

# メンション関係の分析を開始（日数は省略可能）
/mention-map [日数]
```

3. DMで進捗状況が通知され、分析完了後にブラウザが自動的に開きます

4. サンキーダイアグラムを操作:
- ノードをドラッグして配置を調整
- ホバーで詳細情報を確認
- 「画像をダウンロード」ボタンで画像として保存
- 「使い方を見る」ボタンでガイドを表示

## 技術スタック

- **バックエンド**: Python, slack-bolt
- **フロントエンド**: HTML, JavaScript, Plotly.js
- **サーバー**: Python HTTPServer
- **データ可視化**: Plotly Sankey

## ライセンス

MIT

## 注意事項

- ローカルサーバー（デフォルト: ポート8000）を使用します
- アプリケーション実行中のみサンキーダイアグラムにアクセス可能です
- Slack APIの制限により、大量のメッセージ取得には時間がかかる場合があります
- ブラウザのポップアップブロックが有効な場合、手動でURLを開く必要があります

