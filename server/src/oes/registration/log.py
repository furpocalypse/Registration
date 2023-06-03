"""Logging module."""
import copy
import logging
import sys
from enum import Enum

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


class AuditLogType(str, Enum):
    audit = "audit"
    registration_create = "registration.create"
    registration_create_pending = "registration.create_pending"
    registration_update = "registration.update"
    registration_cancel = "registration.cancel"
    checkout_create = "checkout.create"
    checkout_complete = "checkout.complete"


def setup_logging(debug: bool = False):
    """Set up the logger."""

    # TODO: configuration

    level = logging.DEBUG if debug else logging.INFO

    logger.remove()
    logger.add(sys.stderr, level=level)

    audit_log.remove()
    audit_log.add(
        sys.stderr,
        level=level,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


audit_log = copy.deepcopy(logger, memo={id(sys.stderr): sys.stderr}).bind(name="audit")
"""Separate logger for audit events."""

audit_log.remove()

audit_log.configure(
    extra=dict(
        type=AuditLogType.audit,
        registration=None,
        checkout=None,
    )
)
