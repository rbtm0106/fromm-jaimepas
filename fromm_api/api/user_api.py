import uuid
from ..http_client import HttpClient
from ..headers import get_base_fromm_headers


class UserAPI:
    """
    Handles general user and chat endpoints.
    Base URL: https://api.frommyarti.com

    Note: Based on your examples, this API uses the "Bearer " prefix
    for its authentication token.
    """

    def __init__(self):
        self.client = HttpClient(
            base_url="https://api.frommyarti.com",
            auth_prefix="Bearer "  # Note the "Bearer " prefix
        )
        self.user_agent_string = None
        self.device_info = None


    def set_token(self, token):
        """Passes the token to the underlying HttpClient."""
        self.client.set_token(token)

    def get_using_ticket(self):
        """
        GET /v2/purchase/usingTicket/reader
        """
        headers = get_base_fromm_headers(self.device_info)
        headers['Host'] = 'api.frommyarti.com'

        return self.client.get("/v2/purchase/usingTicket/reader", headers=headers)

    def update_push_token(self, push_token, device_id):
        """
        POST /v2/user/pushToken
        """
        headers = get_base_fromm_headers(self.device_info)
        headers['Host'] = 'api.frommyarti.com'

        payload = {
            "token": push_token,
            "from": self.device_info.get("os").lower(),
            "deviceId": device_id,
            "vendor": "fcm"
        }

        return self.client.post("/v2/user/pushToken", headers=headers, json=payload)

    def get_chat_rooms(self):
        """
        GET /v2/chat/fanFriendAndChatRooms/reader
        """
        headers = get_base_fromm_headers(self.device_info)
        headers['Host'] = 'api.frommyarti.com'

        return self.client.get("/v2/chat/fanFriendAndChatRooms/reader", headers=headers)

    # You can add a method for the '/v2/user/profile/reader' endpoint here too
    def get_profile(self):
        """
        Gets the user's profile.
        GET /v2/user/fan/profile/reader
        (Path updated from /v2/profile/reader based on user feedback)
        """
        headers = get_base_fromm_headers(self.device_info)
        headers['Host'] = 'api.frommyarti.com'

        # Updated path from "/v2/profile/reader" to "/v2/user/fan/profile/reader"
        return self.client.get("/v2/user/fan/profile/reader", headers=headers)

    def set_user_agent_string(self, user_agent_string):
        self.user_agent_string = user_agent_string

    def set_device_info(self, device_info):
        self.device_info = device_info