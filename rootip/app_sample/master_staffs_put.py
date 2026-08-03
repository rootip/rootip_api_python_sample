from rootip.api import make_request
import json

# 【注意】これはデータを書き換える更新系（PUT）のサンプルです
# - 実行前に、更新対象のid・値が正しいことを必ず確認してください
# - 最初はデモ・検証環境での実行を推奨します
# - 更新内容を表示し、人が確認（yes入力）してから実行する構成を保ってください

def main():
    """担当者マスタを1件だけ、確認後に更新するPUTサンプル。"""
    staff_id = None
    fax = None

    if staff_id is None or fax is None:
        raise ValueError(
            "staff_idとfaxをサンプル内へ設定してから実行してください。"
            "最初はデモ・検証環境を使用してください。"
        )

    endpoint = "/api/v1/master_staffs"

    # 更新前にGETし、対象IDが現在のマスタに1件だけ存在することを確認する
    current_response = make_request("GET", endpoint)
    current_staffs = current_response.json()
    if not isinstance(current_staffs, list):
        raise ValueError("APIレスポンスが想定した配列形式ではありません。")
    matched = [
        staff for staff in current_staffs
        if isinstance(staff, dict) and str(staff.get("id")) == str(staff_id)
    ]
    if len(matched) != 1:
        raise ValueError(
            f"更新対象IDの一致件数が{len(matched)}件のため処理を中止します。"
        )

    payload = {
        "id": staff_id,
        "fax": fax,
    }

    # 単件更新の前後値だけをローカル画面へ表示し、人が確認してから実行する
    print("以下の内容で担当者マスタを1件更新します")
    print(
        json.dumps(
            {
                "id": staff_id,
                "fax": {
                    "before": matched[0].get("fax"),
                    "after": fax,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    answer = input("よろしいですか？ (yes/no): ")
    if answer.strip().lower() != "yes":
        print("キャンセルしました。担当者マスタは更新していません")
        return

    response = make_request(
        "PUT", endpoint, json.dumps(payload)
    )

    # レスポンス本文は不必要に表示せず、結果のステータスのみ確認する
    print("Response status code:", response.status_code)


if __name__ == "__main__":
    main()
