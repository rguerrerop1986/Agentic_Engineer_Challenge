"""initial schema and seed data

Revision ID: 001_initial
Revises:
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEMO_PASSWORD_HASH = "$2b$12$c7tiYXhtHLT3BALAm4i3POjZnPGenUCLPM/yMox05F2WbHxBSWCIq"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "checkout_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tax_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("discount_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("discount_threshold", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "checkout_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("taxes", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_checkout_transactions_user_id"), "checkout_transactions", ["user_id"], unique=False)

    op.create_table(
        "checkout_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("checkout_transaction_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["checkout_transaction_id"], ["checkout_transactions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_checkout_items_checkout_transaction_id"),
        "checkout_items",
        ["checkout_transaction_id"],
        unique=False,
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO checkout_config (tax_rate, discount_rate, discount_threshold, is_active)
            VALUES (:tax_rate, :discount_rate, :discount_threshold, :is_active)
            """
        ),
        {
            "tax_rate": 0.13,
            "discount_rate": 0.10,
            "discount_threshold": 100.00,
            "is_active": True,
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO users (email, hashed_password, is_active)
            VALUES (:email, :hashed_password, :is_active)
            """
        ),
        {
            "email": "demo@example.com",
            "hashed_password": DEMO_PASSWORD_HASH,
            "is_active": True,
        },
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_checkout_items_checkout_transaction_id"), table_name="checkout_items")
    op.drop_table("checkout_items")
    op.drop_index(op.f("ix_checkout_transactions_user_id"), table_name="checkout_transactions")
    op.drop_table("checkout_transactions")
    op.drop_table("checkout_config")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
