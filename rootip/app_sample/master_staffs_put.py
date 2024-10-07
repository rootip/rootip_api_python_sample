from rootip.api import make_request
import json

# Example usage
method = "PUT"
endpoint = "/api/v1/master_staffs"

id = None
fax = None

if id is None or fax is None:
    raise ValueError("id and fax must be provided")

data = json.dumps(
    {
        "id": id,
        "fax": fax,
    }
)
response = make_request(method, endpoint, data)

print("Response status code:", response.status_code)
print("Response content:", response.text)
