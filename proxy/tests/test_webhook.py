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
                        "_links": {
                            "project": {
                                "href": "/api/v3/projects/demo-project",
                                "title": "Test Project"
                            }
                        }
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

    @patch('proxy.services.rocketchat.rc_service.send_message')
    @patch('proxy.services.openproject.op_service.get_user_name')
    @patch('proxy.core.mapper.mapper.get_channel')
    def test_webhook_includes_url_with_project(self, mock_get_channel, mock_get_user, mock_send):
        """正常処理でワークパッケージURL（プロジェクトパス付き）が含まれることを確認"""
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
                        "_links": {
                            "project": {
                                "href": "/api/v3/projects/demo-project",
                                "title": "Test Project"
                            }
                        }
                    }
                }
            }
        }

        response = self.client.post('/webhook',
                                   data=json.dumps(payload),
                                   content_type='application/json')

        # RocketChatService.send_message が呼び出される際の引数を検証
        args = mock_send.call_args[0]
        channel, message_text, alias = args

        # プロジェクトパス付きURLが含まれていることを確認
        self.assertIn("/projects/demo-project/work_packages/123", message_text)
        self.assertIn("OpenProjectで表示", message_text)
        self.assertEqual(response.status_code, 200)

    @patch('proxy.services.rocketchat.rc_service.send_message')
    @patch('proxy.services.openproject.op_service.get_user_name')
    @patch('proxy.core.mapper.mapper.get_channel')
    def test_webhook_includes_url_fallback(self, mock_get_channel, mock_get_user, mock_send):
        """project.hrefが無い場合、シンプルなURL形式にフォールバックすることを確認"""
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
                        "_links": {"project": {"title": "Test Project"}}  # href なし
                    }
                }
            }
        }

        response = self.client.post('/webhook',
                                   data=json.dumps(payload),
                                   content_type='application/json')

        args = mock_send.call_args[0]
        channel, message_text, alias = args

        # シンプルなURL形式が含まれていることを確認
        self.assertIn("/work_packages/123", message_text)
        self.assertNotIn("/projects/", message_text)
        self.assertIn("OpenProjectで表示", message_text)
        self.assertEqual(response.status_code, 200)

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
