from datetime import datetime, timedelta
from unittest.mock import patch

from oes.registration.hook.entities import HookLogEntity
from oes.registration.hook.models import NUM_RETRIES, RETRY_SECONDS


@patch("oes.registration.hook.entities.get_now")
def test_hook_update_attempts(get_now_mock):
    now = datetime(2020, 1, 1)
    hook = HookLogEntity(attempts=0)

    get_now_mock.return_value = now

    expected_1 = now + timedelta(seconds=RETRY_SECONDS[0])
    res1 = hook.update_attempts()
    assert res1 == expected_1
    assert hook.retry_at == expected_1
    assert hook.attempts == 1

    expected_2 = now + timedelta(seconds=RETRY_SECONDS[1])
    res2 = hook.update_attempts()
    assert res2 == expected_2
    assert hook.retry_at == expected_2
    assert hook.attempts == 2

    hook.attempts = NUM_RETRIES
    res2 = hook.update_attempts()
    assert res2 is None
    assert hook.retry_at is None
