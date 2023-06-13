"""Pricing models."""
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Optional
from uuid import UUID

from attrs import field, frozen
from oes.registration.models.cart import CartData
from oes.registration.models.event import SimpleEventInfo


class PricingError(ValueError):
    """Raised when there is a problem with a pricing result."""

    pass


@frozen(kw_only=True)
class Modifier:
    """A line item modifier."""

    type_id: Optional[str] = None
    """A type ID for the modifier."""

    name: str
    """The modifier name."""

    amount: int
    """The amount."""


def _validate_price(a, i, v):
    if v < 0:
        raise PricingError("Price cannot be negative")


@frozen(kw_only=True)
class LineItem:
    """A line item."""

    type_id: Optional[str] = None
    """A type ID for the line item."""

    registration_id: UUID
    """The registration ID the line item is associated with."""

    name: str
    """The name of the line item."""

    price: int = field(validator=_validate_price)
    """The line item base price."""

    total_price: int
    """The total price of the line item."""

    modifiers: Sequence[Modifier] = ()
    """Line item modifiers."""

    description: Optional[str] = None
    """A line item description."""

    meta: Optional[dict[str, Any]] = None
    """Line item metadata."""

    def _validate_total(self):
        """Validate that the ``total_price`` sums up correctly."""
        total = self.price
        for modifier in self.modifiers:
            total += modifier.amount

        # discounts cannot make the total negative
        if total < 0:
            total = 0

        if total != self.total_price:
            raise PricingError("Line item total price does not sum")

    def __attrs_post_init__(self):
        self._validate_total()


def _validate_line_item_count(a, i, v):
    if len(v) == 0:
        raise PricingError("Cart has no line items")


@frozen
class PricingResult:
    """A cart pricing result."""

    currency: str
    """The currency code."""

    line_items: Sequence[LineItem] = field(validator=_validate_line_item_count)
    """The line items in the cart."""

    total_price: int
    """The cart total price."""

    modifiers: Sequence[Modifier] = ()
    """Cart-level modifiers."""

    def _validate_total(self):
        """Validate that the ``total_price`` sums up correctly."""
        total = sum(n.total_price for n in self.line_items)

        for mod in self.modifiers:
            total += mod.amount

        # discounts cannot make the total negative
        if total < 0:
            total = 0

        if total != self.total_price:
            raise PricingError("Cart total price does not sum")

    def __attrs_post_init__(self):
        self._validate_total()


def _get_added_option_ids(inst):
    old_ids = inst.old_data.get("option_ids", [])
    new_ids = inst.new_data.get("option_ids", [])

    return [o for o in new_ids if o not in old_ids]


@frozen
class PricingRequest:
    """Cart data to be priced."""

    currency: str
    """The currency code."""

    event: SimpleEventInfo
    """Event data."""

    cart: CartData
    """The cart data."""


@frozen
class PricingEventBody:
    """The body sent with a :class:`HookEvent.cart_price` event."""

    request: PricingRequest
    prev_result: PricingResult


PricingFunction = Callable[
    [PricingRequest, Optional[PricingResult]], Awaitable[PricingResult]
]
"""Function to get a :class:`PricingResult` from a :class:`PricingRequest`."""
