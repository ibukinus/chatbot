import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock dependencies
sys.modules['pandas'] = MagicMock()
sys.modules['flask'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['requests.adapters'] = MagicMock()
sys.modules['urllib3'] = MagicMock()
sys.modules['urllib3.util'] = MagicMock()
sys.modules['urllib3.util.retry'] = MagicMock()

sys.path.insert(0, '/home/ibuki/workspace/chatbot')


class TestConfigValidation(unittest.TestCase):
    @patch('proxy.config.os.path.exists')
    @patch('proxy.config.RC_WEBHOOK_URL', 'http://test')
    @patch('proxy.config.OP_API_KEY', 'test_key')
    def test_validate_config_all_valid(self, mock_exists):
        """全ての設定が有効な場合"""
        mock_exists.return_value = True

        from proxy.config import validate_config
        is_valid, errors = validate_config()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    @patch('proxy.config.os.path.exists')
    @patch('proxy.config.RC_WEBHOOK_URL', None)
    @patch('proxy.config.OP_API_KEY', None)
    def test_validate_config_missing_required(self, mock_exists):
        """必須環境変数が欠けている場合"""
        mock_exists.return_value = False

        from proxy.config import validate_config
        is_valid, errors = validate_config()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
