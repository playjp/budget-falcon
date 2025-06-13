import os
import pytest
from datetime import datetime, timedelta
from budget_falcon.graph_plotter import plot_graph

def test_plot_graph_normal_accounts():
    """
    テスト内容:
    通常利用の2つのAWSアカウントの、過去14日分の各種サービス利用コストのダミーデータからグラフ画像を生成できるかテストします。
    画像の内容は自動では検証されないので、目視で確認してください。
    - 画像ファイルが生成されていることを検証する。
    """
    # テスト用のデータを作成
    accounts = [
        ("123456789012", "Test Account 1"),
        ("987654321098", "テストアカウント 2"),
    ]

    # 過去14日分のデータを生成
    base_date = datetime.now()
    records = []
    for i in range(14):
        date = (base_date - timedelta(days=13-i)).strftime("%Y-%m-%d")
        records.extend([
            # Compute系
            [date, "123456789012", "AmazonEC2", 30.0],
            [date, "123456789012", "AWSLambda", 5.0 + i * 0.2],
            [date, "123456789012", "AmazonECS", 15.0 + i * 0.1],
            [date, "123456789012", "AmazonEKS", 20.0 + i],
            # Storage系
            [date, "123456789012", "AmazonS3", 30.0 + i * 0.5],
            [date, "123456789012", "AmazonEFS", 15.0 + i * 0.3],
            [date, "123456789012", "AmazonECR", 10.0 + i * 0.2],
            # Database系
            [date, "123456789012", "AmazonRDS", 75.0],
            [date, "123456789012", "AmazonDynamoDB", 110.0 if i == 12 else 15.0 + i * 0.7], # 急に増える
            # その他
            [date, "123456789012", "AmazonCloudWatch", 8.0 - i * 0.1],
        ])
        records.extend([
            # Networking系
            [date, "987654321098", "AmazonCloudFront", 45.0 + i * 0.9],
            [date, "987654321098", "AmazonRoute53", 12.0 + i * 0.2],
            # Analytics系
            [date, "987654321098", "AmazonAthena", max(40.0,  i * 8.1 - 20.0)], # 急に増える
            [date, "987654321098", "AmazonKinesis", 55.0 + i * 0.8],
            # Security系
            [date, "987654321098", "awskms", 18.0 + i * 0.3],
            [date, "987654321098", "AWSSecretsManager", 9.0 + i * 0.2],
            # その他
            [date, "987654321098", "AmazonSNS", 5.0 + i * 0.1],
        ])
    # 出力ファイルパスの設定
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "test_cost_graph_normal.png")

    # グラフの生成
    result_path = plot_graph(
        records=records,
        accounts=accounts,
        output_path=output_path,
        top_n_services=5
    )

    # 画像ファイルが生成されていることを確認
    assert os.path.exists(result_path)
    print(f"\nGraph has been generated at: {result_path}")

def test_plot_graph_low_usage_account():
    """
    テスト内容:
    低利用アカウント（コスト0.01未満）のグラフ生成をテストします。
    Y軸のスケールが0から0.01になることを目視で確認してください。
    - 画像ファイルが生成されていることを検証する。
    """
    # テスト用のデータを作成
    accounts = [
        ("000000000000", "Low Usage Account"),
    ]

    # 過去14日分のデータを生成
    base_date = datetime.now()
    records = []
    for i in range(14):
        date = (base_date - timedelta(days=13-i)).strftime("%Y-%m-%d")
        records.extend([
            # Storage系のみ使用
            [date, "000000000000", "AmazonS3", 0.0001 + i * 0.00002],  # 非常に小さな利用量
            # CloudWatchのメトリクス保存
            [date, "000000000000", "AmazonCloudWatch", 0.00001],  # さらに小さな利用量
        ])

    # 出力ファイルパスの設定
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "test_cost_graph_low_usage.png")

    # グラフの生成
    result_path = plot_graph(
        records=records,
        accounts=accounts,
        output_path=output_path,
        top_n_services=5
    )

    # 画像ファイルが生成されていることを確認
    assert os.path.exists(result_path)
    print(f"\nLow usage account graph has been generated at: {result_path}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
