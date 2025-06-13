import time
import boto3
from typing import Any, Optional, TypedDict

# fetch CUR(Cost and Usage Report) data from AWS Athena

class CurDAOParameters(TypedDict):
    AWS_REGION: str
    ATHENA_DATABASE: str
    ATHENA_TABLE: str
    ATHENA_OUTPUT_URI: str
    ATHENA_LINE_ITEM_TYPES: list[str]
    QUERY_DAYS_RANGE: int


CurRecord = tuple[str, str, str, float]  # (date, account_id, service, cost)

class CurDAO:
    """
    Data Access Object for AWS Cost and Usage Report (CUR) 2.0 data via Athena.
    
    This class provides methods to query AWS cost data stored in S3 as Parquet files
    through Amazon Athena service.
    """
    def __init__(self, PARAMS: CurDAOParameters) -> None:
        self.client = boto3.client("athena", region_name=PARAMS["AWS_REGION"])
        self.database: str = PARAMS["ATHENA_DATABASE"]
        self.table: str = PARAMS["ATHENA_TABLE"]
        self.output_uri: str = PARAMS["ATHENA_OUTPUT_URI"]
        self.line_item_types: list[str] = PARAMS["ATHENA_LINE_ITEM_TYPES"]
        self.query_days_range: int = max(7, min(30, PARAMS["QUERY_DAYS_RANGE"]))

    def fetch(self, account_ids: list[str]) -> list[CurRecord]:
        """
        Fetches cost and usage report data for given AWS account IDs.

        Args:
            account_ids: List of AWS account IDs to fetch data for.

        Returns:
            List of (date, account_id, service, cost) where cost is a float and others are strings.
        """
        ids_str: str = ",".join([f"'{aid.strip()}'" for aid in account_ids])
        line_item_types_str: str = ",".join([f"'{lit.strip()}'" for lit in self.line_item_types])
        query: str = f"""
            SELECT
                date_format(date_add('hour', 9, line_item_usage_start_date), '%Y-%m-%d') AS date,
                line_item_usage_account_id AS account_id,
                line_item_product_code AS service,
                SUM(line_item_unblended_cost) AS cost
            FROM "{self.table}"
            WHERE
                line_item_usage_account_id IN ({ids_str})
                AND line_item_usage_start_date >= date_add('day', -{self.query_days_range}, date(date_add('hour', 9, current_timestamp)))
                AND line_item_line_item_type IN ({line_item_types_str})
            GROUP BY 1, 2, 3
            ORDER BY 1, 2
        """
        response: dict[str, Any] = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={"Database": self.database},
            ResultConfiguration={"OutputLocation": self.output_uri},
            # クエリ結果の再利用設定
            ResultReuseConfiguration={
                "ResultReuseByAgeConfiguration": {
                    "Enabled": True,
                    "MaxAgeInMinutes": 60,
                }
            },
        )
        query_execution_id: str = response["QueryExecutionId"]
        print("QueryExecutionId:", query_execution_id)
        while True:
            status: dict[str, Any] = self.client.get_query_execution(
                QueryExecutionId=query_execution_id
            )
            state: str = status["QueryExecution"]["Status"]["State"]
            if state in ["FAILED", "CANCELLED"]:
                reason: str = status["QueryExecution"]["Status"]["StateChangeReason"]
                raise Exception(f"Query failed: {state} {reason}")
            if state == "SUCCEEDED":
                break
            time.sleep(1)

        # ページネーションで全件取得
        query_results: list[dict[str, Any]] = []
        next_token: Optional[str] = None
        while True:
            if next_token:
                response = self.client.get_query_results(
                    QueryExecutionId=query_execution_id,
                    NextToken=next_token,
                )
            else:
                response = self.client.get_query_results(
                    QueryExecutionId=query_execution_id,
                )
            query_results.extend(response["ResultSet"]["Rows"])
            next_token = response.get("NextToken")
            if not next_token:
                break

        # クエリ結果を整形
        query_results = query_results[1:]  # ヘッダーの除外
        results: list[CurRecord] = []
        for row in query_results:
            date, account_id, service, cost = [
                col["VarCharValue"] for col in row["Data"]
            ]
            results.append((date, account_id, service, float(cost)))
        return results
