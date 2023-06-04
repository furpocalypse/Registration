"""Checkout entities."""
import copy
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from oes.registration.entities.base import PKUUID, Base, JSONData
from oes.registration.models.cart import CART_HASH_SIZE, CartData
from oes.registration.models.pricing import PricingResult
from oes.registration.serialization import get_converter
from oes.registration.util import get_now
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

SERVICE_ID_MAX_LENGTH = 32
"""Max length of a service ID."""


class CheckoutState(str, Enum):
    """State of a checkout."""

    pending = "pending"
    """The checkout is open."""

    canceled = "canceled"
    """The checkout has been canceled."""

    complete = "complete"
    """The checkout is complete."""


class CheckoutEntity(Base):
    """Cart checkout entity."""

    __tablename__ = "checkout"

    id: Mapped[PKUUID]
    """The checkout ID."""

    state: Mapped[CheckoutState] = mapped_column(default=CheckoutState.pending)
    """The checkout state."""

    date_created: Mapped[datetime] = mapped_column(default=lambda: get_now())
    """The date the checkout was created."""

    date_closed = Mapped[Optional[datetime]]
    """The date the checkout was canceled or completed."""

    changes_applied: Mapped[bool] = mapped_column(nullable=False, default=False)
    """Whether the changes have been applied."""

    service: Mapped[str] = mapped_column(String(SERVICE_ID_MAX_LENGTH))
    """The ID of the payment service provider."""

    external_id: Mapped[Optional[str]]
    """The ID of the checkout via the payment service provider."""

    external_data: Mapped[JSONData]
    """Additional checkout data specific to the payment service provider."""

    cart_id: Mapped[str] = mapped_column(String(CART_HASH_SIZE))
    """The ID of the cart data."""

    cart_data: Mapped[JSONData]
    """The cart data in the checkout."""

    pricing_result: Mapped[JSONData]
    """The pricing result data."""

    def __repr__(self):
        return (
            "<Checkout "
            f"id={self.id} "
            f"service={self.service} "
            f"external_id={self.external_id}"
            ">"
        )

    @hybrid_property
    def is_open(self) -> bool:
        """Whether the checkout is open/pending."""
        return self.state == CheckoutState.pending

    @hybrid_property
    def is_closed(self) -> bool:
        """Whether the checkout is closed (complete/canceled)."""
        return self.state != CheckoutState.pending

    def complete(self, date_completed: Optional[datetime] = None) -> bool:
        """Set the state to ``complete``.

        Args:
            date_completed: The date the checkout was completed.

        Returns:
            Whether a change was made.
        """
        if self.state == CheckoutState.complete:
            return False

        if self.state != CheckoutState.pending:
            raise ValueError("Checkout is canceled")

        self.state = CheckoutState.complete
        self.date_closed = date_completed if date_completed is not None else get_now()
        return True

    def cancel(self, date_canceled: Optional[datetime] = None) -> bool:
        """Set the state to ``canceled``.

        Args:
            date_canceled: The date the checkout was canceled.

        Returns:
            Whether a change was made.
        """
        if self.state == CheckoutState.canceled:
            return False

        if self.state != CheckoutState.pending:
            raise ValueError("Checkout is complete")

        self.state = CheckoutState.canceled
        self.date_closed = date_canceled if date_canceled is not None else get_now()
        return True

    def set_service_info(
        self,
        service: str,
        external_id: str,
        external_data: Optional[dict[str, Any]] = None,
    ):
        """Update the service info."""
        self.service = service
        self.external_id = external_id
        self.external_data = (
            copy.deepcopy(external_data) if external_data is not None else {}
        )

    def set_cart_data(self, cart_data: CartData):
        """Set the cart data."""
        self.cart_id = cart_data.get_hash()
        self.cart_data = get_converter().unstructure(cart_data)

    def get_cart_data(self) -> CartData:
        """Get the :class:`CartData` model."""
        return get_converter().structure(self.cart_data or {}, CartData)

    def set_pricing_result(self, pricing_result: PricingResult):
        """Set the pricing result."""
        self.pricing_result = get_converter().unstructure(pricing_result)

    def get_pricing_result(self) -> PricingResult:
        """Get the :class:`PricingResult`."""
        return get_converter().structure(self.pricing_result or {}, PricingResult)
