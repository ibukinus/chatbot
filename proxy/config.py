import os

# Rocket.Chat 設定
RC_WEBHOOK_URL = os.environ.get("RC_WEBHOOK_URL")
RC_WEBHOOK_TOKEN = os.environ.get("RC_WEBHOOK_TOKEN")
DEFAULT_CHANNEL = os.environ.get("DEFAULT_CHANNEL", "#general")

# OpenProject API 設定
OP_API_URL = os.environ.get("OP_API_URL", "http://openproject:80")
OP_API_KEY = os.environ.get("OP_API_KEY")
OP_API_HOST = os.environ.get("OP_API_HOST", "localhost:8080")

# パス設定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_CSV_PATH = os.path.join(BASE_DIR, 'users.csv')
PROJECTS_CSV_PATH = os.path.join(BASE_DIR, 'projects.csv')