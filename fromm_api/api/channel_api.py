import uuid
from ..http_client import HttpClient
from ..headers import get_base_web_headers


class ChannelAPI:
    """
    Handles channel-specific endpoints.
    Base URL: https://channel-api.frommyarti.com

    Note: Based on your code, this API seems to use the raw token
    without the "Bearer " prefix.
    """

    def __init__(self):
        self.client = HttpClient(
            base_url="https://channel-api.frommyarti.com",
            auth_prefix=""  # No "Bearer " prefix
        )
        self.user_agent_string = None
        self.device_info = None

    def set_token(self, token):
        """Passes the token to the underlying HttpClient."""
        self.client.set_token(token)


    def get_post(self, channel_id, post_id):
        """
        Gets details for a single post.
        GET /media/posts/{post_id}

        Updated to include full WebView headers (Origin, Referer, Timezone, Country)
        and specific mobile identifiers.
        """
        headers = get_base_web_headers(self.device_info, self.user_agent_string)

        # Merge the specific headers required by the new API log
        headers.update({
            'channel-id': channel_id,
            'Host': 'channel-api.frommyarti.com',
            'uuid': str(uuid.uuid4()),
            'Origin': 'https://channel.frommyarti.com',
            'Referer': 'https://channel.frommyarti.com/',
            'country': 'KR',
            'language': 'ko',
            'timezone': 'Asia/Seoul',
            'X-Requested-With': 'com.knowmerce.fromm.fan',
            'sec-ch-ua-platform': f'"{self.device_info["os"]}"',
            'sec-ch-ua-mobile': '?1'
        })


        return self.client.get(f"/media/posts/{post_id}", headers=headers)


    def get_posts(self, channel_id, limit=12, last_post=None):
        """
        Gets posts for a specific channel.
        GET /media/posts
        """
        headers = get_base_web_headers(self.device_info, self.user_agent_string)
        headers['channel-id'] = channel_id
        headers['Host'] = 'channel-api.frommyarti.com'
        headers['uuid'] = str(uuid.uuid4())

        params = {
            'labelId': '0',
            'channelId': channel_id,
            'limit': f'{limit}'
        }

        if last_post:
            params["postId"] = last_post["id"]
            params["num"] = last_post["num"]
            params["displayStartAt"] = last_post["displayStartAt"]

        return self.client.get("/media/posts", headers=headers, params=params)

    def get_channels(self):
        """
        Gets a list of all channels.
        GET /channels
        """
        headers = get_base_web_headers(self.device_info, self.user_agent_string)
        headers['Host'] = 'channel-api.frommyarti.com'
        headers['uuid'] = str(uuid.uuid4())

        return self.client.get("/channels", headers=headers)

    def subscribe_to_channel(self, channel_id):
        """
        Subscribes to a channel.
        POST /channels/{channel_id}/subscribe
        """
        headers = get_base_web_headers(self.device_info, self.user_agent_string)
        headers['Host'] = 'channel-api.frommyarti.com'
        headers['uuid'] = str(uuid.uuid4())
        headers['Content-Length'] = '0'  # Important for POST with no body

        return self.client.post(f"/channels/{channel_id}/subscribe", headers=headers, json=None)

    def set_user_agent_string(self, user_agent_string):
        self.user_agent_string = user_agent_string

    def set_device_info(self, device_info):
        self.device_info = device_info