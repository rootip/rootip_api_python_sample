import sys
import os
import re
import json
import csv
from io import StringIO
from urllib.parse import urlsplit

import requests
import requests_pkcs12

# 秘密情報の読み込み
# config/secrets.py が未作成でも本モジュールの読み込み自体は失敗させず、
# 実行時（check_secret）にわかりやすいエラーを表示する
try:
    from config import secrets as _secrets
except ImportError:
    _secrets = None

ROOTIP_USER_ID = getattr(_secrets, "ROOTIP_USER_ID", "")
ROOTIP_API_KEY = getattr(_secrets, "ROOTIP_API_KEY", "")
ROOTIP_URL = getattr(_secrets, "ROOTIP_URL", "")
ROOTIP_CLIENT_CERTIFICATE_P12 = getattr(_secrets, "ROOTIP_CLIENT_CERTIFICATE_P12", "")
ROOTIP_CLIENT_CERTIFICATE_P12_PASSWORD = getattr(
    _secrets, "ROOTIP_CLIENT_CERTIFICATE_P12_PASSWORD", ""
)
ROOTIP_CLIENT_CERTIFICATE_PEM = getattr(_secrets, "ROOTIP_CLIENT_CERTIFICATE_PEM", "")
# 社内プロキシ等で独自CA証明書が必要な場合のみ設定する（通常は空のままでよい）
ROOTIP_CA_BUNDLE = getattr(_secrets, "ROOTIP_CA_BUNDLE", "")

# 通信タイムアウト（接続, 読み取り）秒
REQUEST_TIMEOUT = (5, 30)

# このサンプルから実行を許可するHTTPメソッド
# DELETEは誤操作・AI生成コードの暴走時の影響が大きいため許可しない
ALLOWED_METHODS = ("GET", "POST", "PUT")

# 認証情報とクライアント証明書を送信してよいrootip公式ホスト
# 独自ドメインを利用する契約では、rootipサポート確認後にここへ追加する
ALLOWED_ROOTIP_HOST_SUFFIXES = (".rootip-cloud.net",)

# CSV変換で一度に処理する最大レコード数
MAX_JSON_RECORDS = 10_000

# rootip APIレスポンス本文の最大サイズ
MAX_RESPONSE_BYTES = 10 * 1024 * 1024


# シークレットの例外処理
def handle_secret_exception(exception):
    # エラーメッセージを表示
    print(f"Exception: {exception}")
    # プログラムを終了させる
    sys.exit(1)


# シークレットのチェック
def check_secret():
    try:
        if _secrets is None:
            raise ValueError(
                "Error: config/secrets.py が見つかりません。"
                "config/secrets.py.template をコピーして config/secrets.py を作成してください。"
            )

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
                "Error: ROOTIP_CLIENT_CERTIFICATE_PEMで指定したファイルが見つかりません。"
            )

        if ROOTIP_CLIENT_CERTIFICATE_P12 and not os.path.exists(
            ROOTIP_CLIENT_CERTIFICATE_P12
        ):
            raise FileNotFoundError(
                "Error: ROOTIP_CLIENT_CERTIFICATE_P12で指定したファイルが見つかりません。"
            )

        if ROOTIP_CA_BUNDLE and not os.path.exists(ROOTIP_CA_BUNDLE):
            raise FileNotFoundError(
                "Error: ROOTIP_CA_BUNDLEで指定したファイルが見つかりません。"
            )
    except Exception as err:
        handle_secret_exception(err)


