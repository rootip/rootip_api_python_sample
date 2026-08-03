import requests
import csv
import json
import re
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from colorama import Fore, Style
from rootip.api import make_request, json_to_csv_array
from datetime import datetime

# 外部サイト（三菱UFJ銀行 公開為替相場CSV）の取得先URL
# 取得先はコード内に固定し、入力データや外部ファイルからURLを組み立てない
MUFG_SPOT_RATE_URL = "https://www.bk.mufg.jp/gdocs/kinri/list_j/kinri/spot_rate.csv"

# 外部CSVの最大サイズ（想定外の巨大データを読み込まないための上限）
MAX_SOURCE_BYTES = 1024 * 1024

# 外部CSVの最大行数
MAX_SOURCE_ROWS = 200

# 一度に更新できる件数の上限（想定外の大量更新を防ぐ）
MAX_UPDATES = 50

# 外部データとして許容するレートと変動幅の上限
MAX_RATE = Decimal("1000000")
MAX_RATE_CHANGE_RATIO = Decimal("0.5")

# rootipAPIで通貨マスタを取得
def get_current_currencies():
    method = "GET"
    endpoint = "/api/v1/master_currencies"
    response = make_request(method, endpoint)

    return json_to_csv_array(response.text)

# 外部サイトから通貨レート、レート日付を取得
# 有効小数点桁数を指定して通貨レートを取得
def get_currency_rate(decimal_places=2):
    # タイムアウトを設定し、リダイレクトは追跡しない
    # stream=Trueで受信しながらサイズを確認し、上限を超えた時点で打ち切る
    # （全体をメモリへ読み込んだ後の事後チェックでは巨大レスポンス対策にならないため）
    response = requests.get(
        MUFG_SPOT_RATE_URL,
        timeout=(5, 30),
        allow_redirects=False,
        stream=True,
    )
    try:
        if 300 <= response.status_code < 400:
            raise requests.exceptions.HTTPError(
                f"Unexpected redirect response: {response.status_code}",
                response=response,
            )
        response.raise_for_status()  # エラーチェック

        content_type = response.headers.get("Content-Type", "").lower()
        allowed_content_types = (
            "text/csv",
            "text/plain",
            "application/csv",
            "application/octet-stream",
        )
        if content_type and not any(
            allowed in content_type for allowed in allowed_content_types
        ):
            raise ValueError("為替CSVのContent-Typeが想定外のため処理を中止します")

        chunks = []
        received = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            received += len(chunk)
            if received > MAX_SOURCE_BYTES:
                raise ValueError("為替CSVのサイズが想定上限を超えたため処理を中止します")
            chunks.append(chunk)
        content = b"".join(chunks)
    finally:
        response.close()

    # このCSVはShift_JIS（cp932）で公開されているため、文字コードを固定してデコードする
    csv_data = content.decode("cp932").splitlines()
    if len(csv_data) > MAX_SOURCE_ROWS:
        raise ValueError("為替CSVの行数が想定上限を超えたため処理を中止します")
    reader = csv.reader(csv_data)
    data_array = list(reader)
    if len(data_array) < 4:
        raise ValueError("為替CSVの行数が不足しているため処理を中止します")

    # 最終更新日時を取得
    date_obj = None
    last_updated = None
    update_date_iso = None
    for row in data_array:
        if row and "最終更新日時" in row[-1] and "：" in row[-1]:
            last_updated = row[-1].split("：", 1)[1]
            # YYYY/MM/DD部分を抽出する正規表現
            match = re.search(r"(\d{4}/\d{2}/\d{2})", last_updated)
            if match:
                date_str = match.group(1)
                # 日付文字列をdatetimeオブジェクトに変換
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
                # datetimeオブジェクトを指定のフォーマットに変換
                update_date_iso = date_obj.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")
            break

    # 最終更新日時が取得できない場合、CSVの形式が変わった可能性があるため停止する
    if update_date_iso is None:
        raise ValueError("為替CSVの最終更新日時を確認できないため処理を中止します")

    # 必要な列を抽出
    # 2行目をヘッダーとして使用し、3行目以降がデータ
    headers = data_array[2]
    data = data_array[3:]

    # 通貨名、TTS、TTBの列インデックスを取得
    required_headers = ("通貨名", "T.T.S.", "T.T.B.")
    missing_headers = [header for header in required_headers if header not in headers]
    if missing_headers:
        raise ValueError(
            f"為替CSVに必須列がありません: {', '.join(missing_headers)}"
        )
    currency_idx = headers.index(required_headers[0])
    tts_idx = headers.index(required_headers[1])
    ttb_idx = headers.index(required_headers[2])
    max_column_index = max(currency_idx, tts_idx, ttb_idx)

    # 通貨名、TTS、TTBの配列を取得
    currency_data = []
    for row in data:
        if len(row) <= max_column_index:
            raise ValueError("為替CSVに列数が不足する行があるため処理を中止します")
        if row[currency_idx] == "":
            break

        # 通貨コードのみを抽出（アルファベット3文字）
        currency_code = row[currency_idx].strip()[:3]
        if not re.fullmatch(r"[A-Z]{3}", currency_code):
            raise ValueError("為替CSVの通貨コード形式が不正なため処理を中止します")

        # 金額計算は浮動小数点ではなくDecimalを使用する
        try:
            tts = Decimal(row[tts_idx].strip())
            ttb = Decimal(row[ttb_idx].strip())
        except InvalidOperation as err:
            raise ValueError("為替CSVのレート形式が不正なため処理を中止します") from err

        if not all(rate.is_finite() and 0 < rate <= MAX_RATE for rate in (tts, ttb)):
            raise ValueError("為替CSVのレートが許容範囲外のため処理を中止します")

        # 小数点以下の桁数を指定し切り捨て
        quantizer = Decimal("1").scaleb(-decimal_places)
        tts = tts.quantize(quantizer, rounding=ROUND_DOWN)
        ttb = ttb.quantize(quantizer, rounding=ROUND_DOWN)

        currency_data.append([currency_code, tts, ttb])

    return last_updated, update_date_iso, currency_data

