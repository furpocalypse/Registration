"""OAuth module."""
from collections.abc import Collection
from enum import Enum

from attrs import frozen
from oauthlib.oauth2 import RequestValidator
from oes.registration.auth.oauth.scope import DEFAULT_SCOPES, Scope
from oes.registration.models.config import Config


class GrantType(str, Enum):
    guest = "guest"


JS_CLIENT_ID = "oes"
"""The client ID of the JS frontend."""


@frozen
class Client:
    """An OAuth client."""

    id: str
    """The client ID."""

    redirect_urls: Collection[str] = ()
    """The allowed redirect URLs."""


class Validator(RequestValidator):
    def __init__(self, config: Config):
        self.config = config
        self.client = Client(id=JS_CLIENT_ID, redirect_urls=("TODO",))

    def validate_client_id(self, client_id, request, *args, **kwargs):
        """Validate the client ID."""
        if client_id == self.client.id:
            request.client = self.client
            return True
        return False

    def validate_redirect_uri(self, client_id, redirect_uri, request, *args, **kwargs):
        return redirect_uri in request.client.redirect_urls

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        return all(s in Scope for s in scopes)

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        return list(DEFAULT_SCOPES)

    def validate_response_type(
        self, client_id, response_type, client, request, *args, **kwargs
    ):
        return response_type == "token"

    def client_authentication_required(self, request, *args, **kwargs):
        return False

    def authenticate_client_id(self, client_id, request, *args, **kwargs):
        if client_id == self.client.id:
            request.client = self.client
            return True
        return False
