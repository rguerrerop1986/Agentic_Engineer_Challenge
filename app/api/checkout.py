"""Checkout HTTP routes."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.checkout import CheckoutRequest, CheckoutResponse
from app.services.checkout_service import (
    CheckoutConfigMissingError,
    calculate_checkout,
    get_active_checkout_config,
    persist_checkout,
)

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a checkout transaction and return calculated totals."""
    try:
        config = get_active_checkout_config(db)
    except CheckoutConfigMissingError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout is not configured.",
        )

    tax_rate = Decimal(config.tax_rate)
    discount_rate = Decimal(config.discount_rate)
    discount_threshold = Decimal(config.discount_threshold)

    totals = calculate_checkout(
        payload.items,
        tax_rate=tax_rate,
        discount_rate=discount_rate,
        discount_threshold=discount_threshold,
    )
    persist_checkout(db, user_id=current_user.id, totals=totals)
    return CheckoutResponse(
        subtotal=totals.subtotal,
        taxes=totals.taxes,
        discount=totals.discount,
        total=totals.total,
    )
