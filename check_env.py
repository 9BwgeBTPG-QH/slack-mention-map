import os
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# 環境変数を表示
print(f"SLACK_BOT_TOKEN: {os.environ.get('SLACK_BOT_TOKEN')}")
print(f"SLACK_APP_TOKEN: {os.environ.get('SLACK_APP_TOKEN')}")