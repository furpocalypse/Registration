from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from oes.registration.serialization.json import json_dumps


@pytest.mark.parametrize(
    "input_, expected",
    [
        ({"1", "2"}, b'["1","2"]'),
        (frozenset({2, 1}), b"[1,2]"),
        (
            UUID("534e683b-499e-4fd4-838a-f706083d4a7c"),
            b'"534e683b-499e-4fd4-838a-f706083d4a7c"',
        ),
        (
            datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            b'"2020-01-01T12:00:00+00:00"',
        ),
        (date(2024, 7, 4), b'"2024-07-04"'),
        (Path("/a/b/c"), b'"/a/b/c"'),
    ],
)
def test_json_defaults(input_, expected):
    result = json_dumps(input_)
    assert result == expected
