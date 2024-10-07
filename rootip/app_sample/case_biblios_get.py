from rootip.api import make_request

# Example usage
method = "GET"
endpoint = "/api/v1/case_biblios"
response = make_request(method, endpoint)

print("Response status code:", response.status_code)
print("Response content:", response.text)
