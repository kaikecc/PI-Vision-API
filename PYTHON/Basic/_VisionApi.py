import requests
import urllib3
from requests_kerberos import HTTPKerberosAuth
import json


# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class VisionApi:
    def __init__(self, url_endpoint):
        self.url_endpoint = url_endpoint

    def _request(self, method, custom_url, body=None):
        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        api_url = f"{self.url_endpoint}/{custom_url}"

        try:
            response = requests.request(
                method, api_url, auth=HTTPKerberosAuth(), headers=headers, 
                json=body, verify=False
            )

            if response.status_code == 200:
                return response.json()
            if response.status_code == 204:
                print(f"204: No content returned from the API: {api_url}")
                return {}
            if response.status_code in [400, 401, 404, 503]:
                print(f"{response.status_code} Error: {response.text} from the API: {api_url}")
                return {}
            print(f"Unexpected {response.status_code} Error: {response.text} from the API: {api_url}")
            return {}

        except requests.exceptions.RequestException as e:
            print(f"Connection Error while accessing the API: {api_url}: {e}")
            return {}

    def get_PiVisionApi(self, custom_url):
        return self._request("GET", custom_url)

    def update_PiVisionApi(self, custom_url, body):
        return self._request("PUT", custom_url, body)

