"""Base payment classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any, Optional

import orjson
from attrs import frozen
from oes.registration.models.cart import CartData
from oes.registration.models.payment import PaymentServiceCheckout
from oes.registration.models.pricing import PricingResult


class PaymentServiceError(RuntimeError):
    """Raised when an operation with a payment service does not succeed."""

    pass


class CheckoutStateError(PaymentServiceError):
    """Raised when there is an issue with the state of a checkout."""


class CheckoutCancelError(CheckoutStateError):
    """Raised when a checkout could not be canceled."""

    pass


class ValidationError(ValueError, PaymentServiceError):
    """Raised when data does not validate."""

    pass


@frozen
class CheckoutMethod:
    """A checkout method."""

    service: str
    """The service ID."""

    method: Optional[str] = None
    """The method ID."""

    name: Optional[str] = None
    """The method name."""


@frozen
class WebhookRequestInfo:
    """A webhook request."""

    body: bytes
    """The body bytes."""

    url: bytes
    """The request URL."""

    headers: Mapping[bytes, bytes]
    """The request headers."""


@frozen
class WebhookResult:
    """A webhook result."""

    updated_checkout: Optional[PaymentServiceCheckout] = None
    """The updated checkout."""

    body: Optional[bytes] = None
    """The body bytes."""

    content_type: bytes = b"application/json"
    """The response content type."""

    status: int = 200
    """The response status."""


@frozen(kw_only=True)
class CheckoutMethodsRequest:
    """Request to get checkout options."""

    service: str
    """The service ID."""

    cart_data: CartData
    """The cart data."""

    pricing_result: PricingResult
    """The pricing result."""


@frozen(kw_only=True)
class CreateCheckoutRequest:
    """Request to create a checkout."""

    service: str
    """The service ID."""

    method: Optional[str] = None
    """The payment method ID."""

    cart_data: CartData
    """The cart data."""

    pricing_result: PricingResult
    """The pricing result."""

    # TODO: email, other user info


@frozen(kw_only=True)
class UpdateRequest:
    """An update request object."""

    service: str
    """The service ID."""

    id: str
    """The ID of the checkout in the service."""

    checkout_data: dict[str, Any] = {}
    """The external checkout data for the existing checkout."""

    body: dict[str, Any] = {}
    """The data submitted by the client."""


WebhookParser = Callable[[WebhookRequestInfo], object]
"""Callable to parse a webhook request and return the parsed body.

Must raise :class:`ValidationError` if the parsing fails.
"""

WebhookValidator = Callable[[WebhookRequestInfo, object], object]
"""Callable to validate a webhook request and return the validated body.

Must raise :class:`ValidationError` if the validation fails.
"""

UpdateHandler = Callable[[UpdateRequest], Awaitable[PaymentServiceCheckout]]
"""Callable to update a payment request.

Returns an updated checkout.
"""


class PaymentService(ABC):
    """Payment service base class."""

    @property
    @abstractmethod
    def id(self) -> str:
        """The payment service ID."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """The human-readable service name."""
        ...

    # TODO: these should be implemented via Protocol instead of like this...

    @property
    def webhook_parser(self) -> Optional[WebhookParser]:
        """The :class:`WebhookParser`, if supported."""
        return None

    @property
    def webhook_validator(self) -> Optional[WebhookValidator]:
        """The :class:`WebhookValidator`, if supported."""
        return None

    @property
    def update_handler(self) -> Optional[UpdateHandler]:
        """The :class:`UpdateHandler`, if supported."""
        return None

    @abstractmethod
    async def get_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> Optional[PaymentServiceCheckout]:
        """Get the current :class:`PaymentServiceCheckout` data.

        Args:
            id: The checkout ID in the payment service.
            extra_data: Additional data about the checkout.

        Returns:
            The current :class:`PaymentServiceCheckout`, or None if not found.
        """
        ...

    @abstractmethod
    async def get_checkout_methods(
        self, request: CheckoutMethodsRequest
    ) -> Iterable[CheckoutMethod]:
        """Get the available checkout methods.

        Args:
            request:

        Returns:
            An iterable of available :class:`CheckoutMethod`.
        """
        ...

    @abstractmethod
    async def create_checkout(
        self, request: CreateCheckoutRequest
    ) -> PaymentServiceCheckout:
        """Create a checkout with the payment service.

        Args:
            request: A :class:`CreateCheckoutRequest` instance.

        Returns:
            A :class:`PaymentServiceCheckout`.
        """
        ...

    @abstractmethod
    async def cancel_checkout(
        self, id: str, extra_data: Optional[dict[str, Any]] = None
    ) -> PaymentServiceCheckout:
        """Cancel a checkout.

        Args:
            id: The checkout ID.
            extra_data: Additional data about the checkout.

        Returns:
            An updated :class:`PaymentServiceCheckout` instance.

        Raises:
            CheckoutCancelError: if the checkout could not be canceled.
        """
        ...


# Defaults
def json_parser(request: WebhookRequestInfo) -> dict[str, Any]:
    """JSON webhook parser."""
    if request.headers.get(b"Content-Type") != b"application/json":
        raise ValidationError("Invalid content-type")

    try:
        obj = orjson.loads(request.body)
        if not isinstance(obj, dict):
            raise ValidationError("Not a valid JSON object")
        return obj
    except Exception:
        raise ValidationError("Could not parse body")


def json_result(checkout: Optional[PaymentServiceCheckout], body: Any) -> WebhookResult:
    """JSON webhook result."""
    return WebhookResult(
        updated_checkout=checkout,
        body=orjson.dumps(body),
        content_type=b"application/json",
        status=200,
    )