# 正規化されたエンドポイントURLを取得
# https以外のスキーム、URL内の認証情報、想定外のパスやクエリは受け付けない
def normalize_url(root_url, endpoint):
    # スキームがない場合はhttps://を補う
    if "://" not in root_url:
        root_url = f"https://{root_url}"

    parsed = urlsplit(root_url)

    # httpなどhttps以外での接続は許可しない（通信内容・認証情報保護のため）
    if parsed.scheme != "https":
        raise ValueError(f"Error: ROOTIP_URLはhttpsで指定してください: {root_url}")

    if not parsed.hostname:
        raise ValueError(f"Error: ROOTIP_URLのホスト名を確認してください: {root_url}")

    hostname = parsed.hostname.lower().rstrip(".")
    if not any(hostname.endswith(suffix) for suffix in ALLOWED_ROOTIP_HOST_SUFFIXES):
        raise ValueError(
            "Error: ROOTIP_URLはrootip公式ホスト（*.rootip-cloud.net）を指定してください。"
            "独自ドメインを利用する場合はrootipサポートへ確認してください。"
        )

    try:
        port = parsed.port
    except ValueError as err:
        raise ValueError("Error: ROOTIP_URLのポート指定が不正です。") from err
    if port not in (None, 443):
        raise ValueError("Error: ROOTIP_URLで許可されるポートは443のみです。")

    # URLへのID・パスワード埋め込み、クエリ、フラグメント、余分なパスは受け付けない
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != ""
    ):
        raise ValueError(
            f"Error: ROOTIP_URLはホスト名のみのURLで指定してください（例 https://xxx.rootip-cloud.net）: {root_url}"
        )

    # エンドポイントはこのAPIのパス配下のみに限定する
    # （外部データ由来の文字列で任意のURLへ接続してしまう事故を防ぐ）
    # パス部分は英数字・ハイフン・アンダースコア・スラッシュのみを許可することで、
    # 「/api/../admin」のようなパスの遡り、%エンコード、絶対URL、制御文字をすべて拒否する
    path, _, query = str(endpoint).partition("?")
    if not re.fullmatch(r"/api/[A-Za-z0-9_/-]+", path):
        raise ValueError(f"Error: エンドポイントの形式が不正です: {endpoint}")
    if query and not re.fullmatch(r"[A-Za-z0-9_.=&%-]+", query):
        raise ValueError(f"Error: エンドポイントのクエリ形式が不正です: {endpoint}")

    # 検証済みホスト名でURLを再構築し、表記ゆれを正規化する
    authority = hostname if port is None else f"{hostname}:{port}"
    url = f"https://{authority}{endpoint}"

    return url


def _load_limited_response_content(response):
    """成功レスポンスを上限付きで読み込み、通常のresponse.text/json()を利用可能にする。"""
    chunks = []
    received = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        received += len(chunk)
        if received > MAX_RESPONSE_BYTES:
            response.close()
            raise ValueError(
                f"Error: APIレスポンスが上限{MAX_RESPONSE_BYTES}バイトを超えました。"
            )
        chunks.append(chunk)

    # requests.Responseの公開アクセサ（text/json/content）が上限確認済み本文を使うよう保持する
    response._content = b"".join(chunks)
    response._content_consumed = True


def make_request(method, endpoint, data=None, accept=None):
    # HTTPメソッドのチェック
    # DELETE等、許可リスト外のメソッドはこのサンプルからは実行できない
    method = str(method).upper()
    if method not in ALLOWED_METHODS:
        raise ValueError(
            f"Error: このサンプルではHTTPメソッド {method} は実行できません。"
            f"許可メソッド: {', '.join(ALLOWED_METHODS)}"
        )

    # シークレットチェック
    check_secret()

    # エンドポイントを取得
    endpoint_url = normalize_url(ROOTIP_URL, endpoint)

    # サーバ証明書の検証設定
    # 検証は常に有効。社内CAが必要な環境のみROOTIP_CA_BUNDLEを指定する
    # ※TLSエラーが出ても verify=False にはしないこと（通信の安全性が失われます）
    verify = ROOTIP_CA_BUNDLE if ROOTIP_CA_BUNDLE else True

    # 通信ヘッダ
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": ROOTIP_USER_ID,
        "X-API-Token": ROOTIP_API_KEY,
    }
    if accept:
        headers["Accept"] = accept

    try:
        # セッションを確実に閉じ、接続リソースを解放する
        with requests.Session() as session:
            session.headers.update(headers)
            if ROOTIP_CLIENT_CERTIFICATE_PEM:
                # PEM形式の証明書を使用してセッションを作成
                response = session.request(
                    method=method,
                    url=endpoint_url,
                    cert=ROOTIP_CLIENT_CERTIFICATE_PEM,
                    data=data,
                    verify=verify,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=False,
                    stream=True,
                )
            elif ROOTIP_CLIENT_CERTIFICATE_P12:
                # PKCS#12形式の証明書を使用してセッションを作成
                adapter = requests_pkcs12.Pkcs12Adapter(
                    pkcs12_filename=ROOTIP_CLIENT_CERTIFICATE_P12,
                    pkcs12_password=ROOTIP_CLIENT_CERTIFICATE_P12_PASSWORD,
                )
                # クライアント証明書をrootipの接続先だけに提示する
                session.mount(f"https://{urlsplit(endpoint_url).netloc}/", adapter)
                response = session.request(
                    method=method,
                    url=endpoint_url,
                    data=data,
                    verify=verify,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=False,
                    stream=True,
                )
            else:
                raise RuntimeError("Error: クライアント証明書が設定されていません。")

            # 予期しないリダイレクト応答は追跡せずエラーにする
            if 300 <= response.status_code < 400:
                raise requests.exceptions.HTTPError(
                    f"Unexpected redirect response: {response.status_code}",
                    response=response,
                )

            # ステータスコードが4xxまたは5xxの場合、本文を表示せず例外にする
            response.raise_for_status()
            _load_limited_response_content(response)

        return response
    except requests.exceptions.SSLError:
        # 証明書検証エラーは原因の確認方法を案内する（検証の無効化はしない）
        print(
            "TLS証明書を検証できませんでした。verify=Falseでの回避はせず、"
            "接続先URL・社内プロキシの有無・PCの時刻設定を確認してください。"
            "社内CAが必要な環境ではROOTIP_CA_BUNDLEを設定してください。"
        )
        raise
    except requests.exceptions.HTTPError as http_err:
        status = (
            http_err.response.status_code
            if http_err.response is not None
            else "unknown"
        )
        print(f"HTTP error occurred (status={status})")
        raise  # 例外を再スローすることで呼び出し元で処理できるようにする
    except Exception as err:
        print(f"Request failed: {type(err).__name__}")
        raise  # 例外を再スローすることで呼び出し元で処理できるようにする


