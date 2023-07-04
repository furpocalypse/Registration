"""OAuth views."""
import asyncio

from blacksheep import Content, FromForm, Request, Response, allow_anonymous
from blacksheep.server.openapi.common import RequestBodyInfo
from oes.registration.app import app
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.credential_service import (
    CredentialService,
    create_new_refresh_token,
    create_refresh_token_entity,
)
from oes.registration.auth.oauth.token import TokenResponse
from oes.registration.auth.oauth.user import User
from oes.registration.auth.oauth.validator import CustomServer
from oes.registration.database import transaction
from oes.registration.docs import docs, docs_helper
from oes.registration.models.config import Config
from oes.registration.util import get_now


@allow_anonymous()
@app.router.post("/auth/oauth/create-account")
@docs_helper(
    response_type=TokenResponse,
    tags=["OAuth"],
)
@transaction
async def new_account_endpoint(
    account_service: AccountService,
    credential_service: CredentialService,
    config: Config,
) -> TokenResponse:
    """Create a new account, without credentials."""
    new_account = await account_service.create_account(None)
    user = User(
        id=new_account.id,
        email=new_account.email,
    )

    # TODO: when to get default scopes?
    refresh_token = create_new_refresh_token(user)
    refresh_token_entity = create_refresh_token_entity(refresh_token)
    await credential_service.create_credential(refresh_token_entity)

    now = get_now(seconds_only=True)
    access_token = refresh_token.create_access_token()
    expires_in = int((access_token.exp - now).total_seconds())

    return TokenResponse.create(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        key=config.auth.signing_key,
    )


@allow_anonymous()
@app.router.post(
    "/auth/oauth/token",
)
@docs(
    request_body=RequestBodyInfo(
        examples={
            "application/x-www-form-urlencoded": {
                "client_id": "oes",
                "grant_type": "refresh_token",
                "refresh_token": "...",
            }
        }
    ),
    tags=["OAuth"],
)
@transaction
async def token_endpoint(
    request: Request,
    form: FromForm,
    config: Config,
    account_service: AccountService,
    credential_service: CredentialService,
) -> Response:
    """OAuth token endpoint."""
    loop = asyncio.get_running_loop()
    server = CustomServer(config.auth, account_service, credential_service, loop)
    headers = {k.decode(): v.decode() for k, v in request.headers.items()}

    resp_headers, resp_body, resp_status = await asyncio.to_thread(
        server.create_token_response,
        str(request.url),
        "POST",
        form.value,
        headers,
    )

    response = Response(
        resp_status,
        [(k.encode(), v.encode()) for k, v in resp_headers.items()],
        Content(b"application/json", resp_body.encode()),
    )
    return response