# 通貨マスタと比較する関数
def compare_currency_rates(master_currencies, currency_rate, update_date_iso):
    # 通貨マスタのデータを辞書に変換
    master_dict = {}
    reader = csv.DictReader(master_currencies)
    for row in reader:
        master_dict[row["name"]] = {
            "id": row["id"],
            "rate_buy": Decimal(row["rate_buy"]),
            "rate_sell": Decimal(row["rate_sell"]),
            "date_currency_rate": row["date_currency_rate"],
        }

    # レートが異なる通貨を見つける
    different_rates = []
    for code, tts, ttb in currency_rate:
        if code in master_dict:
            master_rate_sell = master_dict[code]["rate_sell"]
            master_rate_buy = master_dict[code]["rate_buy"]
            date_currency_rate = master_dict[code]["date_currency_rate"]
            for label, current, external in (
                ("TTS", master_rate_sell, tts),
                ("TTB", master_rate_buy, ttb),
            ):
                if current > 0:
                    change_ratio = abs(external - current) / current
                    if change_ratio > MAX_RATE_CHANGE_RATIO:
                        raise ValueError(
                            f"{code}の{label}変動幅が上限"
                            f"{MAX_RATE_CHANGE_RATIO * 100}%を超えたため処理を中止します"
                        )
            if (
                master_rate_sell != tts
                or master_rate_buy != ttb
                or date_currency_rate != update_date_iso
            ):
                different_rates.append(
                    {
                        "id": master_dict[code]["id"],
                        "code": code,
                        "master_rate_sell": master_rate_sell,
                        "master_rate_buy": master_rate_buy,
                        "external_rate_sell": tts,
                        "external_rate_buy": ttb,
                        "date_currency_rate": master_dict[code]["date_currency_rate"],
                    }
                )
            else:
                print(f"{Fore.WHITE}通貨 {Fore.CYAN}{code}{Style.RESET_ALL} は更新の必要がありません")

    return different_rates

# 値の変化に応じて色を返す関数
def get_color(before, after):
    if after > before:
        return Fore.GREEN
    elif after < before:
        return Fore.RED
    else:
        return Fore.WHITE

# 日付を変換する関数
def format_iso_date(iso_date):
    # ISO 8601形式の日付をパース
    parsed_date = datetime.fromisoformat(iso_date[:-6])
    # パースした日付を yyyy-mm-dd 形式に変換
    return parsed_date.strftime('%Y-%m-%d')

