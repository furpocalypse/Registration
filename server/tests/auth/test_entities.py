from datetime import datetime, timedelta
from unittest.mock import patch

from oes.registration.auth.entities import (
    AUTH_CODE_EXPIRATION_SEC,
    AUTH_CODE_LEN,
    AUTH_CODE_MAX_ATTEMPTS,
    AUTH_CODE_MAX_NUM_SENT,
    EmailAuthCodeEntity,
)
from oes.registration.util import get_now


def test_generate_code():
    code = EmailAuthCodeEntity.generate_code()
    assert isinstance(code, str)
    assert len(code) == AUTH_CODE_LEN

    code2 = EmailAuthCodeEntity.generate_code()
    assert code != code2


def test_is_auth_code_expired():
    now = get_now()
    later = now + timedelta(seconds=5)
    auth = EmailAuthCodeEntity(
        date_expires=later,
    )
    assert not auth.get_is_expired(now=now)

    auth.date_expires = now
    assert auth.get_is_expired(now=later)


def test_auth_code_get_is_usable():
    now = get_now()
    later = now + timedelta(seconds=5)
    auth = EmailAuthCodeEntity(
        date_expires=later,
        num_sent=0,
        attempts=0,
    )
    assert auth.get_is_usable(now=now)
    assert not auth.get_is_usable(now=later)

    auth.attempts = AUTH_CODE_MAX_ATTEMPTS
    assert not auth.get_is_usable(now=now)


def test_auth_code_can_send():
    auth = EmailAuthCodeEntity(
        num_sent=0,
        attempts=0,
    )
    assert auth.can_send
    auth.num_sent = AUTH_CODE_MAX_NUM_SENT
    assert not auth.can_send
    auth.num_sent = 0
    auth.attempts = AUTH_CODE_MAX_ATTEMPTS
    assert not auth.can_send


def test_auth_code_set_code():
    now = datetime(2020, 1, 1, 12)
    auth = EmailAuthCodeEntity(
        num_sent=0,
        attempts=0,
    )
    c1 = auth.set_code(now=now)
    assert isinstance(auth.code, str)
    assert len(auth.code) == AUTH_CODE_LEN
    assert auth.date_created == now
    assert auth.date_expires == now + timedelta(seconds=AUTH_CODE_EXPIRATION_SEC)
    assert auth.num_sent == 1
    assert c1 == auth.code

    c2 = auth.set_code(now=now)
    assert c2 == auth.code
    assert c2 != c1
    assert auth.num_sent == 2

    auth.num_sent = AUTH_CODE_MAX_ATTEMPTS
    assert auth.set_code() is None
