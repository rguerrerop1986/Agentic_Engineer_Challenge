from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer, field_validator


class CheckoutItemIn(BaseModel):
    name: str = Field(min_length=1)
    unit_price: Decimal = Field(gt=0)
    quantity: int = Field(gt=0)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty")
        return v


class CheckoutRequest(BaseModel):
    items: list[CheckoutItemIn] = Field(min_length=1)


class CheckoutResponse(BaseModel):
    subtotal: Decimal
    taxes: Decimal
    discount: Decimal
    total: Decimal

    @field_serializer("subtotal", "taxes", "discount", "total", when_used="json")
    def _money_as_json_number(self, value: Decimal) -> float:
        # Values are already quantized to 2 decimals in checkout_service; float is for JSON only.
        return float(value)
