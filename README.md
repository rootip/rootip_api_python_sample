# root ipクラウド API Pythonサンプルコード

知財管理システム「root ipクラウド」のAPI利用方法を示す公式サンプルです。
製品情報は [root ip公式サイト](https://rootip.co.jp) を参照してください。

> [!WARNING]
> 本リポジトリは学習・検証用のサンプルです。本番利用前に、組織のセキュリティ担当者によるレビューとデモ・検証環境での動作確認を行ってください。

## 対応環境

- Python 3.11
- Windows、macOS、Linux（利用するCPU・OS向けwheelがPyPIで提供されている環境）
- Dev Container: Python 3.11

`requirements-lock.txt` はwheelのみを許可するため、Alpine Linuxなど未対応環境では安全のためインストールに失敗します。「最新のPython」ではなく、上記バージョンを使用してください。

## 利用前に確認すること

1. 契約者向けrootip APIリファレンスで、利用するAPIと必要権限を確認する。
2. 最初は本番環境ではなく、デモ・検証環境を使用する。
3. [セキュリティガイド](SECURITY_GUIDE.md)を読む。
4. APIトークン、証明書、パスワード、実顧客データをAIチャットやIssueへ貼り付けない。

本サンプルは `*.rootip-cloud.net` のHTTPS接続だけを許可します。rootipが提供する独自ドメインを利用する契約では、rootipサポートへ確認したうえで許可ホスト設定を変更してください。

## セットアップ

リポジトリのルートディレクトリで実行してください。

### 1. 仮想環境を作成

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. ハッシュ検証付きで依存パッケージを導入

```bash
python -m pip install --only-binary=:all: --require-hashes -r requirements-lock.txt
```

バージョンとSHA-256ハッシュを照合します。ただし、ハッシュ一致はパッケージ自体の安全性を保証するものではありません。`requirements.txt` 単体でのインストールは行わないでください。

### 3. 認証情報を設定

`config/secrets.py.template` を `config/secrets.py` へコピーし、契約者向けAPIリファレンスに従って設定します。

- `config/secrets.py` はGit管理対象外です。
- 証明書はリポジトリ外のアクセス制限された場所へ保存してください。
- TLSエラーが発生しても `verify=False` を使用しないでください。

### 4. ローカル検証

```bash
python -m app.hello
python -m unittest discover -s tests
```

### 5. 読み取りサンプル

次のコマンドは案件書誌をGETし、ステータスと件数だけを表示します。レスポンス本文は表示しません。

```bash
python -m app.sample
```

## サンプル一覧

| コマンド | 操作 | 注意事項 |
|---|---|---|
| `python -m rootip.app_sample.case_biblios_get` | GET | 案件書誌の件数だけを表示 |
| `python -m rootip.app_sample.master_staffs_get_to_csv` | GET・ローカル保存 | 確認後に担当者CSVを保存。POSIX環境では所有者限定権限。Windowsでは保存先ACLを確認 |
| `python -m rootip.app_sample.master_staffs_put` | PUT（単件） | ソース内の値設定が必要。内容表示後に `yes` で実行 |
| `python -m rootip.app_sample.master_currencies_get_and_update` | GET・PUT（最大50件） | 外部為替CSVを利用。内容表示後に `yes` で実行 |

更新系サンプルは、最初にGETで対象を確認し、更新内容を表示してから実行します。失敗時の自動再送は行いません。一括更新は途中まで成功する可能性があるため、完了件数を必ず確認してください。

### 第三者為替データについて

通貨更新サンプルは、三菱UFJ銀行が公開する為替相場CSV
`https://www.bk.mufg.jp/gdocs/kinri/list_j/kinri/spot_rate.csv`
へ通信します。root ipが提供するデータではなく、提供元の利用条件・可用性・形式変更の影響を受けます。サンプルはサイズ、行数、列、値域、変動幅を検証しますが、更新前に人が内容を確認してください。

## Dev Container / GitHub Codespaces

`.devcontainer/devcontainer.json` を同梱しています。コンテナ作成時にハッシュ付きロックファイルから依存関係を導入し、テストを実行します。認証情報はコンテナイメージやリポジトリへ含めないでください。

## 依存関係の更新

依存関係の追加・更新は通常利用者向けの操作ではありません。メンテナは [CONTRIBUTING.md](CONTRIBUTING.md) と [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md) に従い、`requirements.txt` と `requirements-lock.txt` を同時に更新し、対応OSでCIを通してください。

## セキュリティとサポート

- 安全な利用方法: [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
- 脆弱性の報告: [SECURITY.md](SECURITY.md)
- AI支援開発の正本ルール: [AI_DEVELOPMENT_RULES.md](AI_DEVELOPMENT_RULES.md)
- 製品サポート: [root ip公式サイト](https://rootip.co.jp)

公開Issueへ秘密情報や実顧客データを投稿しないでください。

## ライセンス

[BSD 3-Clause License](LICENSE) に基づいて提供します。本サンプルは現状有姿で提供され、特定目的への適合性を保証しません。
