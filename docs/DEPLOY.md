# デプロイ手順

AWS SAM でのデプロイとは別に、以下の準備が必要です。

- Google Cloud Platform での設定
  - プロジェクトの作成
  - Spreadsheets APIの有効化
  - サービスアカウントの作成
  - Workload Identity Federation
- Googleスプレッドシートの作成と設定
- Slack Appの設定
- AWS Cost and Usage Report 2.0の設定


## Google Cloud Platformの設定

AWS アカウントはすでに作成されている前提です。またAWSのLambda関数に設定するIAMロールの名前を予め決めてください。

### プロジェクトの作成

Google Cloud Platform (GCP)で新しいプロジェクトを作成します。

### Spreadsheets APIの有効化

Google Cloud Consoleで、作成したプロジェクトに対してSpreadsheets APIを有効化します。

1. 左側のナビゲーションメニューから「APIとサービス」→「ライブラリ」を選択します。
2. 検索バーに「Google Sheets API」と入力し、表示された結果から「Google Sheets API」を選択します。
3. 「有効にする」ボタンをクリックして、APIを有効化します。

### サービスアカウントの作成

Google Cloud Consoleで、Google Sheets APIを使用するためのサービスアカウントを作成します。アクセス権限はスプレッドシート側に設定するため、ここでの設定は不要です。

1. 左側のナビゲーションメニューから「IAMと管理」→「サービスアカウント」を選択します。
2. 「サービスアカウントを作成」ボタンをクリックします。
3. サービスアカウントの名前を入力、必要に応じて説明を追加し「作成」ボタンをクリックします。

### Workload Identity Federation

Google Cloud で Workload Identity Federation を設定し、AWSと連携します。

1. 左側のナビゲーションメニューから「IAMと管理」→「Workload Identity 連携」を選択します。
2. 「プールを作成」ボタンをクリックし、名前を入力します。
3. 「プロバイダの選択」から「AWS」を選択し、プロバイダ名（任意）とAWSアカウントIDを入力します。
4. 「マッピングを編集」セクションで google.subject のマッピングを ` assertion.arn.contains('assumed-role') ? assertion.arn.extract('assumed-role/{role_name}/') : assertion.arn ` に設定し、保存します。
5. 作成したプールの詳細ページで「アクセスを許可」 → 「Grant access using service account impersonation」を選択します。
6. 先ほど作成したサービスアカウントを選択。プリンシパルの属性名は subject、値には後ほどAWS SAMで指定するIAMロール名を入力・保存します。
7. プール詳細ページの「接続済みサービスアカウント」セクションを開くと、サービスアカウントに対応する Client library config の表示と「ダウンロード」が表示されます。これをダウンロードし、本リポジトリの `budget_falcon/config/wif.json` に保存します。
  - このファイルに秘密鍵などの情報は含まれないので、Secret Managerは使用していません。
  - 項目を手動で入力して作成することもできます。 [デプロイ手順](DEVELOPER.md)


## Googleスプレッドシートの作成と設定

Googleスプレッドシートを作成し、GCPのサービスアカウントに閲覧者権限を付与します（メールアドレスでの指定で追加できます）。データを入力するシート名（画面下のタブ名）をわかりやすい名前に設定します。

シート名とスプレッドシートのID（URLの `/d/` と `/edit` の間の部分）は AWS SAM でのデプロイ時に必要となります。

シート内のセルには以下のようなデータを、1行ごとに入力します（使用するセル範囲は SAM デプロイ時に指定できます）。
- 設定名（ログ用）
- SlackチャンネルID
- AWSアカウントID 1
- 表示名 1
- AWSアカウントID 2
- 表示名 2
- ...(12アカウントまで)


## Slack Appの設定

Slack Appを作成し、必要な権限を設定します。

1. Slack APIの[アプリ作成ページ](https://api.slack.com/apps)にアクセスし、「Create New App」をクリックします。
2. 「From scratch」を選択し、アプリ名とワークスペースを指定して「Create App」をクリックします。
3. 「Oauth & Permissions」セクションの「Scopes」で、Bot Token Scopesに以下権限を追加します。
  - channels:join
  - chat:write
  - files:write
4. 「OAuth Token」セクションで「Install to (Workspace)」をクリックし、アプリをインストールします。
5. インストール後に表示される Bot User OAuth Token を記録します。このトークンは AWS SAM でのデプロイ時に必要となります。
6. 「Basic Information」セクションの「Display Information」でアイコン等を設定します。


## AWS Cost and Usage Report 2.0の設定

Parquet形式で、AWS Cost and Usage Report(CUR)2.0をS3バケットに出力します。詳細な手順は[AWSのドキュメント](https://docs.aws.amazon.com/ja_jp/awsaccountbilling/latest/aboutv2/cost-and-usage-report-setup.html)を参照してください。

システムで利用する最低限のカラムは以下になりますが、別途分析する場合など、必要に応じて他のカラムも出力してください。

- line_item_usage_account_id
- line_item_product_code
- line_item_line_item_type
- line_item_unblended_cost
- line_item_usage_start_date

出力先のS3バケット名とプレフィックスは、AWS SAMでのデプロイ時に必要となります。


## SAMでのビルド・デプロイ

名前を指定してIAMロールを作成するため、デプロイ時に`--capabilities CAPABILITY_NAMED_IAM`の指定が必要です。

```bash
sam build --use-container --build-image public.ecr.aws/sam/build-python3.13

sam deploy --config-env develop --guided --capabilities CAPABILITY_NAMED_IAM
```

`Error: Docker is unreachable. Please check if Docker is running.`などのエラーが出る場合は`DOCKER_HOST`を設定してビルドすること。

```bash
# 使用したいDOCKER ENDPOINTを確認する
docker context ls
DOCKER_HOST=unix:///Users/sampleuser/.rd/docker.sock sam build --use-container --build-image public.ecr.aws/sam/build-python3.13
```

### SAM パラメータ例

```
GoogleSpreadsheetId: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GoogleSpreadsheetRange: data!A3:Z
SlackToken: xoxb-00000000...

AthenaBucket: your-bucket-name
AthenaDataPrefix: cur-exports/daily-cur/data/
AthenaOutputPrefix: athena/

FunctionRoleName: budget-falcon-role
QueryDaysRange: 14
TopNServices: 10
FunctionMemorySize: 1024
FunctionTimeout: 300
Schedule: 0 1 * * ? *
LogRetentionInDays: 90
```
