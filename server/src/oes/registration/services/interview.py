"""Interview service module."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from attrs import frozen
from oes.interview.state import InterviewState, InvalidStateError
from oes.interview.state import get_validated_state as _get_validated_state
from oes.registration.models.config import Config, InterviewConfig
from oes.registration.serialization.json import json_default


@frozen
class InterviewResult:
    """Data from a completed interview."""

    submission_id: str
    interview_id: str
    interview_version: str
    target_url: str
    data: dict[str, Any]


class InterviewService:
    """Interview service."""

    interview_config: InterviewConfig

    def __init__(self, config: Config):
        self.interview_config = config.interview

    def create_state(
        self,
        interview_id: str,
        *,
        target_url: str,
        submission_id: Optional[UUID] = None,
        context: Optional[dict[str, Any]] = None,
        initial_data: Optional[dict[str, Any]] = None,
        expiration_date: Optional[datetime] = None,
    ) -> str:
        """Create a :class:`InterviewState`."""
        state = InterviewState.create(
            interview_id=interview_id,
            interview_version="1",  # TODO,
            target_url=target_url,
            submission_id=str(submission_id) if submission_id is not None else None,
            expiration_date=expiration_date,
            context=context,
            data=initial_data,
        )
        return state.encrypt(
            key=self.interview_config.encryption_key,
            default=json_default,
        )

    def get_validated_state(
        self,
        state_str: str,
        *,
        current_url: Optional[str] = None,
    ) -> InterviewResult:
        """Get a validated, completed interview.

        If ``current_url`` is provided, checks that the ``target_url`` matches.

        Args:
            state_str: The encrypted state string.
            current_url: The current URL.

        Returns:
            A :class:`InterviewResult`.

        Raises:
            InvalidStateError: If the state is invalid, expired, or incomplete.
        """
        state = _get_validated_state(
            state_str, key=self.interview_config.encryption_key
        )

        if not state.complete:
            raise InvalidStateError("Interview state is not complete")

        if current_url is not None and state.target_url != current_url:
            raise InvalidStateError("Invalid target URL")

        return InterviewResult(
            submission_id=state.submission_id,
            interview_id=state.interview_id,
            interview_version=state.interview_version,
            target_url=state.target_url,
            data=state.data,
        )
