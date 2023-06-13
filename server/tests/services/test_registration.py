import uuid
from datetime import datetime
from unittest.mock import create_autospec
from uuid import UUID

import pytest
import pytest_asyncio
from oes.registration.entities.registration import RegistrationEntity
from oes.registration.hook.service import HookSender
from oes.registration.models.config import Config
from oes.registration.models.registration import RegistrationState
from oes.registration.services.registration import RegistrationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def service(db: AsyncSession):
    return RegistrationService(db, create_autospec(HookSender), create_autospec(Config))


@pytest_asyncio.fixture
async def registration_id(service: RegistrationService, db: AsyncSession):
    id_ = uuid.uuid4()
    reg = RegistrationEntity(
        id=id_,
        state=RegistrationState.created,
        event_id="example",
        extra_data={
            "extra": 123,
        },
    )
    await service.create_registration(reg)
    await db.commit()
    return id_


@pytest.mark.asyncio
async def test_get_registration(service: RegistrationService, registration_id: UUID):
    reg = await service.get_registration(registration_id)
    assert reg.id == registration_id
    assert reg.version == 1
    assert reg.state == RegistrationState.created
    assert isinstance(reg.date_created, datetime)


@pytest.mark.asyncio
async def test_list_registrations(service: RegistrationService, registration_id: UUID):
    res = await service.list_registrations()
    assert len(res) == 1
    assert res[0].id == registration_id


@pytest.mark.asyncio
async def test_list_registrations_pagination(
    service: RegistrationService, registration_id: UUID
):
    # TODO: improve
    res = await service.list_registrations(page=1)
    assert len(res) == 0


@pytest.mark.asyncio
async def test_update_registration(
    service: RegistrationService, registration_id: UUID, db: AsyncSession
):
    reg = await service.get_registration(registration_id)
    model = reg.get_model()
    model.email = "updated@test.com"
    model.option_ids = {"option1", "option2"}
    model.extra_data = {"extra2": 123}
    reg.update_properties_from_model(model)
    await db.commit()

    reg = await service.get_registration(registration_id)
    assert reg.id == registration_id
    assert reg.email == "updated@test.com"
    assert sorted(reg.option_ids) == ["option1", "option2"]
    assert reg.extra_data == {"extra": 123, "extra2": 123}
    assert reg.version == 2
    assert isinstance(reg.date_updated, datetime)


@pytest.mark.asyncio
async def test_update_registration_only_increment_version_once(
    service: RegistrationService, registration_id: UUID
):
    reg = await service.get_registration(registration_id)
    model = reg.get_model()
    model.email = "updated@test.com"
    model.option_ids = {"option1", "option2"}
    model.extra_data = {"extra2": 123}
    reg.update_properties_from_model(model)
    assert reg.version == 2

    model.email = "updated2@test.com"
    reg.update_properties_from_model(model)
    assert reg.email == "updated2@test.com"
    assert reg.version == 2
