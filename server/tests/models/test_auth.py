from datetime import datetime, timedelta, timezone

import pytest
from jwt import InvalidTokenError
from oes.registration.models.auth import (
    AUDIENCE,
    ISSUER,
    AccessToken,
    Scope,
    Scopes,
    converter,
)
from oes.registration.util import get_now


def test_token_encode_decode():
    now = get_now(seconds_only=True)
    exp = now + timedelta(seconds=30)
    token = AccessToken(
        iss=ISSUER,
        aud=AUDIENCE,
        sub="test",
        iat=now,
        exp=exp,
    )

    encoded = token.encode(key="test-key")
    assert isinstance(encoded, str)

    decoded = token.decode(encoded, key="test-key")
    assert decoded == token


def test_token_different_key_error():
    now = get_now(seconds_only=True)
    exp = now + timedelta(seconds=30)
    token = AccessToken(
        iss=ISSUER,
        aud=AUDIENCE,
        sub="test",
        iat=now,
        exp=exp,
    )
    encoded = token.encode(key="test-key")
    with pytest.raises(InvalidTokenError):
        token.decode(encoded, key="wrong-key")


@pytest.mark.parametrize(
    "props",
    [
        {"iss": "wrong"},
        {"aud": "wrong"},
        {"exp": datetime.fromtimestamp(0, tz=timezone.utc)},
        {"exp": None},
    ],
)
def test_token_validation_errors(props):
    now = get_now(seconds_only=True)
    exp = now + timedelta(seconds=30)
    with pytest.raises(InvalidTokenError):
        token = AccessToken(
            **{
                "sub": "test",
                "iat": now,
                "exp": exp,
                "iss": ISSUER,
                "aud": AUDIENCE,
                **props,
            }
        )
        encoded = token.encode(key="test-key")
        token.decode(encoded, key="test-key")


def test_has_scope():
    exp = get_now(seconds_only=True) + timedelta(seconds=30)
    token1 = AccessToken(exp=exp, scope=Scopes(frozenset({Scope.self_service})))

    assert token1.has_scope(Scope.self_service)
    assert not token1.has_scope(Scope.admin)

    token2 = AccessToken(
        exp=exp,
        scope=Scopes(
            frozenset(
                {
                    Scope.self_service,
                    Scope.admin,
                }
            )
        ),
    )
    assert token2.has_scope(Scope.admin, Scope.self_service)
    assert not token2.has_scope(Scope.admin, Scope.self_service, "other")


def test_parsing():
    now = get_now(seconds_only=True)
    exp = now + timedelta(seconds=30)

    token_data = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(exp.timestamp()),
        "scope": Scope.self_service + " " + Scope.admin,
    }

    loaded = converter.structure(token_data, AccessToken)
    assert loaded == AccessToken(
        iss=ISSUER,
        aud=AUDIENCE,
        exp=exp,
        scope=Scopes(frozenset({Scope.self_service, Scope.admin})),
    )

    as_dict = converter.unstructure(loaded)

    # hacky workaround for set non-ordering
    assert (
        as_dict["scope"] == Scope.self_service + " " + Scope.admin
        or as_dict["scope"] == Scope.admin + " " + Scope.self_service
    )

    as_dict["scope"] = Scope.self_service + " " + Scope.admin

    assert as_dict == token_data
