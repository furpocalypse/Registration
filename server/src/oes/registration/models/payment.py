"""Payment models."""
from datetime import datetime
from typing import Any, Optional

from attrs import frozen
from oes.registration.entities.checkout import CheckoutState


@frozen
class PaymentServiceCheckout:
    """Checkout data."""

    service: str
    """The payment service ID."""

    id: str
    """The checkout ID in the payment service."""

    state: CheckoutState
    """The state of the checkout."""

    date_created: Optional[datetime] = None
    """The date the checkout was created with the service."""

    date_closed: Optional[datetime] = None
    """The date the checkout was closed with the service."""

    checkout_data: Optional[dict[str, Any]] = None
    """Additional checkout data with the service."""

    response_data: Optional[dict[str, Any]] = None
    """Additional checkout data with the service that will not be stored."""

    @property
    def is_open(self) -> bool:
        """Whether the checkout is open."""
        return self.state == CheckoutState.pending

    @property
    def is_closed(self) -> bool:
        """Whether the checkout is closed/canceled."""
        return self.state != CheckoutState.pending
