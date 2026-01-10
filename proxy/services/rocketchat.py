import requests
import logging
import config

logger = logging.getLogger(__name__)

class RocketChatService:
    def send_message(self, channel, text, alias="OpenProject"):
        """Rocket.Chatにメッセージを送信する"""
        if not config.RC_WEBHOOK_URL:
            logger.error("RC_WEBHOOK_URL is not set.")
            return False, "Server misconfiguration"

        payload = {
            "channel": channel,
            "text": text,
            "alias": alias,
            "icon_emoji": ":clipboard:"
        }
        
        try:
            self._post(payload)
            return True, channel
        except requests.exceptions.HTTPError as e:
            # フォールバック処理: 指定チャンネルへの投稿が400エラー（存在しない等）の場合、デフォルトチャンネルに再試行
            if e.response.status_code == 400 and channel != config.DEFAULT_CHANNEL:
                logger.warning(f"Failed to post to {channel}. Retrying with default channel {config.DEFAULT_CHANNEL}...")
                payload["channel"] = config.DEFAULT_CHANNEL
                try:
                    self._post(payload)
                    return True, config.DEFAULT_CHANNEL
                except Exception as retry_e:
                     logger.error(f"Fallback to default channel failed: {retry_e}")
                     return False, str(retry_e)
            else:
                return False, str(e)
        except Exception as e:
            return False, str(e)

    def _post(self, payload):
        """実際のHTTPリクエストを実行"""
        channel_name = payload.get('channel', 'default')
        logger.info(f"Sending to {channel_name}: {payload.get('text')[:50]}...")
        resp = requests.post(config.RC_WEBHOOK_URL, json=payload)
        if resp.status_code != 200:
            logger.error(f"Rocket.Chat Error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()

# グローバルインスタンス
rc_service = RocketChatService()