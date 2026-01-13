import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# --- MOCK DEPENDENCIES START ---
sys.modules['pandas'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['requests'] = MagicMock()

# Mock config module
mock_config_module = MagicMock()
mock_config_module.USERS_CSV_PATH = "dummy_users.csv"
mock_config_module.PROJECTS_CSV_PATH = "dummy_projects.csv"
mock_config_module.DEFAULT_CHANNEL = "#general"
mock_config_module.OP_API_KEY = "test_key"
mock_config_module.OP_API_URL = "http://mock-op"
mock_config_module.OP_API_HOST = "localhost"

# We need to make sure 'from .. import config' works in submodules
# Since we are running test_core.py, '..' relative to proxy/core is 'proxy'
# So we need 'proxy.config' to be available.
sys.modules['proxy.config'] = mock_config_module
# --- MOCK DEPENDENCIES END ---

# Adjust path to include the workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from proxy.core.text_processor import convert_mentions
from proxy.core.mapper import mapper
from proxy.services.openproject import op_service

class TestRefactoredLogic(unittest.TestCase):

    def setUp(self):
        # Inject mock data into mapper
        mapper.users_map = {
            'OpenProject Admin': 'admin.rc',
            'Tanaka Taro': 'tanaka.rc'
        }
        mapper.projects_map = {
            'デモプロジェクト': '#dev-alerts'
        }
        # Reset cache
        op_service.user_cache = {}

    def test_convert_mentions_new_format(self):
        text = '<mention class="mention" data-id="4" data-type="user" data-text="@OpenProject Admin">@OpenProject Admin</mention>&nbsp;\n\nメンション付きコメント'
        expected = "@admin.rc&nbsp;\n\nメンション付きコメント"
        converted = convert_mentions(text, mapper)
        self.assertEqual(converted, expected)

    def test_convert_mentions_fallback(self):
        text = '<mention class="mention" data-id="5" data-type="user" data-text="@Unknown User">@Unknown User</mention> Hello'
        expected = "@Unknown User Hello"
        converted = convert_mentions(text, mapper)
        self.assertEqual(converted, expected)

    def test_mapper_routing(self):
        self.assertEqual(mapper.get_channel('デモプロジェクト'), '#dev-alerts')
        self.assertEqual(mapper.get_channel('Unknown Project'), '#general')

    @patch('proxy.services.openproject.requests.get')
    def test_op_service_get_user_name(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 4, "name": "Tanaka Taro"}
        mock_get.return_value = mock_response

        # Test
        name = op_service.get_user_name("/api/v3/users/4")
        
        # Verify
        self.assertEqual(name, "Tanaka Taro")
        self.assertIn("/api/v3/users/4", op_service.user_cache)

if __name__ == '__main__':
    unittest.main()
