
# root ipクラウドAPI pythonサンプルコード

このプロジェクトは「知財管理システム root ipクラウド」のAPI機能を活用するためのサンプルプログラムです。
<a href="https://rootip.co.jp"  target="_blank">https://rootip.co.jp</a>

## 目次
- [一般的な利用方法](#一般的な利用方法)
- [開発経験者向け利用方法（Dev Container利用）](#開発経験者向け利用方法（DevContainer利用）)
- [サンプルコードのフォルダ構造](#サンプルコードのフォルダ構造)

※通常は"一般的な利用方法"をご参照ください。GitHub Codespaceを使用する場合は"開発経験者向け利用方法"の手順となります

---

## 一般的な利用方法

### 事前準備
- **Python（Windows版）**：公式サイト https://www.python.org/ から最新のバージョンのPythonをインストールしてください。
  - インストール時に「Add Python to PATH」にチェックを入れてください。
- **Visual Studio Code (VSCode)**：VSCodeをインストールしてください。
  - 必要に応じて「Python」拡張機能もインストールしてください。

### インストール手順
1. 本GitHubのリポジトリページから「Code」→「Download ZIP」でダウンロードします。
2. ダウンロードしたZipファイルを解凍し、任意のフォルダに展開します。
3. VSCodeでこのフォルダを開きます。
4. VSCodeのターミナルから下記コマンドを実行し、必要なPythonパッケージをインストールします。
    ```bash
    pip install -r requirements.txt
    ```
5. `config/secrets.py.template`ファイルをコピーし、`config/secrets.py`という名前で保存します。
6. `config/secrets.py`ファイルを編集し、必要な秘密情報（APIキーやパスワードなど）を記入します。

### 動作確認・実行方法
VSCodeのターミナルから下記のように実行できます。
```bash
# Pythonの動作確認 (Hello, World!と表示されれば正常)
python -m app.hello

# サンプルプログラムの実行
python -m app.sample
```

---

## 開発経験者向け利用方法（DevContainer利用）

### 事前準備
- **Visual Studio Code (VSCode)インストール**
- **Dev Containers拡張機能インストール**
- **Docker Desktopインストール**（WSL2有効化推奨）

※GitHub Codespaceを使用する場合は不要

### インストール手順
1. 本リポジトリをクローンまたはZipでダウンロードし、展開します。
2. VSCodeでこのフォルダを開きます。
3. 「このリポジトリで利用できる Dev Container構成 があります」と表示されたら「コンテナーで再度開く」を選択します。
4. `config/secrets.py.template`ファイルをコピーし、`config/secrets.py`という名前で保存します。
5. `config/secrets.py`ファイルを編集し、必要な秘密情報（APIキーやパスワードなど）を記入します。

### 実行方法
VSCodeのターミナルから下記のようにプログラムを指定して実行できます。
```bash
# Pythonの動作確認 (Hello, World!と表示されれば正常)
python -m app.hello

# サンプルプログラムの実行
python -m app.sample
```

もしpythonモジュールを追加した場合は、下記コマンドでパッケージを再インストールしてください。
```bash
pip install -r requirements.txt
```

---

## サンプルコードのフォルダ構造
サンプルコードのフォルダ構造は下記のとおりです。
```markdown
rootip_api_python_sample/
├── app/
│   ├── ユーザが自身のプログラムを保存するフォルダ
├── config/
│   ├── 設定ファイルを保存するフォルダ
└── rootip/
    ├── rootipが作成したサンプルプログラムを保存するフォルダ
```
