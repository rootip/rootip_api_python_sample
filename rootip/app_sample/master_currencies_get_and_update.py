import requests
import chardet
import csv
import json
import re
import math
from colorama import Fore, Style
from rootip.api import make_request, json_to_csv_array
from datetime import datetime

# rootipAPIで通貨マスタを取得
def get_current_currencies():
    method = "GET"
    endpoint = "/api/v1/master_currencies"
    response = make_request(method, endpoint)

    return json_to_csv_array(response.text)

# 外部サイトから通貨レート、レート日付を取得
# 有効小数点桁数を指定して通貨レートを取得
def get_currency_rate(decimal_places=2):
    url = "https://www.bk.mufg.jp/gdocs/kinri/list_j/kinri/spot_rate.csv"
    response = requests.get(url)
    response.raise_for_status()  # エラーチェック

    # エンコーディングの検出
    result = chardet.detect(response.content)
    encoding = result["encoding"]
    # print(f"Detected encoding: {encoding}")

    # CSVデータを検出されたエンコーディングでデコード
    csv_data = response.content.decode(encoding).splitlines()
    reader = csv.reader(csv_data)
    data_array = list(reader)

    # 最終更新日時を取得
    date_obj = None
    last_updated = None
    for row in data_array:
        if "最終更新日時" in row[-1]:
            last_updated = row[-1].split("：")[1]
            # YYYY/MM/DD部分を抽出する正規表現
            match = re.search(r"(\d{4}/\d{2}/\d{2})", last_updated)
            if match:
                date_str = match.group(1)
                # 日付文字列をdatetimeオブジェクトに変換
                date_obj = datetime.strptime(date_str, "%Y/%m/%d")
                # datetimeオブジェクトを指定のフォーマットに変換
                update_date_iso = date_obj.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")
            break

    # 必要な列を抽出
    # 2行目をヘッダーとして使用し、3行目以降がデータ
    headers = data_array[2]
    data = data_array[3:]

    # 通貨名、TTS、TTBの列インデックスを取得
    currency_idx = headers.index("通貨名")
    tts_idx = headers.index("T.T.S.")
    ttb_idx = headers.index("T.T.B.")

    # 通貨名、TTS、TTBの配列を取得
    currency_data = []
    for row in data:
        if row[currency_idx] == "":
            break

        # 通貨コードのみを抽出（アルファベット3文字）
        currency_code = row[currency_idx].strip()[:3]
        tts = row[tts_idx].strip()
        ttb = row[ttb_idx].strip()

        # TTSとTTBが数字であることを確認
        if (
            not tts.replace(".", "", 1).isdigit()
            or not ttb.replace(".", "", 1).isdigit()
        ):
            continue

        # 小数点以下の桁数を指定し切り捨て
        factor = 10**decimal_places
        tts = math.floor(float(tts) * factor) / factor
        ttb = math.floor(float(ttb) * factor) / factor

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
            "rate_buy": float(row["rate_buy"]),
            "rate_sell": float(row["rate_sell"]),
            "date_currency_rate": row["date_currency_rate"],
        }

    # レートが異なる通貨を見つける
    different_rates = []
    for code, tts, ttb in currency_rate:
        if code in master_dict:
            master_rate_sell = master_dict[code]["rate_sell"]
            master_rate_buy = master_dict[code]["rate_buy"]
            date_currency_rate = master_dict[code]["date_currency_rate"]
            if (
                master_rate_sell != float(tts)
                or master_rate_buy != float(ttb)
                or date_currency_rate != update_date_iso
            ):
                different_rates.append(
                    {
                        "id": master_dict[code]["id"],
                        "code": code,
                        "master_rate_sell": master_rate_sell,
                        "master_rate_buy": master_rate_buy,
                        "external_rate_sell": float(tts),
                        "external_rate_buy": float(ttb),
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

    print(f"[root ip API] {Fore.WHITE}通貨 {Fore.CYAN}{rate['code']} {Fore.WHITE}を更新します...")
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
            "rate_buy": rate['external_rate_buy'],
            "rate_sell": rate['external_rate_sell'],
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
    print("外部APIから為替情報を取得します...")
    last_updated, update_date_iso, currency_rate = get_currency_rate(1)
    print(f"{Fore.GREEN}  OK!{Style.RESET_ALL}")
    print(f"  外国為替相場一覧表最終更新日時：{Fore.CYAN}{last_updated}{Style.RESET_ALL}\n")

    # 通貨レートの比較
    different_rates = compare_currency_rates(master_currencies, currency_rate, update_date_iso)

    # 通貨マスタのアップデート
    for rate in different_rates:
        print_rate_change(rate, update_date_iso)
        if update_rate(rate, update_date_iso):
            print(f"  {Fore.GREEN}OK:{Style.RESET_ALL} 通貨マスタアップデート成功！\n")
        else:
            print(f"  {Fore.RED}NG:{Style.RESET_ALL} 通貨マスタアップデート失敗\n")

if __name__ == "__main__":
    main()
