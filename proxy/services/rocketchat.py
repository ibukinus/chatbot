import requests
import logging
from typing import Tuple, Dict, Any
import config

logger = logging.getLogger(__name__)


class RocketChatService:
    def send_message(self, channel: str, text: str, alias: str = "OpenProject") -> Tuple[bool, str]:
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
            logger.info(f"Message sent successfully to {channel}")
            return True, channel

        except requests.exceptions.HTTPError as e:
            # フォールバック処理
            if e.response.status_code == 400 and channel != config.DEFAULT_CHANNEL:
                logger.warning(f"Channel {channel} not found (400). Retrying with default channel {config.DEFAULT_CHANNEL}")
                payload["channel"] = config.DEFAULT_CHANNEL
                try:
                    self._post(payload)
                    logger.info(f"Message sent to fallback channel {config.DEFAULT_CHANNEL}")
                    return True, config.DEFAULT_CHANNEL
                except Exception as retry_e:
                    logger.error(f"Fallback to default channel failed: {retry_e}")
                    return False, "Failed to send message to both target and default channel"
            else:
                logger.error(f"HTTP error sending message: {e.response.status_code}")
                return False, "Failed to send message"

        except requests.exceptions.Timeout:
            logger.error("Timeout sending message to Rocket.Chat")
            return False, "Timeout sending message"

        except requests.exceptions.ConnectionError:
            logger.error("Connection error sending message to Rocket.Chat")
            return False, "Connection error"

        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            return False, "Unexpected error"

    def _post(self, payload: Dict[str, Any]) -> None:
        """実際のHTTPリクエストを実行"""
        channel_name = payload.get('channel', 'default')
        logger.debug(f"Sending to {channel_name}: {payload.get('text')[:50]}...")
        resp = requests.post(config.RC_WEBHOOK_URL, json=payload)
        if resp.status_code != 200:
            logger.error(f"Rocket.Chat Error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()