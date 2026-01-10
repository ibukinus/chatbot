import requests
import logging
import config

logger = logging.getLogger(__name__)

class OpenProjectService:
    def __init__(self):
        # メモリ内キャッシュ
        self.user_cache = {}

    def get_user_name(self, user_href):
        """
        OpenProject APIからユーザー名を取得する。
        API負荷軽減のためキャッシュを使用する。
        """
        if not user_href:
            return "OpenProject"

        # キャッシュを確認
        if user_href in self.user_cache:
            return self.user_cache[user_href]

        # APIキーがない場合は取得不可
        if not config.OP_API_KEY:
            return "OpenProject"

        try:
            # user_href は /api/v3/users/4 のような相対パス
            url = f"{config.OP_API_URL.rstrip('/')}{user_href}"
            
            logger.info(f"Fetching user info from {url}")
            # Docker内部ネットワークからのアクセスのため、Hostヘッダーを明示的に指定
            headers = {'Host': config.OP_API_HOST}
            response = requests.get(url, auth=('apikey', config.OP_API_KEY), headers=headers, timeout=5)
            
            if response.status_code == 200:
                user_data = response.json()
                name = user_data.get('name')
                if name:
                    self.user_cache[user_href] = name
                    return name
            else:
                logger.warning(f"Failed to fetch user {user_href}: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error fetching user info: {e}")

        return "OpenProject"

# グローバルインスタンス
op_service = OpenProjectService()