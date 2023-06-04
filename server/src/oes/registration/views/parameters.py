"""Parameter binding utilities."""
from typing import Any, Optional, TypeVar

from blacksheep import Request
from blacksheep.server.bindings import BodyBinder, BoundValue, QueryBinder
from cattrs import BaseValidationError
from loguru import logger
from oes.registration.serialization import get_converter
from oes.registration.serialization.json import json_loads
from oes.registration.views.responses import BodyValidationError

T = TypeVar("T")


class AttrsBody(BoundValue[T]):
    """Parse an attrs class from the request body."""

    pass


class AttrsBinder(BodyBinder):
    """Binder for :class:`AttrsBody`."""

    handle = AttrsBody

    @property
    def content_type(self) -> str:
        return "application/json"

    def matches_content_type(self, request: Request) -> bool:
        return request.declares_json()

    async def read_data(self, request: Request) -> Any:
        return await request.json(loads=json_loads)

    def parse_value(self, data: dict) -> Any:
        try:
            return get_converter().structure(data, self.expected_type)
        except BaseValidationError as e:
            logger.opt(exception=e).debug("Invalid request")
            raise BodyValidationError(e)


class Page(BoundValue[int]):
    """Page bound value."""

    pass


class PerPage(BoundValue[int]):
    """Per-page bound value."""

    pass


class PageBinder(QueryBinder):
    """Binds the ``page`` parameter."""

    handle = Page
    name_alias = "page"

    def __init__(self, expected_type=int, param_name="page", implicit=True):
        super().__init__(expected_type, param_name, implicit)

    async def get_value(self, request: Request) -> Optional[Any]:
        value = await super().get_value(request)
        if value is None or value < 0:
            return 0
        else:
            return value


class PerPageBinder(QueryBinder):
    """Binds the ``per_page`` parameter."""

    handle = PerPage
    name_alias = "per_page"
    max = 50

    def __init__(self, expected_type=int, param_name="per_page", implicit=True):
        super().__init__(expected_type, param_name, implicit)

    async def get_value(self, request: Request) -> Optional[Any]:
        value = await super().get_value(request)
        if value is not None:
            if value < 1:
                return 1
            elif value > self.max:
                return self.max
            else:
                return value
        else:
            return self.max
