import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock dependencies
sys.modules['pandas'] = MagicMock()
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests
sys.modules['requests.adapters'] = MagicMock()
sys.modules['urllib3'] = MagicMock()
sys.modules['urllib3.util'] = MagicMock()
sys.modules['urllib3.util.retry'] = MagicMock()

sys.path.insert(0, '/home/ibuki/workspace/chatbot')


class TestOpenProjectService(unittest.TestCase):
    def setUp(self):
        from proxy.services.openproject import OpenProjectService
        self.service = OpenProjectService()

    def test_get_user_name_no_href(self):
        """user_hrefがNoneの場合"""
        result = self.service.get_user_name("")
        self.assertEqual(result, "OpenProject")

    def test_get_user_name_cached(self):
        """キャッシュからの取得"""
        self.service.user_cache["/api/v3/users/1"] = "Cached User"
        result = self.service.get_user_name("/api/v3/users/1")
        self.assertEqual(result, "Cached User")

    @patch('proxy.services.openproject.config.OP_API_KEY', None)
    def test_get_user_name_no_api_key(self):
        """APIキーが設定されていない場合"""
        result = self.service.get_user_name("/api/v3/users/1")
        self.assertEqual(result, "OpenProject")


class TestRocketChatService(unittest.TestCase):
    def setUp(self):
        from proxy.services.rocketchat import RocketChatService
        self.service = RocketChatService()

    @patch('proxy.services.rocketchat.config.RC_WEBHOOK_URL', None)
    def test_send_message_no_webhook_url(self):
        """Webhook URLが設定されていない場合"""
        success, message = self.service.send_message("#test", "message")
        self.assertFalse(success)
        self.assertEqual(message, "Server misconfiguration")

    @patch('proxy.services.rocketchat.requests.post')
    @patch('proxy.services.rocketchat.config.RC_WEBHOOK_URL', 'http://rc/webhook')
    def test_send_message_success(self, mock_post):
        """正常にメッセージ送信"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        success, channel = self.service.send_message("#test", "message")
        self.assertTrue(success)
        self.assertEqual(channel, "#test")


if __name__ == '__main__':
    unittest.main()
