# root ipクラウドAPI pythonサンプルコード

このプロジェクトは「知財管理システム root ipクラウド」のAPI機能を活用するためのサンプルプログラムを公開するものです。
<a href="https://rootip.co.jp"  target="_blank">https://rootip.co.jp</a>

## 目次
- [事前準備](#事前準備)
- [インストール手順](#インストール手順)
- [実行方法](#実行方法)

## 事前準備
このプログラムを実行するために、以下の環境が必要です：
- **Python**：最新のバージョンのPythonをインストールしてください。
- **Visual Studio Code (VSCode)**：VSCodeをインストールし、Python拡張機能もインストールしてください。

## インストール手順
1. リポジトリのZipファイルをダウンロードします。
   - GitHubのリポジトリページから、`Code`ボタンをクリックし、`Download ZIP`を選択してダウンロードします。
2. ダウンロードしたZipファイルを解凍し、任意のフォルダに展開します。
3. サンプルコードのフォルダ構造は下記のとおりです。
    ```markdown
    rootip_api_python_sample/
    ├── app/
    │   ├── ユーザが自身のプログラムを保存するフォルダ
    ├── config/
    │   ├── 設定ファイルを保存するフォルダ
    └── rootip/
        ├── rootipが作成したサンプルプログラムを保存するフォルダ
    ```
4. `config/secrets.py.template`ファイルをコピーし、`config/secrets.py`という名前で保存します。
5. `config/secrets.py`ファイルを編集し、必要な秘密情報（APIキーやパスワードなど）を記入します。
6. VSCodeでプロジェクトフォルダを開き、ターミナルから必要なPythonパッケージをインストールします
```bash
pip install -r requirements.txt
```

## 実行方法
VSCodeのターミナルから下記のようにプログラムを指定して実行できます。
```bash
#appフォルダのsample.pyを実行
python -m app.sample
```
