"""Account service module."""
from typing import Optional
from uuid import UUID

from oes.registration.auth.entities import AccountEntity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class AccountService:
    db: AsyncSession

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account(
        self, id: UUID, *, lock: bool = False, with_credentials: bool = False
    ) -> Optional[AccountEntity]:
        """Get an account by ID."""

        options = []

        if with_credentials:
            options.append(selectinload(AccountEntity.credentials))

        return await self.db.get(
            AccountEntity,
            id,
            options=options,
            with_for_update=lock,
        )

    async def create_account(self, email: Optional[str]) -> AccountEntity:
        """Create a new account."""
        entity = AccountEntity(
            email=email,
            credentials=[],
            registrations=[],
        )
        self.db.add(entity)
        await self.db.flush()
        return entity
