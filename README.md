# Slack メンション分析ダッシュボード

Slackチャンネル内のメンション関係と投稿頻度をPlotlyで可視化するツールです。
チャンネル内のメンバー間のメンション（@メンション）の関係性をサンキーダイアグラム、投稿頻度をヒートマップとして表示します。
Slack Bolt SDKでSlack APIとの連携を行っています。メンションがない場合は「N/A」として表示されるため、すべての投稿者の活動を把握できます。

## 特徴

- スラッシュコマンドでトリガー(`/mention-map`)
- 数値入力で日数指定可能、標準は30日、最大365日
- 指定したチャンネルの過去のメンション関係・投稿頻度を分析
- ブラウザでインタラクティブなダッシュボード（サンキーダイアグラム＋ヒートマップ）を表示
- メンバー間の関係性や活動傾向を視覚的に把握可能
- メンション頻度に基づいた関係の強さを表現
- 高解像度の画像としてエクスポート可能(PNG画像)
- 使い方ガイドの表示機能
- レスポンシブ対応でどのデバイスでも見やすい

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
- **ヒートマップ機能**:
  - ユーザーごとの日別投稿頻度を色で可視化
  - タブでサンキーダイアグラムとヒートマップを切り替え
  - レスポンシブ対応で見切れ防止

## 必要要件

- Python 3.10以上
- Slack Bot Token (`SLACK_BOT_TOKEN`)
- Slack App Token (`SLACK_APP_TOKEN`)

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/yourusername/slack-mention-map.git
cd slack-mention-map
```

2. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
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
2. 「Basic Information」→「App-Level Tokens」で新しいトークンを生成
   - トークン名を入力（例：`socket-token`）
   - 必要なスコープ（`connections:write`）を選択
3. 生成されたApp Token（`xapp-` で始まる）をメモ

## アプリをワークスペースにインストール

1. 「Install App」セクションで「Install to Workspace」をクリック
2. インストール後、Bot User OAuth Token（`xoxb-` で始まる）をメモ

## 環境変数の設定

### .envファイルを使用（推奨）

プロジェクトのルートディレクトリに`.env`ファイルを作成:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

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

4. ダッシュボードの操作:
- タブで「メンション関係図」と「投稿頻度ヒートマップ」を切り替え
- ノードをドラッグして配置を調整
- ホバーで詳細情報を確認
- 「画像をダウンロード」ボタンで画像として保存
- 「使い方を見る」ボタンでガイドを表示
- グラフが見切れる場合は横スクロールで全体を確認可能

5. SlackのDMに表示される「分析対象チャンネル」はリンク形式（`<#{channel_id}>`）で表示され、クリックでチャンネルにジャンプできます

## 技術スタック

- **バックエンド**: Python, slack-bolt
- **フロントエンド**: HTML, JavaScript, Plotly.js
- **サーバー**: Python HTTPServer
- **データ可視化**: Plotly Sankey, Plotly Heatmap

## トラブルシューティング

### よくある問題と解決方法

1. **Socket Mode接続エラー**
   - 症状: `not_allowed_token_type` エラー
   - 解決: App Tokenが正しい形式（xapp-で始まる）であることを確認

2. **トークン未設定エラー**
   - 症状: `SLACK_BOT_TOKEN` または `SLACK_APP_TOKEN` が設定されていない
   - 解決: `.env`ファイルまたは環境変数が正しく設定されているか確認

3. **ブラウザが開かない**
   - 症状: 分析完了後もブラウザが自動で開かない
   - 解決: 表示されたURLを手動でブラウザにコピー＆ペースト

4. **メッセージ取得エラー**
   - 症状: チャンネルのメッセージを取得できない
   - 解決: botに適切な権限（`channels:history`）が付与されているか確認

5. **グラフが見切れる・表示が崩れる**
   - 症状: サンキーダイアグラムやヒートマップが画面からはみ出す
   - 解決: 横スクロールで全体を確認、またはウィンドウ幅を広げてください。レスポンシブ対応済みです

## ライセンス

MIT

## 注意事項

- ローカルサーバー（デフォルト: ポート8000）を使用します
- アプリケーション実行中のみダッシュボードにアクセス可能です
- Slack APIの制限により、大量のメッセージ取得には時間がかかる場合があります
- ブラウザのポップアップブロックが有効な場合、手動でURLを開く必要があります
- トークンは安全に管理し、GitHubなどに公開しないように注意してください

