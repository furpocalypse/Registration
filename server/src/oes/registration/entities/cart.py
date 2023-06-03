"""Cart entities."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from oes.registration.entities.base import Base, JSONData
from oes.registration.models.cart import CART_HASH_SIZE, CartData
from oes.registration.models.pricing import PricingResult
from oes.registration.serialization import get_converter
from oes.registration.util import get_now
from sqlalchemy import String, null
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CartEntity(Base):
    """Cart entity."""

    __tablename__ = "cart"

    id: Mapped[str] = mapped_column(String(CART_HASH_SIZE), primary_key=True)
    """The cart ID."""

    date_created: Mapped[datetime] = mapped_column(default=lambda: get_now())
    """The date the cart was created."""

    cart_data: Mapped[JSONData]
    """The cart data."""

    pricing_result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, default=null()
    )
    """The pricing result."""

    def get_cart_data_model(self) -> CartData:
        """Get a :class:`CartData` instance."""
        return get_converter().structure(self.cart_data, CartData)

    def set_pricing_result(self, pricing_result: PricingResult):
        """Set the pricing result."""
        self.pricing_result = get_converter().unstructure(pricing_result)

    @classmethod
    def create(cls, cart_data: CartData) -> CartEntity:
        """Create a :class:`CartEntity` from a :class:`CartData` instance."""
        data_dict = get_converter().unstructure(cart_data)
        id_ = cart_data.get_hash()
        entity = CartEntity(id=id_, cart_data=data_dict)
        return entity
