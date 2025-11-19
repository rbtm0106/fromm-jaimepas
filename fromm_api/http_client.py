import requests
import logging
from .exceptions import ApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class HttpClient:
    """
    A centralized HTTP client to manage requests, sessions, and authentication.
    """

    def __init__(self, base_url, auth_prefix=""):
        """
        Initializes the client.

        Args:
            base_url (str): The base URL for this API (e.g., "https://account-api.frommyarti.com")
            auth_prefix (str): A prefix for the Authorization header, e.g., "Bearer ".
                               Leave empty if no prefix is needed.
        """
        self.base_url = base_url
        self.auth_prefix = auth_prefix
        self.auth_token = None
        self.session = requests.Session()

    def set_token(self, token):
        """
        Sets the authentication token for this client instance.
        """
        self.auth_token = token
        log.info(f"Token set for {self.base_url}")

    def _request(self, method, endpoint, headers, params=None, json=None):
        """
        Internal method to make an API request.
        """
        url = self.base_url + endpoint

        # Prepare authorization header
        auth_header = {}
        if self.auth_token:
            auth_header = {"Authorization": f"{self.auth_prefix}{self.auth_token}".strip()}

        # Merge headers: priority is request-specific > auth > session-default
        full_headers = {**self.session.headers, **auth_header, **headers}

        try:
            log.debug(f"Request: {method} {url}")
            log.debug(f"Headers: {full_headers}")
            log.debug(f"Params: {params}")
            log.debug(f"JSON: {json}")

            response = self.session.request(
                method=method,
                url=url,
                headers=full_headers,
                params=params,
                json=json
            )

            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()

            # Try to return JSON, fall back to text if empty or invalid
            try:
                return response.json()
            except requests.exceptions.JSONDecodeError:
                log.warning(f"Response for {url} was not valid JSON. Returning text.")
                return response.text

        except requests.exceptions.RequestException as e:
            log.error(f"API call failed: {e}")
            raise ApiError(f"API call to {url} failed: {e}") from e

    # Public convenience methods (GET, POST, etc.)

    def get(self, endpoint, headers, params=None):
        return self._request("GET", endpoint, headers=headers, params=params)

    def post(self, endpoint, headers, data=None, json=None):
        # Note: requests distinguishes between form data (data) and json payload (json)
        # Your examples all use 'json', so we default to that.
        return self._request("POST", endpoint, headers=headers, params=None, json=json)

    def put(self, endpoint, headers, data=None, json=None):
        return self._request("PUT", endpoint, headers=headers, params=None, json=json)

    def delete(self, endpoint, headers, params=None):
        return self._request("DELETE", endpoint, headers=headers, params=params)