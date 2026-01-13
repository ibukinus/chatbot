import os
import logging
import json
from typing import List, Tuple, Optional

# Rocket.Chat 設定
RC_WEBHOOK_URL: Optional[str] = os.environ.get("RC_WEBHOOK_URL")
RC_WEBHOOK_TOKEN: Optional[str] = os.environ.get("RC_WEBHOOK_TOKEN")
DEFAULT_CHANNEL: str = os.environ.get("DEFAULT_CHANNEL", "#general")

# OpenProject API 設定
OP_API_URL: str = os.environ.get("OP_API_URL", "http://openproject:80")
OP_API_KEY: Optional[str] = os.environ.get("OP_API_KEY")
OP_API_HOST: str = os.environ.get("OP_API_HOST", "localhost:8080")

# ロギング設定
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "text")  # "text" or "json"

# パス設定
BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
USERS_CSV_PATH: str = os.path.join(BASE_DIR, 'users.csv')
PROJECTS_CSV_PATH: str = os.path.join(BASE_DIR, 'projects.csv')


class JsonFormatter(logging.Formatter):
    """構造化ログ用のJSONフォーマッター"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """ロギングを設定する"""
    level = getattr(logging, LOG_LEVEL, logging.INFO)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 既存のハンドラをクリア
    root_logger.handlers.clear()

    # コンソールハンドラの設定
    handler = logging.StreamHandler()
    handler.setLevel(level)

    if LOG_FORMAT == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # サードパーティライブラリのログレベル調整
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def validate_config() -> Tuple[bool, List[str]]:
    """
    必須設定項目を検証する

    Returns:
        (is_valid, errors): 検証結果と欠けている項目のリスト
    """
    errors: List[str] = []

    # 必須環境変数のチェック
    if not RC_WEBHOOK_URL:
        errors.append("RC_WEBHOOK_URL is not set")

    if not OP_API_KEY:
        errors.append("OP_API_KEY is not set")

    # CSV ファイルの存在チェック
    if not os.path.exists(USERS_CSV_PATH):
        errors.append(f"Users CSV not found: {USERS_CSV_PATH}")

    if not os.path.exists(PROJECTS_CSV_PATH):
        errors.append(f"Projects CSV not found: {PROJECTS_CSV_PATH}")

    return len(errors) == 0, errors