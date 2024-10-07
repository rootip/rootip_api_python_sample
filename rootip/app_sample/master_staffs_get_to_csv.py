from rootip.api import make_request, json_to_csv_file, ensure_directory_exists

# Example usage
method = "GET"
endpoint = "/api/v1/master_staffs"
response = make_request(method, endpoint)

print("Response status code:", response.status_code)
print("Response content:", response.text)

# CSVファイルに書き込む
file_path = "tmp/master_staffs.csv"
ensure_directory_exists(file_path)
json_to_csv_file(response.text, "tmp/master_staffs.csv")
