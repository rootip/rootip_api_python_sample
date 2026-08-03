import json
import os

from rootip.api import make_request, json_to_csv_file, ensure_directory_exists


def main():
    """担当者マスタを、確認後にローカルCSVへ保存するサンプル。"""
    file_path = "tmp/master_staffs.csv"
    response = make_request("GET", "/api/v1/master_staffs")
    data = json.loads(response.text)
    if not isinstance(data, list):
        raise ValueError("APIレスポンスが想定した配列形式ではありません。")

    print("Response status code:", response.status_code)
    print("取得件数:", len(data))
    print(f"保存予定先: {os.path.abspath(file_path)}")
    print("注意: 担当者情報を含むため、保存後はアクセス権と保管期間を管理してください。")
    if os.name == "nt":
        print("Windowsでは保存先フォルダのACLが適切か、実行前に確認してください。")
    answer = input("上記データをCSVへ保存しますか？ (yes/no): ")
    if answer.strip().lower() != "yes":
        print("キャンセルしました。CSVは保存していません。")
        return

    ensure_directory_exists(file_path)
    json_to_csv_file(response.text, file_path)
    print(f"{len(data)}件をCSVへ保存しました。レスポンス本文は表示していません。")


if __name__ == "__main__":
    main()
