from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from cattrs import Converter


@pytest.fixture
def converter():
    from oes.registration.serialization.common import converter

    return converter


@pytest.mark.parametrize(
    "input_, type_, expected",
    [
        (
            "534e683b-499e-4fd4-838a-f706083d4a7c",
            UUID,
            UUID("534e683b-499e-4fd4-838a-f706083d4a7c"),
        ),
        (
            UUID("534e683b-499e-4fd4-838a-f706083d4a7c"),
            UUID,
            UUID("534e683b-499e-4fd4-838a-f706083d4a7c"),
        ),
        (
            "2020-01-01T12:00:00+00:00",
            datetime,
            datetime(2020, 1, 1, 12, tzinfo=timezone.utc),
        ),
        (
            datetime(2020, 1, 1, 12, tzinfo=timezone.utc),
            datetime,
            datetime(2020, 1, 1, 12, tzinfo=timezone.utc),
        ),
        (
            1720114200,
            datetime,
            datetime(2024, 7, 4, 17, 30, tzinfo=timezone.utc),
        ),
        (
            "2020-01-01T12:00:00",
            datetime,
            datetime(2020, 1, 1, 12).astimezone(),
        ),
        (
            "2020-08-08",
            date,
            date(2020, 8, 8),
        ),
        (
            date(2020, 8, 8),
            date,
            date(2020, 8, 8),
        ),
        (
            "/a/b/c",
            Path,
            Path("/a/b/c"),
        ),
        (
            Path("/a/b/c"),
            Path,
            Path("/a/b/c"),
        ),
    ],
)
def test_structure(converter: Converter, input_, type_, expected):
    result = converter.structure(input_, type_)
    assert result == expected
