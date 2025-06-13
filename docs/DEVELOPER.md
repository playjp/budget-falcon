# 開発者向けドキュメント

## 開発ツール

- [poetry](https://python-poetry.org/)
- [editorconfig](https://editorconfig.org/)

### パッケージ管理 poetry

本プロジェクトでは poetry を利用してパッケージ管理をしています。

```bash
pip install poetry
# pyproject.toml の内容をもとに .venv を作成
poetry install
```

#### budget_falcon/requirements.txt の更新

開発中のローカル仮想環境のパッケージは poetry で管理されますが、Lambda関数のデプロイ時には `budget_falcon/requirements.txt` にパッケージを記載する必要があります。 poetry 2.0 以降ではプラグイン `poetry-plugin-export` を使用して、`requirements.txt` を生成します。

```bash
pip install poetry-plugin-export
poetry export -f requirements.txt --output budget_falcon/requirements.txt --without-hashes
```

### editorconfig

本プロジェクトでは、コードフォーマットの統一のために [editorconfig](https://editorconfig.org/) を使用しています。エディタに対応するプラグインをインストールしてください。

editorconfig は多数のエディタでサポートされているため、使用するエディタに依存せずにコードのフォーマットを統一できます。

## 設定ファイル

### Google Cloud Workload Identity Federation設定

Google Sheets APIにアクセスするためのWorkload Identity Federation設定ファイルが必要です。

```bash
# サンプルファイルをコピーして作成
cp budget_falcon/config/wif.json.example budget_falcon/config/wif.json
```

`budget_falcon/config/wif.json` を実際のGoogle Cloud Platform設定で更新してください：

- `YOUR_PROJECT_NUMBER`: Google Cloud PlatformのプロジェクトID（数値）
- `YOUR_POOL_ID`: Workload Identity Poolの名前
- `YOUR_PROVIDER_ID`: Workload Identity Providerの名前  
- `YOUR_SERVICE_ACCOUNT`: Google Sheets APIにアクセスするサービスアカウント名
- `YOUR_PROJECT`: Google Cloud Platformのプロジェクト名

Workload Identity Federation の設定手順は [デプロイ手順](DEPLOY.md) を参照してください。

## ユニットテスト

```bash
poetry run pytest
# ファイル名を指定して実行
poetry run pytest tests/unit/test_graph_plotter.py
```
