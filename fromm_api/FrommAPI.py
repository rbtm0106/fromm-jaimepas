import uuid
import logging
from datetime import datetime, timezone

from util.signin import encrypt_password_for_signin
from util.utils import is_uuid
from .api.account_api import AccountAPI
from .api.channel_api import ChannelAPI
from .api.user_api import UserAPI
from .exceptions import ApiError

log = logging.getLogger(__name__)


class FrommAPI:
    """
    A unified API client that manages authentication state and provides
    access to all sub-APIs (Account, Channel, User).

    This object is designed to be serialized into and deserialized from
    a user's session cookie in a web app (e.g., Flask).
    """

    def __init__(self):
        # Public-facing API modules
        self.account = AccountAPI()
        self.channel = ChannelAPI()
        self.user = UserAPI()

        # Internal state
        self.device_id = None
        self.access_token = None
        self.refresh_token = None
        self.resource_token = None
        self.token_expiry = None

        self.profile = None  # To store user profile data
        self.user_agent_string = None
        self.device_info = None

    def signin(self, email, password,  device_id, user_agent_string, device_info):
        """
        Signs into the API using email and a pre-computed password hash.

        If successful, this method populates the client's internal state
        (access_token, etc.) and automatically configures the
        self.channel and self.user clients with the new token.

        Args:
            email (str): The user's email.
            password (str): The pre-hashed password.
            device_id: The device id
            user_agent_string
            device_info(dict)
        Returns:
            bool: True on success, False on failure.
        """
        if not device_id or not is_uuid(device_id):
            new_device_id = str(uuid.uuid4())
            log.info(f"Replacing device id {device_id} by {new_device_id} as it was not formatted correctly ")
            device_id = new_device_id
        self.device_id=device_id
        log.info(f"Attempting sign-in for {email} with device {self.device_id}")
        password_encrypted = encrypt_password_for_signin(password,self.device_id)
        try:
            # Pass the instance's device_id to the signin method
            response, access_token = self.account.signin(
                email,
                password_encrypted,
                self.device_id
            )

            if access_token:
                log.info("Sign-in successful. Storing tokens.")
                # Store all auth-related state
                self.access_token = access_token
                self.refresh_token = response.get('data', {}).get('refreshToken')
                self.resource_token = response.get('data', {}).get('resourceToken')
                self.user_agent_string = user_agent_string
                self.device_info = device_info

                expires_in_seconds = response.get('data', {}).get('expiresIn', 0)

                # 2. Calculate absolute timestamp (Now + Seconds)
                if expires_in_seconds:
                    current_time = datetime.now(timezone.utc).timestamp()
                    self.token_expiry = current_time + expires_in_seconds
                else:
                    self.token_expiry = None


                # Propagate the new token to the other API clients
                #TODO wrap everything in a single class
                self.channel.set_token(self.access_token)
                self.user.set_token(self.access_token)
                self.channel.set_user_agent_string(self.user_agent_string)
                self.user.set_user_agent_string(self.user_agent_string)
                self.channel.set_device_info(self.device_info)
                self.user.set_device_info(self.device_info)

                # Fetch and store profile
                profile_response = self.user.get_profile()
                if profile_response.get('success'):
                    self.profile = profile_response.get('data')
                else:
                    log.warning(f"Could not fetch profile: {profile_response}")
                    self.profile = None  # Ensure profile is None on failure

                return True
        except ApiError as e:
            log.error(f"Sign-in API error: {e}")
        except Exception as e:
            log.error(f"Sign-in failed: {e}")

        return False

    def signout(self):
        """
        Clears the internal authentication state.
        """
        log.info("Signing out. Clearing local tokens.")
        self.access_token = None
        self.refresh_token = None
        self.resource_token = None
        self.token_expiry = None
        self.profile = None
        self.device_id = None
        self.user_agent_string = None
        self.device_info = None

        # Clear tokens from sub-clients
        self.channel.set_token(None)
        self.user.set_token(None)
        self.channel.set_user_agent_string(None)
        self.user.set_user_agent_string(None)
        self.channel.set_device_info(None)
        self.user.set_device_info(None)

    def get_session_data(self):
        """
        Serializes the client's state into a dictionary
        safe for storing in a Flask session (cookie).
        """
        return {
            "device_id": self.device_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "resource_token": self.resource_token,
            "token_expiry": self.token_expiry,
            "profile": self.profile,
            "user_agent_string": self.user_agent_string,
            "device_info": self.device_info

        }

    @classmethod
    def from_session_data(cls, data):
        """
        Restores a client instance from a session data dictionary.

        Args:
            data (dict): The dictionary from get_session_data().

        Returns:
            FrommAPI: A new, configured FrommAPI instance.
        """
        api = cls()  # Create a new instance
        if not data:
            log.debug("No session data found, returning new API instance.")
            return api

        log.debug("Restoring API instance from session data.")
        # Restore all state
        api.device_id = data.get("device_id")
        api.access_token = data.get("access_token")
        api.refresh_token = data.get("refresh_token")
        api.resource_token = data.get("resource_token")
        api.token_expiry = data.get("token_expiry")
        api.user_agent_string = data.get("user_agent_string")
        api.device_info = data.get("device_info")


        if api.access_token:
            api.channel.set_token(api.access_token)
            api.user.set_token(api.access_token)
            api.channel.set_user_agent_string(api.user_agent_string)
            api.user.set_user_agent_string(api.user_agent_string)
            api.channel.set_device_info(api.device_info)
            api.user.set_device_info(api.device_info)

        return api

    def is_token_expired(self):
        """Returns True if the token exists but the expiration time has passed."""
        if not self.access_token:
            return False  # No token to expire

        if not self.token_expiry:
            return True  # No expiry set, assume invalid

        current_time = datetime.now(timezone.utc).timestamp()
        # Check if current time is PAST the stored expiry time
        return current_time > self.token_expiry