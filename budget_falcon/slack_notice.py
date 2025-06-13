from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """
    Slack API client for posting files to Slack channels.
    
    This class provides methods to upload files to Slack channels using the Slack SDK.
    Automatically attempts to join channels before posting and includes retry logic.
    """
    def __init__(self, token: str) -> None:
        self.client: WebClient = WebClient(token=token)

    def post_file(self, channel_id: str, file_path: str, title: str = "AWS Cost Breakdown (Daily)") -> None:
        """
        Posts a file to a Slack channel.

        Args:
            channel_id: The ID of the Slack channel to post to
            file_path: Path to the file to upload
            title: Title of the file upload (default: "AWS Cost Breakdown (Daily)")

        Note:
            Attempts to join the channel before posting. Prints error messages if joining
            or uploading fails, but does not raise exceptions.
        """
        try:
            self.client.conversations_join(channel=channel_id)
        except SlackApiError as e:
            print(f"Error joining channel: {e.response['error']}")
            return

        # 失敗時に1回だけリトライする
        for _ in range(2):
            try:
                with open(file_path, "rb") as f:
                    self.client.files_upload_v2(
                        channel=channel_id,
                        file=f,
                        filename=file_path.split("/")[-1],
                        title=title,
                    )
                    return
            except SlackApiError as e:
                print(f"Error uploading file: {e.response['error']}")
            except TimeoutError as e:
                print(f"Timeout error while uploading file: {e}")
