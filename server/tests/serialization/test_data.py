from collections.abc import Sequence
from typing import Optional

import pytest
from attrs import frozen
from cattrs import BaseValidationError, Converter
from oes.registration.views.responses import ExceptionDetails


@pytest.fixture
def converter():
    from oes.registration.serialization.data import converter

    return converter


# specific cases like Registration are tested elsewhere


@pytest.mark.parametrize(
    "input_, type_, expected",
    [
        (1, int, 1),
        (1.5, float, 1.5),
        (True, bool, True),
        (1.4, int, 1),
        (1, float, 1.0),
        (1, Optional[int], 1),
        (1, Optional[float], 1.0),
        (1.5, Optional[int], 1),
        (
            ["a", "b", "c"],
            Sequence[str],
            ("a", "b", "c"),
        ),
        ([1.5, None, -1], Sequence[Optional[int]], (1, None, -1)),
    ],
)
def test_structure(converter: Converter, input_, type_, expected):
    result = converter.structure(input_, type_)
    assert result == expected


@pytest.mark.parametrize(
    "input_, type_",
    [
        ("1", int),
        ("true", bool),
        (1, bool),
        (123, str),
        ("123", Optional[int]),
        ([1.5, None, "1"], Sequence[Optional[int]]),
    ],
)
def test_structure_no_cast(converter: Converter, input_, type_):
    with pytest.raises((TypeError, BaseValidationError)):
        converter.structure(input_, type_)


@pytest.mark.parametrize(
    "input_, expected",
    [
        (
            ExceptionDetails(
                detail="Validation error",
                children=[ExceptionDetails(exception="ValueError")],
            ),
            {"detail": "Validation error", "children": [{"exception": "ValueError"}]},
        )
    ],
)
def test_unstructure(converter: Converter, input_, expected):
    result = converter.unstructure(input_)
    assert result == expected


@frozen
class Model1:
    a: int
    b: int = 2


@frozen
class Model2:
    a: Optional[int] = 1
    b: Optional[int] = None


@pytest.mark.parametrize(
    "input_, expected",
    [
        (Model1(1), {"a": 1, "b": 2}),
        (Model1(1, 3), {"a": 1, "b": 3}),
        (
            Model2(1, 2),
            {"a": 1, "b": 2},
        ),
        (
            Model2(1),
            {"a": 1},
        ),
        (
            Model2(),
            {"a": 1},
        ),
        (
            Model2(a=None, b=2),
            {"b": 2},
        ),
        (
            Model2(a=None),
            {},
        ),
    ],
)
def test_unstructure_omit_none(converter: Converter, input_, expected):
    result = converter.unstructure(input_)
    assert result == expected
