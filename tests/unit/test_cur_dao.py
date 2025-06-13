import unittest
from unittest.mock import MagicMock, patch
from budget_falcon.cur_dao import CurDAO


class TestCurDAO(unittest.TestCase):
    """
    Athenaクエリを利用したCURデータ取得DAO（CurDAO）のfetchメソッドをテストします。
    テスト内容:
    - test_fetch_query_result_conversion:
        - Athenaクエリの実行から結果取得までの一連の流れをモック化し、正常系のデータ変換処理を検証します。
        - Athenaのクエリ結果（ヘッダー＋2行のデータ）を返し、fetch()が正しくデータをパースし、コスト項目をfloat型に変換して返すことを確認します。
        - クエリ文字列にアカウントIDや日付範囲などのパラメータが正しく含まれているかも検証します。
    - test_fetch_with_empty_results:
        - Athenaクエリの結果がヘッダーのみ（データ行なし）の場合、fetch()が空リストを返すことを検証します。
    """
    def setUp(self):
        self.mock_params = {
            "AWS_REGION": "ap-northeast-1",
            "ATHENA_DATABASE": "test-db",
            "ATHENA_TABLE": "test-table",
            "ATHENA_OUTPUT_URI": "s3://test-bucket/output/",
            "ATHENA_LINE_ITEM_TYPES": ["Usage", "DiscountedUsage"],
            "QUERY_DAYS_RANGE": 15,  # 7-30日の範囲内の値を使用
        }

    @patch('boto3.client')
    def test_fetch_query_result_conversion(self, mock_boto3):
        # モックの設定
        mock_athena = MagicMock()
        mock_boto3.return_value = mock_athena

        # Athenaの実行IDを返す
        mock_athena.start_query_execution.return_value = {
            "QueryExecutionId": "test-execution-id"
        }

        # クエリの状態を成功として返す
        mock_athena.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
        }

        # テストデータ (Athenaの結果形式)
        test_rows = [
            # ヘッダー行
            {"Data": [
                {"VarCharValue": "date"},
                {"VarCharValue": "account_id"},
                {"VarCharValue": "service"},
                {"VarCharValue": "cost"}
            ]},
            # データ行
            {"Data": [
                {"VarCharValue": "2025-05-15"},
                {"VarCharValue": "123456789012"},
                {"VarCharValue": "AmazonEC2"},
                {"VarCharValue": "123.45"}
            ]},
            {"Data": [
                {"VarCharValue": "2025-05-15"},
                {"VarCharValue": "234567890123"},
                {"VarCharValue": "AmazonS3"},
                {"VarCharValue": "67.89"}
            ]}
        ]
        mock_athena.get_query_results.return_value = {
            "ResultSet": {"Rows": test_rows}
        }

        # CurDAOのインスタンス化とfetch()の実行
        dao = CurDAO(
            {
                "AWS_REGION": self.mock_params["AWS_REGION"],
                "ATHENA_DATABASE": self.mock_params["ATHENA_DATABASE"],
                "ATHENA_TABLE": self.mock_params["ATHENA_TABLE"],
                "ATHENA_OUTPUT_URI": self.mock_params["ATHENA_OUTPUT_URI"],
                "ATHENA_LINE_ITEM_TYPES": self.mock_params["ATHENA_LINE_ITEM_TYPES"],
                "QUERY_DAYS_RANGE": self.mock_params["QUERY_DAYS_RANGE"],
            }
        )
        results = dao.fetch(["123456789012", "234567890123"])

        # 結果の検証
        self.assertEqual(len(results), 2)

        # 最初の行の検証
        self.assertEqual(results[0], ("2025-05-15", "123456789012", "AmazonEC2", 123.45))
        # 2番目の行の検証
        self.assertEqual(results[1], ("2025-05-15", "234567890123", "AmazonS3", 67.89))

        # クエリパラメータの検証
        mock_athena.start_query_execution.assert_called_once()
        query_string = mock_athena.start_query_execution.call_args[1]["QueryString"]

        # クエリに必要なパラメータが含まれているか確認
        self.assertIn("'123456789012'", query_string)
        self.assertIn("'234567890123'", query_string)
        self.assertIn(f"-{self.mock_params['QUERY_DAYS_RANGE']}", query_string)

    @patch('boto3.client')
    def test_fetch_with_empty_results(self, mock_boto3):
        # モックの設定
        mock_athena = MagicMock()
        mock_boto3.return_value = mock_athena

        mock_athena.start_query_execution.return_value = {
            "QueryExecutionId": "test-execution-id"
        }
        mock_athena.get_query_execution.return_value = {
            "QueryExecution": {"Status": {"State": "SUCCEEDED"}}
        }

        # ヘッダーだけで、データがない場合
        mock_athena.get_query_results.return_value = {
            "ResultSet": {"Rows": [{
                "Data": [
                    {"VarCharValue": "date"},
                    {"VarCharValue": "account_id"},
                    {"VarCharValue": "service"},
                    {"VarCharValue": "cost"}
                ]
            }]}
        }

        # CurDAOのインスタンス化とfetch()の実行
        dao = CurDAO(
            {
                "AWS_REGION": self.mock_params["AWS_REGION"],
                "ATHENA_DATABASE": self.mock_params["ATHENA_DATABASE"],
                "ATHENA_TABLE": self.mock_params["ATHENA_TABLE"],
                "ATHENA_OUTPUT_URI": self.mock_params["ATHENA_OUTPUT_URI"],
                "ATHENA_LINE_ITEM_TYPES": self.mock_params["ATHENA_LINE_ITEM_TYPES"],
                "QUERY_DAYS_RANGE": self.mock_params["QUERY_DAYS_RANGE"],
            }
        )
        results = dao.fetch(["123456789012"])

        # 結果の検証
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
