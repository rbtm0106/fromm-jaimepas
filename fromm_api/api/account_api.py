import uuid
from ..http_client import HttpClient
from ..headers import get_base_app_headers


class AccountAPI:
    """
    Handles authentication and account-related endpoints.
    Base URL: https://account-api.frommyarti.com
    """

    def __init__(self):
        # Auth prefix is empty because these calls don't need auth
        self.client = HttpClient(
            base_url="https://account-api.frommyarti.com",
            auth_prefix=""
        )

    def check_user_exists(self, email):
        """
        Checks if a user exists.
        POST /auth/exist
        """
        headers = get_base_app_headers()
        payload = {"username": email}
        return self.client.post("/auth/exist", headers=headers, json=payload)

    def signin(self, email, password_encrpted, device_id):
        """
        Signs into the account.
        POST /auth/signin

        Returns:
            tuple: (full_api_response, access_token)
                   The access_token can be used to set tokens on other clients.
        """
        headers = get_base_app_headers()
        # Add the dynamic uuid to the headers for this request
        headers['uuid'] = device_id

        payload = {
            "username": email,
            "password": password_encrpted,
            "deviceId": device_id,
            "from": "app",
            "allowUpdateDeviceId": True
        }

        response = self.client.post("/auth/signin", headers=headers, json=payload)

        # Extract the access token to be used by other API clients
        access_token = None
        if response.get("success"):
            access_token = response.get("data", {}).get("accessToken")

        return response, access_token