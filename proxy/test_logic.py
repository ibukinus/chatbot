import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# --- MOCK DEPENDENCIES START ---
sys.modules['pandas'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['requests'] = MagicMock()
# --- MOCK DEPENDENCIES END ---

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import main

class TestProxyLogic(unittest.TestCase):

    def setUp(self):
        # Mock data
        main.USERS_MAP = {
            'OpenProject Admin': 'admin.rc',
            'Tanaka Taro': 'tanaka.rc'
        }
        main.PROJECTS_MAP = {
            'デモプロジェクト': '#dev-alerts'
        }
        main.DEFAULT_CHANNEL = '#general'
        main.USER_CACHE = {} # Reset cache
        main.OP_API_KEY = "test_key"
        main.OP_API_URL = "http://mock-op"

    def test_convert_mentions_new_format(self):
        text = '<mention class="mention" data-id="4" data-type="user" data-text="@OpenProject Admin">@OpenProject Admin</mention>&nbsp;\n\nメンション付きコメント'
        expected = "@admin.rc&nbsp;\n\nメンション付きコメント"
        converted = main.convert_mentions(text)
        self.assertEqual(converted, expected)

    def test_convert_mentions_fallback(self):
        text = '<mention class="mention" data-id="5" data-type="user" data-text="@Unknown User">@Unknown User</mention> Hello'
        expected = "@Unknown User Hello"
        converted = main.convert_mentions(text)
        self.assertEqual(converted, expected)

    @patch('main.requests.get')
    def test_get_user_name_success(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 4, "name": "Tanaka Taro"}
        mock_get.return_value = mock_response

        # Test
        name = main.get_user_name("/api/v3/users/4")
        
        # Verify
        self.assertEqual(name, "Tanaka Taro")
        self.assertIn("/api/v3/users/4", main.USER_CACHE)
        mock_get.assert_called_with("http://mock-op/api/v3/users/4", auth=('apikey', 'test_key'), timeout=5)

    @patch('main.requests.get')
    def test_get_user_name_cache(self, mock_get):
        # Pre-fill cache
        main.USER_CACHE["/api/v3/users/4"] = "Cached User"
        
        # Test
        name = main.get_user_name("/api/v3/users/4")
        
        # Verify
        self.assertEqual(name, "Cached User")
        mock_get.assert_not_called()

    @patch('main.requests.get')
    def test_get_user_name_failure(self, mock_get):
        # Mock failure
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Test
        name = main.get_user_name("/api/v3/users/999")
        
        # Verify default
        self.assertEqual(name, "OpenProject")

if __name__ == '__main__':
    unittest.main()
