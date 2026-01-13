import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Dict
import config

logger = logging.getLogger(__name__)


class OpenProjectService:
    user_cache: Dict[str, str]
    session: requests.Session

    def __init__(self) -> None:
        self.user_cache = {}
        # リトライ設定付きセッション
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1  # 1秒、2秒、4秒とリトライ間隔を増やす
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_user_name(self, user_href: str) -> str:
        """
        OpenProject APIからユーザー名を取得する。
        API負荷軽減のためキャッシュを使用する。
        """
        if not user_href:
            return "OpenProject"

        if user_href in self.user_cache:
            return self.user_cache[user_href]

        if not config.OP_API_KEY:
            logger.warning("OP_API_KEY not configured")
            return "OpenProject"

        try:
            url = f"{config.OP_API_URL.rstrip('/')}{user_href}"
            logger.debug(f"Fetching user info from {url}")

            headers = {'Host': config.OP_API_HOST}
            response = self.session.get(
                url,
                auth=('apikey', config.OP_API_KEY),
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                user_data = response.json()
                name = user_data.get('name')
                if name:
                    self.user_cache[user_href] = name
                    logger.debug(f"Cached user: {user_href} -> {name}")
                    return name
                else:
                    logger.warning(f"User {user_href} has no name field")
            else:
                logger.warning(f"Failed to fetch user {user_href}: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching user info: {user_href}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error fetching user info: {user_href}")
        except requests.exceptions.JSONDecodeError:
            logger.error(f"Invalid JSON response for user: {user_href}")
        except Exception as e:
            logger.error(f"Unexpected error fetching user info: {e}")

        return "OpenProject"