import unittest
from unittest.mock import patch, MagicMock
import sys
import json

# Mock dependencies
sys.modules['pandas'] = MagicMock()
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests
sys.modules['requests.adapters'] = MagicMock()
sys.modules['urllib3'] = MagicMock()
sys.modules['urllib3.util'] = MagicMock()
sys.modules['urllib3.util.retry'] = MagicMock()

sys.path.insert(0, '/home/ibuki/workspace/chatbot')

from proxy.main import app


class TestWebhookEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_webhook_invalid_action(self):
        """サポートされていないアクションの処理"""
        payload = {"action": "invalid_action"}
        response = self.client.post('/webhook',
                                   data=json.dumps(payload),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ignored')

    def test_webhook_no_json(self):
        """JSONなしのリクエスト"""
        response = self.client.post('/webhook')
        self.assertEqual(response.status_code, 400)

    @patch('proxy.services.rocketchat.rc_service.send_message')
    @patch('proxy.services.openproject.op_service.get_user_name')
    @patch('proxy.core.mapper.mapper.get_channel')
    def test_webhook_valid_comment(self, mock_get_channel, mock_get_user, mock_send):
        """有効なコメント投稿の処理"""
        mock_get_channel.return_value = "#test"
        mock_get_user.return_value = "Test User"
        mock_send.return_value = (True, "#test")

        payload = {
            "action": "work_package_comment:comment",
            "activity": {
                "comment": {"raw": "Test comment"},
                "_links": {"user": {"href": "/api/v3/users/1"}},
                "_embedded": {
                    "workPackage": {
                        "id": 123,
                        "subject": "Test WP",
                        "_links": {"project": {"title": "Test Project"}}
                    }
                }
            }
        }

        response = self.client.post('/webhook',
                                   data=json.dumps(payload),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')

    def test_health_endpoint(self):
        """ヘルスチェックエンドポイント"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')

    def test_ready_endpoint(self):
        """レディネスチェックエンドポイント"""
        response = self.client.get('/ready')
        self.assertIn(response.status_code, [200, 503])
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('checks', data)


if __name__ == '__main__':
    unittest.main()
