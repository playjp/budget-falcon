import re
import os
import json
from typing import Any, Set, TypedDict, Optional, Tuple
from google.auth import load_credentials_from_dict
from google.auth.credentials import Credentials
from googleapiclient.discovery import build

class AccountDAOParameters(TypedDict):
    SPREADSHEET_ID: str
    SPREADSHEET_RANGE: str

Account = tuple[str, str] # account_id, display_name

"""
AccountGroup structure:
    {
        "name": "PROJECT X",           # Project name
        "target_channel": "CXXXXXXXX", # Slack channel ID
        "accounts": [                  # List of AWS account ID and display name pairs
            ("123456789012", "dev-account"),
            ("234567890123", "prod-account"),
        ],
    }
"""
class AccountGroup(TypedDict):
    name: str
    target_channel: str
    accounts: list[Account] # List of (account_id, display_name)


class AccountDAO:
    """
    Data Access Object for AWS account configurations stored in Google Spreadsheets.
    
    This class provides methods to retrieve account groupings and Slack channel mappings
    from Google Sheets using Workload Identity Federation for authentication.
    """
    def __init__(self, PARAMS: AccountDAOParameters) -> None:
        # Workload Identity Federationを使用した認証
        path: str = os.path.join(os.path.dirname(__file__), "config", "wif.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                wif_config: dict[str, Any] = json.load(f)
                credentials_and_project: Tuple[Credentials, Optional[str]] = load_credentials_from_dict(wif_config)
                self.credentials = credentials_and_project[0]
        except FileNotFoundError:
            raise RuntimeError(f"Workload Identity Federation configuration file not found: {path}. "
                             "Please copy wif.json.example to wif.json and configure it.") from None
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Invalid WIF configuration file: {e}") from e

        # Google Sheets APIのサービスオブジェクトを作成
        self.service: Any = build("sheets", "v4", credentials=self.credentials)
        self.sheets: Any = self.service.spreadsheets()
        self.spreadsheetId: str = PARAMS["SPREADSHEET_ID"]
        self.spreadsheetRange: str = PARAMS["SPREADSHEET_RANGE"]

    def group_list(self) -> list[AccountGroup]:
        result: dict[str, Any] = (
            self.sheets.values()
            .get(spreadsheetId=self.spreadsheetId, range=self.spreadsheetRange, majorDimension="ROWS")
            .execute()
        )
        """
        Example values from spreadsheet:
            ['PROJECT X', 'CXXXXXXXX', '123456789012', 'dev-account', '234567890123', 'prod-account']
        """
        values: list[list[str]] = result.get("values", [])


        items: list[AccountGroup] = []
        slack_channel_pattern: re.Pattern = re.compile(r"^[CG][A-Z0-9]{8,}$")
        aws_account_pattern: re.Pattern = re.compile(r"^\d{12}$")
        for value in values:
            if len(value) < 4:
                continue
            name: str = value[0]
            target_channel: str = value[1]
            if not target_channel or not slack_channel_pattern.match(target_channel):
                continue

            accounts: list[tuple[str, str]] = []
            account_ids: Set[str] = set()
            for i in range(2, len(value), 2):
                if i + 1 < len(value):
                    account_id: str = value[i]
                    display_name: str = value[i + 1]
                    if (
                        not account_id
                        or not display_name
                        or account_id in account_ids
                        or not aws_account_pattern.match(account_id)
                    ):
                        continue
                    accounts.append((account_id, display_name))
                    account_ids.add(account_id)
            if not accounts:
                continue
            item: AccountGroup = {
                "name": name if len(name) > 0 else "No Name",
                "target_channel": target_channel,
                "accounts": accounts,
            }
            items.append(item)
        return items
