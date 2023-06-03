import uuid

import pytest
from oes.registration.models.pricing import (
    LineItem,
    Modifier,
    PricingError,
    PricingResult,
)


def test_line_item_validation_negative():
    id_ = uuid.uuid4()
    with pytest.raises(PricingError):
        LineItem(
            type_id="item1",
            registration_id=id_,
            name="Item 1",
            price=-1,
            total_price=-1,
        )


def test_line_item_validation_total():
    id_ = uuid.uuid4()
    with pytest.raises(PricingError):
        LineItem(
            type_id="item1",
            registration_id=id_,
            name="Item 1",
            price=1,
            total_price=2,
        )

    with pytest.raises(PricingError):
        id_ = uuid.uuid4()
        LineItem(
            registration_id=id_,
            type_id="item1",
            name="Item 1",
            price=10,
            modifiers=(
                Modifier(
                    type_id="mod1",
                    name="Modifier",
                    amount=-5,
                ),
            ),
            total_price=10,
        )


def test_cart_validation_total():
    id_ = uuid.uuid4()
    with pytest.raises(PricingError):
        PricingResult(
            currency="USD",
            line_items=(
                LineItem(
                    type_id="item1",
                    registration_id=id_,
                    name="Item 1",
                    price=10,
                    modifiers=(
                        Modifier(
                            type_id="mod1",
                            name="Modifier",
                            amount=-5,
                        ),
                    ),
                    total_price=5,
                ),
            ),
            total_price=10,
        )


def test_line_item_min_0():
    id_ = uuid.uuid4()
    PricingResult(
        currency="USD",
        line_items=(
            LineItem(
                type_id="item1",
                registration_id=id_,
                name="Item 1",
                price=10,
                modifiers=(
                    Modifier(
                        type_id="mod1",
                        name="Modifier",
                        amount=-15,
                    ),
                ),
                total_price=0,
            ),
        ),
        total_price=0,
    )


def test_pricing_result_min_0():
    id_ = uuid.uuid4()
    PricingResult(
        currency="USD",
        line_items=(
            LineItem(
                type_id="item1",
                registration_id=id_,
                name="Item 1",
                price=10,
                total_price=10,
            ),
        ),
        modifiers=(
            Modifier(
                type_id="mod2",
                name="Test",
                amount=-15,
            ),
        ),
        total_price=0,
    )


def test_pricing_result():
    id_ = uuid.uuid4()
    PricingResult(
        currency="USD",
        line_items=(
            LineItem(
                type_id="item1",
                registration_id=id_,
                name="Item 1",
                price=10,
                modifiers=(
                    Modifier(
                        type_id="mod1",
                        name="Modifier",
                        amount=-5,
                    ),
                ),
                total_price=5,
            ),
            LineItem(
                type_id="item1",
                registration_id=id_,
                name="Item 1",
                price=10,
                modifiers=(
                    Modifier(
                        type_id="mod1",
                        name="Modifier",
                        amount=5,
                    ),
                ),
                total_price=15,
            ),
        ),
        total_price=20,
    )


def test_pricing_result_no_line_items():
    with pytest.raises(PricingError):
        PricingResult(
            currency="USD",
            line_items=(),
            total_price=0,
        )
