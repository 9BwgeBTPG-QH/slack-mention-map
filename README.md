# Slack メンション分析ダッシュボード

Slackチャンネル内のメンション関係をネットワークグラフで可視化するツールです。
メッセージの @メンション・スレッド応答・リアクションの3種類のインタラクションからコミュニケーション構造を分析し、コミュニティ検出やキーパーソン特定を行います。

**[デモを見る（サンプルデータ）](https://9BwgeBTPG-QH.github.io/slack-mention-map/)** — 架空のチームデータで実際のダッシュボードを操作できます。

## 特徴

- `/mention-map [日数]` スラッシュコマンドで分析をトリガー（デフォルト30日、最大730日）
- DMスレッドでリアルタイムに進捗通知、完了後ブラウザが自動で開く
- 同時実行防止の排他ロック付き（1チャンネルずつ分析）

### ダッシュボード

- **Network ビュー**: vis.js による物理シミュレーション付きネットワークグラフ
  - ノードクリックで接続関係にドリルダウン（パンくずナビ付き）
  - ダブルクリックでコミュニティ単位の折りたたみ/展開
  - Convex Hull（凸包）によるコミュニティ境界の自動描画
  - ノードサイズは活動量（送信+受信+リアクション数）に比例
- **Word Cloud ビュー**: メンション頻度に応じた人名ワードクラウド
  - 名前クリックで Network ビューの該当ノードにジャンプ
- **サイドパネル**: ノード選択時に表示される詳細統計
  - 送信/受信/リアクション数
  - Mention先・Reaction先・受信元の内訳（クリックで遷移可能）
  - Hub / Passive Observer バッジ表示
- **凡例パネル**: コミュニティ一覧（メンバー名のプレビュー付き）と Passive Observer 一覧
  - クリックでコミュニティメンバーにズーム
- **エクスポート**: PNG 画像 / スタンドアロン HTML

### 分析機能

- **コミュニティ検出**: Louvain 法による自動グループ分け
- **ハブ検出**: Degree centrality + Betweenness centrality のスコアで上位20名を特定
- **Passive Observer 検出**: メッセージを送らずリアクションのみで参加する人物を検出（CC比率が閾値以上）

## アーキテクチャ

```
Slack API (messages + threads + reactions)
    │
    ▼
build_dataframe()        ← Slack メッセージを DataFrame に変換
    │                       (メンション→to, スレッド参加→to, リアクション→cc)
    ▼
run_analysis_pipeline()  ← NetworkX: グラフ構築 → Louvain → Centrality
    │
    ▼
/vis-data (JSON)         ← ローカル HTTP サーバーで配信
    │
    ▼
template.html            ← vis.js + wordcloud2.js で描画
```

### データ変換マッピング

Slack のメッセージデータをメール風の DataFrame 構造に変換し、ネットワーク分析に利用します。

| Slack の概念 | 分析上の概念 | マッピング |
|-------------|-------------|-----------|
| メッセージ投稿者 | from (送信者) | `user_id` → `from_email` |
| @メンション先 | to (受信者) | `<@USER_ID>` を正規表現でパース |
| スレッド参加者 | to (受信者) | スレッド内の他の投稿者全員（親メッセージ含む） |
| リアクション | cc (受動的参加) | リアクションしたユーザー（to と重複しないもの） |
| メッセージ先頭50文字 | subject | メッセージプレビュー |

## 必要要件

- Python 3.10以上
- Slack Bot Token (`SLACK_BOT_TOKEN`)
- Slack App Token (`SLACK_APP_TOKEN`) — Socket Mode 用

## インストール

```bash
git clone https://github.com/9BwgeBTPG-QH/slack-mention-map.git
cd slack-mention-map
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
- `channels:history` — チャンネルのメッセージ履歴を読み取る
- `channels:read` — チャンネル情報を読み取る
- `chat:write` — メッセージを送信する
- `im:write` — DMを送信する
- `users:read` — ユーザー情報を読み取る
- `commands` — スラッシュコマンドを使用する

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

```bash
cp .env.example .env
```

`.env` を編集して実際のトークンを設定:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

分析パラメータのカスタマイズについては `.env.example` 内のコメントを参照してください。

## 使い方

### 起動

```bash
python slack-mention-map.py
```

ローカル HTTP サーバーがポート 8000 で起動します（8000 が使用中の場合は 8009 まで順に試行）。

### 分析の実行

1. Slack で分析したいチャンネルに bot を招待:
   ```
   /invite @mention-map
   ```

2. スラッシュコマンドを実行:
   ```
   /mention-map        # デフォルト: 過去30日間
   /mention-map 90     # 過去90日間
   /mention-map 365    # 過去1年間（最大730日）
   ```

3. DMスレッドで進捗がリアルタイム通知されます:
   - メッセージ取得 → スレッド応答取得 → DataFrame変換 → ネットワーク分析
   - 完了後、ブラウザが自動で開きダッシュボードが表示されます

### ダッシュボード操作

| 操作 | 動作 |
|------|------|
| ノードをクリック | 接続関係にドリルダウン + サイドパネルで詳細表示 |
| 空白をクリック | 全体表示にリセット |
| ノードをダブルクリック | コミュニティを1つのクラスターノードに折りたたみ/展開 |
| 凡例のコミュニティをクリック | そのコミュニティのメンバーにズーム |
| 凡例の Passive Observer をクリック | 該当ノードにフォーカス |
| Network / Word Cloud ボタン | ビュー切り替え |
| Word Cloud の名前をクリック | Network ビューに切り替わり該当ノードにジャンプ |
| PNG ボタン | ネットワークグラフを画像としてダウンロード |
| HTML ボタン | ダッシュボード全体をスタンドアロン HTML としてエクスポート |

## エクスポート

### PNG

ツールバーの「PNG」ボタンで現在のネットワークグラフをキャンバスの状態のまま画像保存します。

ファイル名: `slack_network_{チャンネル名}_{日数}days_{日付}.png`

### HTML

ツールバーの「HTML」ボタンで分析結果をスタンドアロン HTML ファイルとしてダウンロードできます。

- **共有・アーカイブ向け**: 分析 JSON がファイル内に埋め込まれるため、サーバー不要で共有可能
- **全機能対応**: ノードクリック、コミュニティ折りたたみ、Convex Hull、Word Cloud 切り替えなどすべて動作
- **ダークテーマ**: ライブビューと同じ Dark Obsidian テーマを保持
- vis.js / wordcloud2.js は CDN 参照のため、閲覧時にインターネット接続が必要です

ファイル名: `slack_network_{チャンネル名}_{日数}days_{日付}.html`

## 分析パラメータ

`.env` で以下のパラメータを調整できます（すべてオプション）。

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `MENTION_MAP_CC_THRESHOLD` | `0.30` | Passive Observer 検出閾値。CC数 / 総メッセージ数がこの値以上で検出 |
| `MENTION_MAP_MIN_EDGE_WEIGHT` | `1` | エッジ表示の最小重み。大きくするとノイズが減る |
| `MENTION_MAP_HUB_DEGREE_W` | `0.5` | ハブスコアの Degree centrality の重み |
| `MENTION_MAP_HUB_BETWEEN_W` | `0.5` | ハブスコアの Betweenness centrality の重み |
| `MENTION_MAP_COMPANY_DOMAINS` | （なし） | 社内ドメインリスト（カンマ区切り）。未設定時は全員を社内扱い |

## ファイル構成

```
slack-mention-map/
├── slack-mention-map.py   Slack Bot (Socket Mode) + HTTP サーバー + データ変換
├── core.py                分析パイプライン (NetworkX + Louvain + Centrality)
├── template.html          ダッシュボード UI (vis.js + wordcloud2.js)
├── manifest.json          Slack App Manifest（セットアップ用）
├── requirements.txt       Python パッケージ一覧
├── .env.example           環境変数テンプレート
└── .env                   Slack トークン + 分析パラメータ（要作成、git管理外）
```

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Slack 連携 | slack-bolt, slack-sdk（Socket Mode 接続） |
| データ変換 | pandas（DataFrame） |
| ネットワーク分析 | NetworkX（有向グラフ構築, Louvain コミュニティ検出, Degree/Betweenness centrality） |
| フロントエンド | vis.js（ネットワークグラフ + Barnes-Hut 物理シミュレーション）, wordcloud2.js |
| 可視化補助 | Canvas API（Convex Hull 描画, Graham Scan アルゴリズム） |
| HTTP サーバー | Python http.server（ローカル配信専用） |

## トラブルシューティング

| 症状 | 解決方法 |
|------|---------|
| `not_allowed_token_type` エラー | App Token が `xapp-` で始まることを確認 |
| トークン未設定エラー | `.env` ファイルに `SLACK_BOT_TOKEN` と `SLACK_APP_TOKEN` が設定されているか確認 |
| ブラウザが開かない | DM に表示された `http://localhost:8000` を手動でブラウザに入力 |
| メッセージ取得エラー | Bot に `channels:history` 権限があるか確認。チャンネルに Bot を招待しているか確認 |
| 「別の分析が実行中です」 | 前の分析が完了するまで待機（排他ロックにより同時実行不可） |
| Rate Limit エラー | 自動リトライ（最大3回、`Retry-After` ヘッダーを尊重）で対応済み。大量メッセージの場合は時間がかかります |
| ポート 8000 が使用中 | 自動的に 8001〜8009 を順に試行します |
| 分析結果のノイズが多い | `MENTION_MAP_MIN_EDGE_WEIGHT` の値を上げてエッジを間引く |

## 注意事項

- HTTP サーバーは `/` と `/vis-data` のみ配信し、それ以外のパスはすべて 404 を返します（`.env` 等のファイル漏洩を防止）
- アプリケーション実行中のみダッシュボードにアクセス可能です（結果を保存するには HTML エクスポートを利用してください）
- 200ノードを超える大規模グラフでは、Betweenness centrality を k=100 のサンプリングで近似計算します
- トークンは安全に管理し、`.env` ファイルを GitHub などに公開しないよう注意してください

## ライセンス

MIT
