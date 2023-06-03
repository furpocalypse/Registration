import copy

import pytest
from oes.registration.util import merge_dict


@pytest.mark.parametrize(
    "a, b, result",
    [
        # trivial cases
        ({}, {}, {}),
        ({}, {"x": 1}, {"x": 1}),
        ({"x": 1}, {}, {"x": 1}),
        # merging/overwriting
        ({"x": 1}, {"y": 2}, {"x": 1, "y": 2}),
        ({"x": 1, "y": 2}, {"x": 2}, {"x": 2, "y": 2}),
        # nested merging
        (
            {"x": {"x1": 1, "x2": 2}, "y": 5},
            {"x": {"x2": 3, "x3": 4}},
            {"x": {"x1": 1, "x2": 3, "x3": 4}, "y": 5},
        ),
        # replacing dicts instead of merging
        (
            {"x": {"x1": 1}},
            {"x": 1},
            {"x": 1},
        ),
        (
            {"x": 1},
            {"x": {"x1": 1}},
            {"x": {"x1": 1}},
        ),
    ],
)
def test_merge_dict(a, b, result):
    a = copy.deepcopy(a)
    b = copy.deepcopy(b)
    merge_dict(a, b)
    assert a == result