# 通貨の変化を表示する関数
def print_rate_change(rate, update_date_iso):
    master_sell = rate['master_rate_sell']
    master_buy = rate['master_rate_buy']
    master_date = rate['date_currency_rate']
    external_sell = rate['external_rate_sell']
    external_buy = rate['external_rate_buy']
    tts_color = get_color(master_sell, external_sell)
    ttb_color = get_color(master_buy, external_buy)

    print(f"[root ip API] {Fore.WHITE}通貨 {Fore.CYAN}{rate['code']} {Fore.WHITE}を更新予定")
    print(f"  {Fore.YELLOW}TTS{Style.RESET_ALL}: {Fore.WHITE}{master_sell} {Fore.WHITE}=> {tts_color}{external_sell}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}TTB{Style.RESET_ALL}: {Fore.WHITE}{master_buy} {Fore.WHITE}=> {ttb_color}{external_buy}{Style.RESET_ALL}")
    print(f"  {Fore.YELLOW}レート更新日{Style.RESET_ALL}: {format_iso_date(master_date)} => {Fore.CYAN}{format_iso_date(update_date_iso)}{Style.RESET_ALL}")

# 通貨マスタを更新する関数
def update_rate(rate, update_date_iso):
    method = "PUT"
    endpoint = "/api/v1/master_currencies"
    data = json.dumps(
        {
            "id": rate["id"],
            "rate_buy": float(rate['external_rate_buy']),
            "rate_sell": float(rate['external_rate_sell']),
            "date_currency_rate": update_date_iso,
        }
    )
    response = make_request(method, endpoint, data)

    return response.status_code == 200

# メイン関数
def main():
    # 通貨マスタを取得
    print(f"[root ip API] 現在の通貨マスタを取得します...")
    master_currencies = get_current_currencies()
    print(f"{Fore.GREEN}  OK!{Style.RESET_ALL}\n")

    # 外部サイトから通貨レート、レート日付を取得
    print("外部サイト（三菱UFJ銀行の公開CSV）から為替情報を取得します...")
    last_updated, update_date_iso, currency_rate = get_currency_rate(1)
    print(f"{Fore.GREEN}  OK!{Style.RESET_ALL}")
    print(f"  外国為替相場一覧表最終更新日時：{Fore.CYAN}{last_updated}{Style.RESET_ALL}\n")

    # 通貨レートの比較
    different_rates = compare_currency_rates(master_currencies, currency_rate, update_date_iso)

    # 更新対象がない場合はここで終了
    if not different_rates:
        print("更新対象の通貨はありません")
        return

    # 想定外の大量更新を防ぐため、更新件数の上限を確認する
    if len(different_rates) > MAX_UPDATES:
        print(
            f"{Fore.RED}更新候補が{len(different_rates)}件あり、"
            f"上限{MAX_UPDATES}件を超えたため処理を中止します{Style.RESET_ALL}"
        )
        print("データを確認し、上限変更が必要な場合は管理者承認とコードレビューを行ってください")
        return

    # 更新内容を先にすべて表示し、人が確認してから更新を実行する
    for rate in different_rates:
        print_rate_change(rate, update_date_iso)
    print()
    answer = input(
        f"上記{len(different_rates)}件の通貨マスタを更新します。よろしいですか？ (yes/no): "
    )
    if answer.strip().lower() != "yes":
        print("キャンセルしました。通貨マスタは更新していません")
        return

    # 通貨マスタのアップデート。最初の失敗で中断し、自動再送しない
    completed = 0
    try:
        for rate in different_rates:
            print(f"[root ip API] {Fore.WHITE}通貨 {Fore.CYAN}{rate['code']} {Fore.WHITE}を更新します...")
            if not update_rate(rate, update_date_iso):
                raise RuntimeError(f"{rate['code']}の更新に失敗しました")
            completed += 1
            print(f"  {Fore.GREEN}OK:{Style.RESET_ALL} 通貨マスタアップデート成功！\n")
    except Exception:
        print(
            f"{Fore.RED}更新を中断しました。成功済み{completed}件、"
            f"未実行{len(different_rates) - completed}件です。"
            f"自動再送は行いません。{Style.RESET_ALL}"
        )
        raise

    print(f"更新完了: {completed}件")

if __name__ == "__main__":
    main()
