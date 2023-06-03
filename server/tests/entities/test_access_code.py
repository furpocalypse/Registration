from datetime import datetime

import pytest
from oes.registration.entities.access_code import AccessCodeEntity, generate_code


def test_generate_code():
    # not super robust
    code1 = generate_code()
    code2 = generate_code()
    assert len(code1) == 12
    assert code1 != code2


@pytest.mark.parametrize(
    "now, exp, used, res",
    [
        (datetime(2020, 1, 1, 12), datetime(2020, 1, 1, 13), False, True),
        (datetime(2020, 1, 1, 12), datetime(2020, 1, 1, 12), False, False),
        (datetime(2020, 1, 1, 12), datetime(2020, 1, 1, 13), True, False),
        (datetime(2020, 1, 1, 12), datetime(2020, 1, 1, 12), True, False),
    ],
)
def test_check_valid(now, exp, used, res):
    code = AccessCodeEntity(
        date_expires=exp,
        used=used,
    )
    assert code.check_valid(now=now) == res
