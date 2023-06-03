from collections.abc import Sequence

import pytest
from cattrs import Converter
from oes.registration.models.config import Base64Bytes
from oes.template import Condition, Expression, LogicAnd, Template


@pytest.fixture
def converter():
    from oes.registration.serialization.config import converter

    return converter


@pytest.mark.parametrize(
    "input_, type_, expected",
    [
        (
            "{{test}}",
            Template,
            Template("{{test}}"),
        ),
        (
            "1 + a",
            Expression,
            Expression("1 + a"),
        ),
        (
            ["1 + 1 == 2", {"and": [True, "false"]}],
            Condition,
            (Expression("1 + 1 == 2"), LogicAnd((True, Expression("false")))),
        ),
        (
            ["a", "b", "c"],
            Sequence[str],
            ("a", "b", "c"),
        ),
        ("dGVzdA==", Base64Bytes, Base64Bytes(b"test")),
        (b"test", Base64Bytes, Base64Bytes(b"test")),
    ],
)
def test_structure(converter: Converter, input_, type_, expected):
    result = converter.structure(input_, type_)
    assert result == expected


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            Expression("test"),
            "test",
        ),
        (
            Template("test"),
            "test",
        ),
        (
            LogicAnd((True, Expression("false"))),
            {
                "and": [
                    True,
                    "false",
                ]
            },
        ),
    ],
)
def test_unstructure(converter: Converter, input_, expected):
    result = converter.unstructure(input_)
    assert result == expected


@pytest.mark.parametrize(
    "input_, type_, expected",
    [
        ("dGVzdA==", Base64Bytes, "dGVzdA=="),
        (Base64Bytes(b"test"), Base64Bytes, "dGVzdA=="),
    ],
)
def test_unstructure_specific_types(converter: Converter, input_, type_, expected):
    result = converter.unstructure(input_, unstructure_as=Base64Bytes)
    assert result == expected
