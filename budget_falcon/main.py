import os
from datetime import datetime
import pytz
from typing import Any

from account_dao import AccountDAO, AccountGroup, AccountDAOParameters
from cur_dao import CurDAO, CurDAOParameters
from graph_plotter import plot_graph, ServiceRecord
from slack_notice import SlackClient


ACCOUNT_DAO_PARAMS: AccountDAOParameters = {
    "SPREADSHEET_ID": os.environ["GOOGLE_SPREADSHEET_ID"],
    "SPREADSHEET_RANGE": os.environ["GOOGLE_SPREADSHEET_RANGE"],
}

CUR_DAO_PARAMS: CurDAOParameters = {
    "AWS_REGION": os.environ.get("AWS_REGION") or "ap-northeast-1",
    "ATHENA_DATABASE": os.environ["ATHENA_DATABASE"],
    "ATHENA_TABLE": os.environ["ATHENA_TABLE"],
    "ATHENA_OUTPUT_URI": os.environ["ATHENA_OUTPUT_URI"],
    "ATHENA_LINE_ITEM_TYPES": os.environ["ATHENA_LINE_ITEM_TYPES"].split(","),
    "QUERY_DAYS_RANGE": int(os.environ.get("QUERY_DAYS_RANGE", "14")),
}

SLACK_TOKEN: str = os.environ["SLACK_TOKEN"]

TOP_N_SERVICES: int = int(os.environ.get("TOP_N_SERVICES", "8"))


def lambda_handler(event: dict[str, Any], context: Any) -> None:
    """
    AWS Lambda function to fetch AWS cost and usage data, generate graphs, and post them to Slack.
    event and context are provided by AWS Lambda, but they are not used in this function.

    Args:
        event
        context

    Returns:
        None
    """
    jst = pytz.timezone("Asia/Tokyo")
    exec_time_jst: str = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"Execution time: {exec_time_jst}")

    account_dao = AccountDAO(ACCOUNT_DAO_PARAMS)
    cur_dao = CurDAO(CUR_DAO_PARAMS)
    slack_client = SlackClient(SLACK_TOKEN)

    account_groups: list[AccountGroup] = account_dao.group_list()
    for i, group in enumerate(account_groups):
        print("execute for group:", group["name"])
        try:
            # ループごとに再計算
            exec_time_jst = datetime.now(jst).strftime("%Y-%m-%d %H:%M")
            account_ids: list[str] = [aid[0] for aid in group["accounts"]]

            records: list[ServiceRecord] = cur_dao.fetch(account_ids)
            filepath: str = plot_graph(
                records,
                accounts=group["accounts"],
                output_path=f"/tmp/chart_{i}.png",
                top_n_services=TOP_N_SERVICES,
            )
            slack_client.post_file(
                group["target_channel"],
                filepath,
                title=f"AWS日次コスト{exec_time_jst}",
            )
        except Exception as e:
            print(f"Error processing group {group['name']}: {e}")
