"""Auth credential service."""
import secrets
from datetime import datetime
from typing import Optional
from uuid import UUID

import jwt
from loguru import logger
from oes.registration.auth.account_service import AccountService
from oes.registration.auth.entities import CredentialEntity
from oes.registration.auth.models import CredentialType
from oes.registration.auth.oauth.scope import Scopes
from oes.registration.auth.oauth.token import (
    DEFAULT_REFRESH_TOKEN_LIFETIME,
    RefreshToken,
    converter,
)
from oes.registration.auth.oauth.user import User
from oes.registration.util import get_now
from sqlalchemy.ext.asyncio import AsyncSession


class CredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_credential(
        self, id: str, *, lock: bool = False
    ) -> Optional[CredentialEntity]:
        """Get a credential by ID."""
        return await self.db.get(CredentialEntity, id, with_for_update=lock)

    async def create_credential(self, entity: CredentialEntity) -> CredentialEntity:
        """Create the given :class:`CredentialEntity`."""
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update_credential(self, entity: CredentialEntity) -> CredentialEntity:
        """Merge the given credential with the data in the database."""
        merged = await self.db.merge(entity)
        return merged

    async def delete_credential(self, entity: CredentialEntity):
        """Delete the given credential."""
        await self.db.delete(entity)


def create_new_refresh_token(
    user: Optional[User],
    scope: Optional[Scopes] = None,
    expiration_date: Optional[datetime] = None,
) -> RefreshToken:
    """Create a new :class:`RefreshToken`.

    Args:
        user: The :class:`User`.
        scope: The scope of the token.
        expiration_date: A non-default expiration date.
    """
    credential_id = secrets.token_urlsafe()
    return RefreshToken.create(
        account_id=user.id if user is not None else None,
        credential_id=credential_id,
        token_num=1,
        scope=scope
        if scope is not None
        else user.scope
        if user is not None
        else Scopes(),
        email=user.email if user is not None else None,
        expiration_date=expiration_date
        if expiration_date is not None
        else (get_now() + DEFAULT_REFRESH_TOKEN_LIFETIME),
    )


def create_refresh_token_entity(token: RefreshToken) -> CredentialEntity:
    """Create a :class:`CredentialEntity` for a :class:`RefreshToken`."""
    return CredentialEntity(
        id=token.credential_id,
        account_id=UUID(token.sub) if token.sub is not None else None,
        type=CredentialType.refresh_token,
        date_created=token.iat if token.iat is not None else get_now(),
        date_updated=None,
        date_last_used=None,
        date_expires=token.exp,
        data=converter.unstructure(token),
    )


async def validate_refresh_token(
    refresh_token_str: str,
    *,
    account_service: AccountService,
    key: str,
) -> Optional[RefreshToken]:
    """Validate a refresh token.

    Decodes/verifies the refresh token. Revokes all refresh tokens if an old token is
    re-used.

    Args:
        refresh_token_str: The refresh token string.
        account_service: The :class:`AccountService`.
        key: The signing key.

    Returns:
        The decoded :class:`RefreshToken`, or ``None`` if not valid.
    """
    try:
        dec_refresh_token = RefreshToken.decode(refresh_token_str, key=key)
    except jwt.InvalidTokenError:
        return None

    account_id = UUID(dec_refresh_token.sub) if dec_refresh_token.sub else None

    account = (
        (
            await account_service.get_account(
                account_id, with_credentials=True, lock=True
            )
        )
        if account_id
        else None
    )

    credential = next(
        (c for c in account.credentials if c.id == dec_refresh_token.credential_id),
        None,
    )

    if not credential:
        logger.debug(f"Refresh token ID {dec_refresh_token.credential_id} not found")
        return None

    from_db = converter.structure(credential.data, RefreshToken)
    if from_db.token_num != dec_refresh_token.token_num:
        logger.warning(
            "Received an old version of refresh token ID " f"{from_db.credential_id}"
        )
        account.revoke_refresh_tokens()
        return None

    return from_db
