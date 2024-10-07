import sys
import os
import requests
import urllib3
import json
import csv
from io import StringIO
from config.secrets import (
    ROOTIP_CLIENT_CERTIFICATE_P12,
    ROOTIP_CLIENT_CERTIFICATE_P12_PASSWORD,
    ROOTIP_CLIENT_CERTIFICATE_PEM,
    ROOTIP_API_KEY,
    ROOTIP_USER_ID,
    ROOTIP_URL,
)
import requests_pkcs12

# p12形式クライアント証明書によるInsecureRequestWarningをskip
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# シークレットの例外処理
def handle_secret_exception(exception):
    # エラーメッセージを表示
    print(f"Exception: {exception}")
    # プログラムを終了させる
    sys.exit(1)


# シークレットのチェック
def check_secret():
    try:
        essential_secrets = {
            "ROOTIP_USER_ID": ROOTIP_USER_ID,
            "ROOTIP_API_KEY": ROOTIP_API_KEY,
            "ROOTIP_URL": ROOTIP_URL,
        }

        for key, value in essential_secrets.items():
            if not value:
                raise ValueError(
                    f"Error: The secret value for '{key}' is empty or missing."
                )

        if not ROOTIP_CLIENT_CERTIFICATE_P12 and not ROOTIP_CLIENT_CERTIFICATE_PEM:
            raise ValueError("Error: No client certificate is provided.")

        if ROOTIP_CLIENT_CERTIFICATE_PEM and not os.path.exists(
            ROOTIP_CLIENT_CERTIFICATE_PEM
        ):
            raise FileNotFoundError(
                f"Error: The file {ROOTIP_CLIENT_CERTIFICATE_PEM} does not exist."
            )

        if ROOTIP_CLIENT_CERTIFICATE_P12 and not os.path.exists(
            ROOTIP_CLIENT_CERTIFICATE_P12
        ):
            raise FileNotFoundError(
                f"Error: The file {ROOTIP_CLIENT_CERTIFICATE_P12} does not exist."
            )
    except Exception as err:
        handle_secret_exception(err)


# 正規化されたエンドポイントURLを取得
def normalize_url(root_url, endpoint):
    # 先頭にhttps://を追加する
    if not root_url.startswith("https://"):
        root_url = f"https://{root_url}"

    # URLの末尾にスラッシュがある場合は削除する
    if root_url.endswith("/"):
        root_url = root_url[:-1]

    # endpointを結合して完全なURLを作成する
    url = f"{root_url}{endpoint}"

    return url


def make_request(method, endpoint, data=None, accept=None):
    # シークレットチェック
    check_secret()

    # エンドポイントを取得
    endpoint_url = normalize_url(ROOTIP_URL, endpoint)

    # 通信ヘッダ
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": ROOTIP_USER_ID,
        "X-API-Token": ROOTIP_API_KEY,
    }
    if accept:
        headers["Accept"] = accept

    try:
        # Create a session
        session = requests.Session()
        session.headers.update(headers)
        if ROOTIP_CLIENT_CERTIFICATE_PEM:
            # PEM形式の証明書を使用してセッションを作成
            response = session.request(
                method=method,
                url=endpoint_url,
                cert=ROOTIP_CLIENT_CERTIFICATE_PEM,
                data=data,
            )
        elif ROOTIP_CLIENT_CERTIFICATE_P12:
            # PKCS#12形式の証明書を使用してセッションを作成
            adapter = requests_pkcs12.Pkcs12Adapter(
                pkcs12_filename=ROOTIP_CLIENT_CERTIFICATE_P12,
                pkcs12_password=ROOTIP_CLIENT_CERTIFICATE_P12_PASSWORD,
            )
            session.mount("https://", adapter)
            response = session.request(
                method=method, url=endpoint_url, data=data, verify=False
            )
        else:
            return

        # ステータスコードが4xxまたは5xxの場合、HTTPError例外を発生させる
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # HTTPエラーの詳細を出力
        raise  # 例外を再スローすることで呼び出し元で処理できるようにする
    except Exception as err:
        print(f"An error occurred: {err}")  # その他のエラーの詳細を出力
        raise  # 例外を再スローすることで呼び出し元で処理できるようにする


# JSONをCSV配列に変換する関数
def json_to_csv_array(json_text):
    data = json.loads(json_text)
    output = StringIO()
    csv_writer = csv.writer(output)

    # ヘッダー行を書き込み
    header = data[0].keys()
    csv_writer.writerow(header)

    # データ行を書き込み
    for entry in data:
        csv_writer.writerow(entry.values())

    # 配列としてCSVを取得
    output.seek(0)
    csv_array = output.getvalue().splitlines()

    return csv_array


# JSONをCSVとして保存する関数
def json_to_csv_file(json_text, file_path):
    # JSON テキストをデコードしてデータを取得
    data = json.loads(json_text)

    # CSV ファイルにデータを書き込み
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        # BOM を書き込む
        file.write("\ufeff")

        csv_writer = csv.writer(file)

        # ヘッダー行を書き込み
        header = data[0].keys()
        csv_writer.writerow(header)

        # データ行を書き込み
        for entry in data:
            csv_writer.writerow(entry.values())


def ensure_directory_exists(file_path):
    # ディレクトリパスを取得
    directory = os.path.dirname(file_path)

    # ディレクトリが存在しない場合は作成する
    if not os.path.exists(directory):
        os.makedirs(directory)