# Excel等の表計算ソフトで数式として解釈される値を無害化する
# （CSVインジェクション対策。=、+、-、@、タブで始まる値の先頭に'を付ける）
def sanitize_csv_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value


# JSONをCSV配列に変換する関数
def json_to_csv_array(json_text):
    data = json.loads(json_text)
    if not data:
        raise ValueError("Error: 変換対象のデータがありません。")
    if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
        raise ValueError("Error: JSONはオブジェクトの配列である必要があります。")
    if len(data) > MAX_JSON_RECORDS:
        raise ValueError(
            f"Error: 変換対象が上限{MAX_JSON_RECORDS}件を超えています。"
        )
    output = StringIO()
    csv_writer = csv.writer(output)

    # ヘッダー行を書き込み
    header = list(data[0].keys())
    csv_writer.writerow(header)

    # データ行を書き込み
    for entry in data:
        csv_writer.writerow([sanitize_csv_value(entry.get(key)) for key in header])

    # 配列としてCSVを取得
    output.seek(0)
    csv_array = output.getvalue().splitlines()

    return csv_array


# JSONをCSVとして保存する関数
def json_to_csv_file(json_text, file_path):
    # JSON テキストをデコードしてデータを取得
    data = json.loads(json_text)
    if not data:
        raise ValueError("Error: 変換対象のデータがありません。")
    if not isinstance(data, list) or not all(isinstance(entry, dict) for entry in data):
        raise ValueError("Error: JSONはオブジェクトの配列である必要があります。")
    if len(data) > MAX_JSON_RECORDS:
        raise ValueError(
            f"Error: 変換対象が上限{MAX_JSON_RECORDS}件を超えています。"
        )

    # CSVを所有者だけが読み書きできる権限で作成する
    file_descriptor = os.open(
        file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
    )
    with os.fdopen(
        file_descriptor, "w", newline="", encoding="utf-8"
    ) as file:
        if os.name != "nt":
            os.chmod(file_path, 0o600)
        # BOM を書き込む
        file.write("\ufeff")

        csv_writer = csv.writer(file)

        # ヘッダー行を書き込み
        header = list(data[0].keys())
        csv_writer.writerow(header)

        # データ行を書き込み
        for entry in data:
            csv_writer.writerow([sanitize_csv_value(entry.get(key)) for key in header])


def ensure_directory_exists(file_path):
    # ディレクトリパスを取得
    directory = os.path.dirname(file_path)

    # ディレクトリが存在しない場合は作成する
    if not os.path.exists(directory):
        os.makedirs(directory)
