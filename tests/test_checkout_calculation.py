from decimal import Decimal

import pytest

from app.schemas.checkout import CheckoutItemIn
from app.services.checkout_service import calculate_checkout


def test_discount_zero_when_subtotal_not_above_threshold() -> None:
    items = [CheckoutItemIn(name="Widget", unit_price=Decimal("10.00"), quantity=1)]
    totals = calculate_checkout(
        items,
        tax_rate=Decimal("0.13"),
        discount_rate=Decimal("0.10"),
        discount_threshold=Decimal("100.00"),
    )
    assert totals.subtotal == Decimal("10.00")
    assert totals.taxes == Decimal("1.30")
    assert totals.discount == Decimal("0.00")
    assert totals.total == Decimal("11.30")


def test_discount_applied_when_subtotal_strictly_above_threshold() -> None:
    items = [CheckoutItemIn(name="Widget", unit_price=Decimal("60.00"), quantity=2)]
    totals = calculate_checkout(
        items,
        tax_rate=Decimal("0.13"),
        discount_rate=Decimal("0.10"),
        discount_threshold=Decimal("100.00"),
    )
    assert totals.subtotal == Decimal("120.00")
    assert totals.taxes == Decimal("15.60")
    assert totals.discount == Decimal("12.00")
    assert totals.total == Decimal("123.60")


def test_no_discount_when_subtotal_equals_threshold() -> None:
    items = [CheckoutItemIn(name="Edge", unit_price=Decimal("100.00"), quantity=1)]
    totals = calculate_checkout(
        items,
        tax_rate=Decimal("0.13"),
        discount_rate=Decimal("0.10"),
        discount_threshold=Decimal("100.00"),
    )
    assert totals.subtotal == Decimal("100.00")
    assert totals.discount == Decimal("0.00")
    assert totals.taxes == Decimal("13.00")
    assert totals.total == Decimal("113.00")


def test_money_rounding_half_up() -> None:
    items = [CheckoutItemIn(name="A", unit_price=Decimal("10.005"), quantity=1)]
    totals = calculate_checkout(
        items,
        tax_rate=Decimal("0.13"),
        discount_rate=Decimal("0.10"),
        discount_threshold=Decimal("0.00"),
    )
    assert totals.subtotal == Decimal("10.01")
    assert totals.discount == Decimal("1.00")
    assert totals.taxes == Decimal("1.30")
    assert totals.total == Decimal("10.31")
