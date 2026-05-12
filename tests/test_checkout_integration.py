from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.checkout import CheckoutItem, CheckoutTransaction


def test_checkout_without_token_returns_401(integration_harness) -> None:
    client = integration_harness.client
    response = client.post(
        "/checkout",
        json={"items": [{"name": "A", "unit_price": "10.00", "quantity": 1}]},
    )
    assert response.status_code == 401


def test_checkout_with_valid_token_returns_200_and_correct_totals(integration_harness) -> None:
    client = integration_harness.client
    login = client.post(
        "/auth/login",
        json={"email": "integration-test@example.com", "password": "test-secret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.post(
        "/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"name": "Widget", "unit_price": "60.00", "quantity": 2}]},
    )
    assert response.status_code == 200
    body = response.json()

    # JSON numbers (not strings); values: subtotal 120, tax 15.60, discount 12, total 123.60
    assert isinstance(body["subtotal"], (int, float))
    assert isinstance(body["taxes"], (int, float))
    assert isinstance(body["discount"], (int, float))
    assert isinstance(body["total"], (int, float))

    assert body["subtotal"] == pytest.approx(120.0, abs=1e-9)
    assert body["taxes"] == pytest.approx(15.6, abs=1e-9)
    assert body["discount"] == pytest.approx(12.0, abs=1e-9)
    assert body["total"] == pytest.approx(123.6, abs=1e-9)


def test_checkout_transaction_persisted_correctly(integration_harness) -> None:
    client = integration_harness.client
    token = client.post(
        "/auth/login",
        json={"email": "integration-test@example.com", "password": "test-secret"},
    ).json()["access_token"]

    response = client.post(
        "/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"items": [{"name": "Pen", "unit_price": "5.00", "quantity": 3}]},
    )
    assert response.status_code == 200

    with integration_harness.session_factory() as s:
        tx = s.scalars(select(CheckoutTransaction)).one()
        assert tx.user_id == 1
        assert tx.subtotal == Decimal("15.00")
        assert tx.taxes == Decimal("1.95")
        assert tx.discount == Decimal("0.00")
        assert tx.total == Decimal("16.95")

        items = s.scalars(select(CheckoutItem).where(CheckoutItem.checkout_transaction_id == tx.id)).all()
        assert len(items) == 1
        assert items[0].name == "Pen"
        assert items[0].quantity == 3
        assert items[0].unit_price == Decimal("5.00")
        assert items[0].line_total == Decimal("15.00")
