from rootip.api import make_request


def main():
    """案件書誌の件数のみを安全に確認するGETサンプル。"""
    response = make_request("GET", "/api/v1/case_biblios")
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("APIレスポンスが想定した配列形式ではありません。")

    print("Response status code:", response.status_code)
    print("取得件数:", len(data))
    print("レスポンス本文は機密情報保護のため表示しません。")


if __name__ == "__main__":
    main()
