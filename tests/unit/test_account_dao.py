import unittest
from unittest.mock import Mock, MagicMock, patch
from budget_falcon.account_dao import AccountDAO

class TestAccountDAO(unittest.TestCase):
    """
    AWSアカウント情報を取得するためのDAO（Data Access Object）クラスをテストします。
    """
    def setUp(self):
        self.mock_params = {
            "SPREADSHEET_ID": "test-spreadsheet",
            "SPREADSHEET_RANGE": "test-range",
        }

    @patch('budget_falcon.account_dao.build')
    @patch('budget_falcon.account_dao.load_credentials_from_dict')
    def test_list_data(self, mock_load_creds, mock_build):
        test_values = [
            ["Project A", "C12345678901", "123456789012", "dev", "234567890123", "prod"],
            ["Project B", "G87654321XY", "345678901234", "test"],
            ["Project C", "", "456789012345", "staging", "567890123456", "prod"], # チャンネルIDが空
            ["Project D", "C34567890123", "678901234567"],  # 不完全なAWSアカウント情報
            ["Project E", "C45678901234"],  # チャンネルIDのみ
            ["Project F"],  # 空のアカウント情報
            ["", "C56789012345", "789012345678"],  # 空のプロジェクト名
        ]

        mock_creds = MagicMock()
        mock_load_creds.return_value = (mock_creds, 'test-project-id')

        mock_execute = MagicMock()
        mock_execute.return_value = {
            "values": test_values
        }
        mock_get = Mock()
        mock_get.execute.return_value = mock_execute.return_value # values().get() の戻り値が持つ execute() の戻り値
        mock_get.return_value = mock_get # values().get() の呼び出し自体の戻り値（チェーン継続用）

        mock_values = Mock()
        mock_values.get.return_value = mock_get.return_value # spreadsheets().values() の戻り値が持つ get() の戻り値
        mock_values.return_value = mock_values # spreadsheets().values() の呼び出し自体の戻り値（チェーン継続用）

        mock_spreadsheets = Mock()
        mock_spreadsheets.values.return_value = mock_values.return_value # service.spreadsheets() の戻り値が持つ values() の戻り値
        mock_spreadsheets.return_value = mock_spreadsheets # service.spreadsheets() の呼び出し自体の戻り値（チェーン継続用）

        mock_service = Mock()
        mock_service.spreadsheets.return_value = mock_spreadsheets.return_value # build() の戻り値が持つ spreadsheets() の戻り値
        mock_service.return_value = mock_service # build() の呼び出し自体の戻り値（チェーン継続用）

        mock_build.return_value = mock_service.return_value # build() の最終的な戻り値



        dao = AccountDAO({
            "SPREADSHEET_ID": self.mock_params["SPREADSHEET_ID"],
            "SPREADSHEET_RANGE": self.mock_params["SPREADSHEET_RANGE"],
        })
        items = dao.group_list()

        # 結果の検証
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["name"], "Project A")
        self.assertEqual(items[0]["target_channel"], "C12345678901")
        self.assertEqual(items[0]["accounts"], [
            ("123456789012", "dev"),
            ("234567890123", "prod")
        ])
        self.assertEqual(items[1]["name"], "Project B")
        self.assertEqual(items[1]["target_channel"], "G87654321XY")
        self.assertEqual(items[1]["accounts"], [
            ("345678901234", "test")
        ])


if __name__ == '__main__':
    unittest.main()
