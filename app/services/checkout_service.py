"""Checkout pricing calculations and persistence."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.checkout import CheckoutConfig, CheckoutItem, CheckoutTransaction
from app.schemas.checkout import CheckoutItemIn

TWO_PLACES = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Round a Decimal to two decimal places using half-up."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CheckoutTotals:
    """Computed checkout amounts and per-line totals for persistence."""

    subtotal: Decimal
    taxes: Decimal
    discount: Decimal
    total: Decimal
    lines: list[tuple[CheckoutItemIn, Decimal]]


class CheckoutConfigMissingError(Exception):
    """Raised when no active checkout configuration row exists."""


def get_active_checkout_config(session: Session) -> CheckoutConfig:
    """Return the newest active checkout config row."""
    stmt = (
        select(CheckoutConfig)
        .where(CheckoutConfig.is_active.is_(True))
        .order_by(CheckoutConfig.id.desc())
        .limit(1)
    )
    row = session.scalars(stmt).first()
    if row is None:
        raise CheckoutConfigMissingError("No active checkout configuration found.")
    return row


def calculate_checkout(
    items: list[CheckoutItemIn],
    *,
    tax_rate: Decimal,
    discount_rate: Decimal,
    discount_threshold: Decimal,
) -> CheckoutTotals:
    """Compute subtotal, taxes, discount, total, and line totals from validated items."""
    lines: list[tuple[CheckoutItemIn, Decimal]] = []
    subtotal_raw = Decimal(0)
    for item in items:
        unit = Decimal(item.unit_price)
        qty = Decimal(item.quantity)
        line = money(unit * qty)
        lines.append((item, line))
        subtotal_raw += unit * qty

    subtotal = money(subtotal_raw)
    taxes = money(subtotal * tax_rate)
    threshold = money(discount_threshold)
    discount = money(subtotal * discount_rate) if subtotal > threshold else money(Decimal(0))
    total = money(subtotal + taxes - discount)
    return CheckoutTotals(
        subtotal=subtotal,
        taxes=taxes,
        discount=discount,
        total=total,
        lines=lines,
    )


def persist_checkout(
    session: Session,
    *,
    user_id: int,
    totals: CheckoutTotals,
) -> CheckoutTransaction:
    """Insert a checkout transaction and its line items, then commit."""
    tx = CheckoutTransaction(
        user_id=user_id,
        subtotal=totals.subtotal,
        taxes=totals.taxes,
        discount=totals.discount,
        total=totals.total,
    )
    session.add(tx)
    session.flush()
    for item, line_total in totals.lines:
        session.add(
            CheckoutItem(
                checkout_transaction_id=tx.id,
                name=item.name.strip(),
                unit_price=money(Decimal(item.unit_price)),
                quantity=item.quantity,
                line_total=line_total,
            )
        )
    session.commit()
    session.refresh(tx)
    return tx
