"""oauthlib request validator module."""
import asyncio
from enum import Enum
from typing import Optional

import jwt
from oauthlib.common import Request
from oauthlib.oauth2 import RequestValidator, Server
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.credential_service import (
    CredentialService,
    create_new_refresh_token,
    create_refresh_token_entity,
    validate_refresh_token,
)
from oes.registration.auth.oauth.client import Client, get_js_client
from oes.registration.auth.oauth.scope import DEFAULT_SCOPES, Scope, Scopes
from oes.registration.auth.oauth.token import AccessToken, RefreshToken
from oes.registration.auth.oauth.user import User
from oes.registration.models.config import AuthConfig


class GrantType(str, Enum):
    """OAuth grant types."""

    refresh_token = "refresh_token"


class CustomValidator(RequestValidator):
    _auth_config: AuthConfig
    _account_service: AccountService
    _credential_service: CredentialService
    _clients: dict[str, Client]
    _loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        auth_config: AuthConfig,
        account_service: AccountService,
        credential_service: CredentialService,
        loop: asyncio.AbstractEventLoop,
    ):
        self._auth_config = auth_config
        self._account_service = account_service
        self._credential_service = credential_service
        self._loop = loop

        js_client = get_js_client(auth_config)
        self._clients = {
            js_client.id: js_client,
        }

    def validate_client_id(
        self, client_id: str, request: Request, *args, **kwargs
    ) -> bool:
        client = self._clients.get(client_id)
        if client is None:
            return False
        request.client = client
        return True

    def validate_redirect_uri(
        self, client_id: str, redirect_uri: str, request: Request, *args, **kwargs
    ) -> bool:
        client = self._clients.get(client_id)
        return client is not None and redirect_uri in client.redirect_uris

    def get_default_redirect_uri(
        self, client_id: str, request: Request, *args, **kwargs
    ):
        return None

    def validate_scopes(
        self,
        client_id: str,
        scopes: list[str],
        client: Client,
        request: Request,
        *args,
        **kwargs
    ) -> bool:
        return all(s in Scope.__members__.values() for s in scopes)

    def get_default_scopes(
        self, client_id: str, request: Request, *args, **kwargs
    ) -> list[str]:
        return list(DEFAULT_SCOPES)

    def validate_response_type(
        self,
        client_id: str,
        response_type: str,
        client: Client,
        request: Request,
        *args,
        **kwargs
    ) -> bool:
        return response_type == "code"  # TODO

    def client_authentication_required(self, request: Request, *args, **kwargs) -> bool:
        return False

    def authenticate_client_id(
        self, client_id: str, request: Request, *args, **kwargs
    ) -> bool:
        client = self._clients.get(client_id)
        if client is None:
            return False
        request.client = client
        return True

    def validate_grant_type(
        self,
        client_id: str,
        grant_type: str,
        client: Client,
        request: Request,
        *args,
        **kwargs
    ) -> bool:
        # TODO
        return grant_type == GrantType.refresh_token

    def save_bearer_token(
        self, token: dict, request: Request, *args, **kwargs
    ) -> Optional[str]:
        if isinstance(request.refresh_token, RefreshToken) and "refresh_token" in token:
            entity = create_refresh_token_entity(request.refresh_token)
            fut = asyncio.run_coroutine_threadsafe(
                self._credential_service.update_credential(entity), self._loop
            )
            fut.result()
        return None

    def validate_bearer_token(
        self, token: str, scopes: list[str], request: Request
    ) -> bool:
        try:
            access_token = AccessToken.decode(token, key=self._auth_config.signing_key)
        except jwt.InvalidTokenError:
            return False

        res = any(t in scopes for t in access_token.scope)

        if res:
            client = self._clients.get(access_token.azp) if access_token.azp else None
            if client is not None:
                request.client = client

            request.scopes = list(access_token.scope)
            request.access_token = access_token
            request.user = access_token.user

        return res

    def validate_refresh_token(
        self, refresh_token: str, client: Client, request: Request, *args, **kwargs
    ) -> bool:
        fut = asyncio.run_coroutine_threadsafe(
            validate_refresh_token(
                refresh_token,
                account_service=self._account_service,
                key=self._auth_config.signing_key,
            ),
            self._loop,
        )
        refresh_token_obj = fut.result()
        if refresh_token_obj is None:
            return False

        # Check azp/client ID
        if refresh_token_obj.azp is not None and refresh_token_obj.azp != client.id:
            return False

        request.user = refresh_token_obj.user
        request.refresh_token = refresh_token_obj
        return True

    def get_original_scopes(
        self, refresh_token: str, request: Request, *args, **kwargs
    ) -> list[str]:
        if isinstance(request.refresh_token, RefreshToken):
            return list(request.refresh_token.scope)
        else:
            return []


class CustomServer(Server):
    _auth_config: AuthConfig
    _account_service: AccountService
    _credential_service: CredentialService
    _loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        auth_config: AuthConfig,
        account_service: AccountService,
        credential_service: CredentialService,
        loop: asyncio.AbstractEventLoop,
    ):
        super().__init__(
            request_validator=CustomValidator(
                auth_config, account_service, credential_service, loop
            ),
            token_generator=self._generate_access_token,
            refresh_token_generator=self._generate_refresh_token,
        )

        self._auth_config = auth_config
        self._account_service = account_service
        self._credential_service = credential_service
        self._loop = loop

    def _generate_access_token(self, request: Request) -> str:
        assert isinstance(request.refresh_token, RefreshToken)
        access_token = request.refresh_token.create_access_token(
            scope=Scopes(request.scopes)
        )
        return access_token.encode(key=self._auth_config.signing_key)

    def _generate_refresh_token(self, request: Request) -> str:
        cur_token = request.refresh_token
        if isinstance(cur_token, RefreshToken):
            # Update the token
            refresh_token = cur_token.reissue_refresh_token()
        else:
            assert request.user is None or isinstance(request.user, User)
            refresh_token = create_new_refresh_token(
                request.user,
                # TODO: check allowed scopes
            )

        request.refresh_token = refresh_token
        return refresh_token.encode(key=self._auth_config.signing_key)
