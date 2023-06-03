"""Docs helpers."""
import asyncio
import functools
from collections.abc import Callable, Sequence
from typing import Any, Optional, Type, TypeVar, Union, cast, get_args, get_origin

from attrs import Attribute, fields
from blacksheep.server.openapi.common import ContentInfo, ResponseInfo
from blacksheep.server.openapi.v3 import FieldInfo, ObjectTypeHandler, OpenAPIHandler
from oes.registration.models.auth import Scope
from oes.registration.serialization import get_converter
from openapidocs.v3 import (
    HTTPSecurity,
    Info,
    OAuth2Security,
    OAuthFlow,
    OAuthFlows,
    OpenAPI,
    Reference,
    Schema,
    Security,
    SecurityRequirement,
)

T = TypeVar("T")


class Handler(OpenAPIHandler):
    def on_docs_generated(self, docs: OpenAPI):
        docs.security = Security(
            requirements=[
                SecurityRequirement("accessToken", []),
                SecurityRequirement("guest", []),
            ]
        )


docs = Handler(
    info=Info(
        title="OES Registration API",
        version="0.1",
    ),
)
"""Docs object."""

docs.components.security_schemes = {
    "accessToken": HTTPSecurity(scheme="bearer"),
    # Only shown here for convenient usage of the guest auth in Swagger
    "guest": OAuth2Security(
        flows=OAuthFlows(
            client_credentials=OAuthFlow(
                scopes={
                    Scope.self_service.value: "Allows access to self-service endpoints",
                },
                refresh_url="/auth/token",
                token_url="/auth/new-account",
            )
        )
    ),
}


class AttrsTypeHandler(ObjectTypeHandler):
    """Schema generator for attrs classes."""

    _no_register_types = (
        int,
        float,
        str,
        bool,
        Any,
    )

    def __init__(self, docs: OpenAPIHandler):
        self.docs = docs

    def handles_type(self, object_type) -> bool:
        return hasattr(object_type, "__attrs_attrs__")

    def get_schema(self, type_) -> Union[Schema, Reference]:
        if type_ in self._no_register_types:
            return self.docs.get_schema_by_type(type_)
        else:
            return self.docs.register_schema_for_type(type_)

    def is_optional(self, type_) -> bool:
        if get_origin(type_) is Union:
            args = get_args(type_)
            return len(args) == 2 and type(None) in args
        else:
            return False

    def get_union_schema(self, type_) -> Schema:
        args = get_args(type_)
        optional = type(None) in args

        return Schema(
            one_of=[
                self.get_schema(arg) for arg in args if arg is type(None)  # noqa: E721
            ],
            nullable=optional,
        )

    def get_field_info(self, field: Attribute) -> FieldInfo:
        if field.type is Any:
            type_ = Any
        elif self.is_optional(field.type):
            type_ = field.type
        elif get_origin(field.type) is Union:
            type_ = self.get_union_schema(field.type)
        else:
            type_ = field.type

        return FieldInfo(field.name, type_)

    def get_type_fields(self, object_type) -> list[FieldInfo]:
        return [self.get_field_info(field) for field in fields(object_type)]


docs.object_types_handlers.append(AttrsTypeHandler(docs))


def _get_serializer(type_: object) -> Callable[[object], Any]:
    if isinstance(type_, type) or get_origin(type_) is not None:
        return lambda v: get_converter().unstructure(v, unstructure_as=type_)
    elif callable(type_):
        return type_
    else:
        return lambda v: v


def serialize(type_: T):
    """Serialize the return value using the given type."""
    serializer = _get_serializer(type_)

    def decorator(fn):
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                response = await fn(*args, **kwargs)
                return serializer(response)

        else:

            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                response = fn(*args, **kwargs)
                return serializer(response)

        return wrapper

    return decorator


def docs_helper(
    *,
    response_type: Optional[object] = None,
    response_summary: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    auth: bool = True,
):
    """Decorate view handlers with documentation."""
    responses = {}

    def serialize_decorator(v):
        return v

    if response_type is not None:
        responses[200] = ResponseInfo(
            description=response_summary or "The result",
            content=[
                ContentInfo(
                    type=cast(Type, response_type),
                )
            ],
        )

        serialize_decorator = serialize(response_type)  # noqa

    docs_decorator = docs(
        responses=responses,
        tags=tags,
    )

    def decorator(fn):
        fn = serialize_decorator(fn)
        fn = docs_decorator(fn)
        return fn

    return decorator
