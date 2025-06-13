import unittest
from unittest.mock import patch, mock_open
from slack_sdk.errors import SlackApiError
from budget_falcon.slack_notice import SlackClient


class TestSlackClient(unittest.TestCase):
    """
    SlackClientクラスのpost_fileメソッドをテストします。
    テスト内容:
        - test_post_file_success:
            正常系。チャンネル参加とファイルアップロードが正常に行われることを検証する。
            ・conversations_joinとfiles_upload_v2が正しく呼ばれること
            ・アップロード時の引数が正しいこと
        - test_post_file_channel_join_error:
            異常系。チャンネル参加時にエラーが発生した場合の挙動を検証する。
            ・エラーメッセージがprintされること
            ・ファイルアップロードが実行されないこと
        - test_post_file_upload_error:
            異常系。ファイルアップロード時にエラーが発生した場合の挙動を検証する。
            ・エラーメッセージがprintされること
            ・アップロード時の引数が正しいこと
    """
    def setUp(self):
        self.token = "test-token"
        self.channel = "C12345678"
        self.file_path = "/tmp/test.png"
        self.title = "Test Title"

    @patch('budget_falcon.slack_notice.WebClient')
    def test_post_file_success(self, mock_web_client):
        # モックのWebClientインスタンスを設定
        mock_client = mock_web_client.return_value
        mock_client.conversations_join.return_value = {"ok": True}
        mock_client.files_upload_v2.return_value = {"ok": True}

        # ファイルオープンのモック
        m = mock_open(read_data=b"test data")
        with patch("builtins.open", m) as mock_file:
            client = SlackClient(self.token)
            client.post_file(self.channel, self.file_path, self.title)

        # チャンネル参加とファイルアップロードが呼ばれたことを確認
        mock_client.conversations_join.assert_called_once_with(channel=self.channel)
        mock_client.files_upload_v2.assert_called_once()
        
        # ファイルアップロードの引数を検証
        upload_args = mock_client.files_upload_v2.call_args[1]
        self.assertEqual(upload_args["channel"], self.channel)
        self.assertEqual(upload_args["filename"], "test.png")
        self.assertEqual(upload_args["title"], self.title)
        self.assertEqual(upload_args["file"], mock_file.return_value)

    @patch('budget_falcon.slack_notice.WebClient')
    @patch('builtins.print')
    def test_post_file_channel_join_error(self, mock_print, mock_web_client):
        # モックの設定
        mock_client = mock_web_client.return_value

        # conversations_joinでエラーを発生させる
        error_response = {"ok": False, "error": "channel_not_found"}
        mock_client.conversations_join.side_effect = SlackApiError(
            message="channel_not_found",
            response=error_response
        )

        client = SlackClient(self.token)
        client.post_file(self.channel, self.file_path, self.title)

        # エラーメッセージが出力されることを確認
        mock_print.assert_called_once_with("Error joining channel: channel_not_found")

        # チャンネル参加は失敗し、ファイルアップロードは実行されないことを確認
        mock_client.conversations_join.assert_called_once_with(channel=self.channel)
        mock_client.files_upload_v2.assert_not_called()

    @patch('budget_falcon.slack_notice.WebClient')
    @patch('builtins.print')
    def test_post_file_upload_error(self, mock_print, mock_web_client):
        # モックの設定
        mock_client = mock_web_client.return_value

        # チャンネル参加は成功させる
        mock_client.conversations_join.return_value = {"ok": True}

        # files_upload_v2でエラーを発生させる
        error_response = {"ok": False, "error": "upload_error"}
        mock_client.files_upload_v2.side_effect = SlackApiError(
            message="upload_error",
            response=error_response
        )

        # ファイルオープンのモック
        m = mock_open(read_data=b"test data")
        with patch("builtins.open", m) as mock_file:
            client = SlackClient(self.token)
            # エラーがキャッチされ、例外は発生しない
            client.post_file(self.channel, self.file_path, self.title)

        # エラーメッセージが出力されることを確認
        mock_print.assert_called_once_with("Error uploading file: upload_error")

        mock_client.conversations_join.assert_called_once_with(channel=self.channel)
        mock_client.files_upload_v2.assert_called_once()

        # ファイルアップロードの引数を検証
        upload_args = mock_client.files_upload_v2.call_args[1]
        self.assertEqual(upload_args["channel"], self.channel)
        self.assertEqual(upload_args["filename"], "test.png")
        self.assertEqual(upload_args["title"], self.title)
        self.assertEqual(upload_args["file"], mock_file.return_value)


if __name__ == '__main__':
    unittest.main()
