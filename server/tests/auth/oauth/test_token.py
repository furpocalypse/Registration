from datetime import timedelta
from uuid import UUID

import jwt
import pytest
from oes.registration.auth.scope import Scopes
from oes.registration.auth.token import (
    DEFAULT_REFRESH_TOKEN_LIFETIME,
    AccessToken,
    RefreshToken,
    TokenBase,
    converter,
)
from oes.registration.util import get_now


def test_token_encode_decode():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = TokenBase(
        sub="test",
        exp=later,
    )

    token_str = token.encode(key="test")
    decoded = TokenBase.decode(token_str, key="test")
    assert decoded == token


def test_token_encode_decode_key():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = TokenBase(
        sub="test",
        exp=later,
    )

    token_str = token.encode(key="test")
    with pytest.raises(jwt.InvalidTokenError):
        TokenBase.decode(token_str, key="test-bad")


def test_token_expired():
    now = get_now(seconds_only=True)
    exp = now - timedelta(seconds=1)
    token = TokenBase(
        sub="test",
        exp=exp,
    )

    token_str = token.encode(key="test")
    with pytest.raises(jwt.InvalidTokenError):
        TokenBase.decode(token_str, key="test")


def test_access_token_unstructure():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = AccessToken.create(
        account_id=UUID("40e189ea-acca-42f7-b4e9-6f248e6e6b58"),
        scope=Scopes("c b a"),
        expiration_date=later,
    )
    res = converter.unstructure(token)
    assert res == {
        "typ": "at",
        "sub": "40e189eaacca42f7b4e96f248e6e6b58",
        "exp": int(later.timestamp()),
        "scope": "a b c",
    }


def test_refresh_token_unstructure():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = RefreshToken.create(
        account_id=UUID("40e189ea-acca-42f7-b4e9-6f248e6e6b58"),
        credential_id="c1",
        token_num=1,
        scope=Scopes("c b a"),
        expiration_date=later,
    )
    res = converter.unstructure(token)
    assert res == {
        "typ": "rt",
        "jti": "c1:1",
        "sub": "40e189eaacca42f7b4e96f248e6e6b58",
        "exp": int(later.timestamp()),
        "scope": "a b c",
    }


def test_refresh_token_create_access_token():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = RefreshToken.create(
        account_id="1234",
        credential_id="c1",
        token_num=1,
        scope=Scopes("c b a"),
        expiration_date=later,
        email="test@test.com",
    )

    access_token = token.create_access_token(
        scope=Scopes("b e"),
        expiration_date=later,
    )

    res = converter.unstructure(access_token)
    assert res == {
        "typ": "at",
        "exp": int(later.timestamp()),
        "sub": "1234",
        "email": "test@test.com",
        "scope": "b",
    }


def test_refresh_token_credential_id():
    token = RefreshToken.create(
        account_id="1234",
        credential_id="c5",
        token_num=4,
    )
    assert token.credential_id == "c5"
    assert token.token_num == 4


def test_refresh_token_reissue():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = RefreshToken.create(
        account_id="1234",
        credential_id="c1",
        token_num=1,
        scope=Scopes("c b a"),
        expiration_date=later,
        email="test@test.com",
    )
    reissued = token.reissue_refresh_token()
    res = converter.unstructure(reissued)
    assert res == {
        "typ": "rt",
        "sub": "1234",
        "jti": "c1:2",
        "scope": "a b c",
        "email": "test@test.com",
        "exp": res["exp"],
    }
    assert (res["exp"] - now.timestamp()) >= DEFAULT_REFRESH_TOKEN_LIFETIME.seconds


def test_check_token_type():
    now = get_now(seconds_only=True)
    later = now + timedelta(seconds=10)
    token = AccessToken.create(
        account_id="test",
        scope=Scopes("c b a"),
        expiration_date=later,
    )
    enc = token.encode(key="test")
    with pytest.raises(jwt.InvalidTokenError):
        RefreshToken.decode(enc, key="test")
