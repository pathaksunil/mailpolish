# desktop/mailpolish_desktop/core/license_client.py
import requests

class LicenseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_status(self, user_id: str):
        response = requests.get(f"{self.base_url}/api/license/status/{user_id}")
        return response.json()