"""Contrato comercial: dados fiscais e identidade da empresa vêm do CorePet."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Money = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,9})(\.[0-9]{1,2})?$")]
Quantity = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,9})(\.[0-9]{1,4})?$")]
UnitPrice = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,9})(\.[0-9]{1,10})?$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Address(StrictModel):
    street: str | None = Field(default=None, max_length=120)
    number: str | None = Field(default=None, max_length=60)
    complement: str | None = Field(default=None, max_length=60)
    district: str | None = Field(default=None, max_length=60)
    city: str | None = Field(default=None, max_length=60)
    municipality_code: str | None = Field(default=None, max_length=7)
    state: str | None = Field(default=None, max_length=2)
    postal_code: str | None = Field(default=None, max_length=9)


class Recipient(StrictModel):
    name: str | None = Field(default=None, max_length=60)
    document: str | None = Field(default=None, max_length=20)
    ie_status: Literal["1", "2", "9"] = "9"
    state_registration: str | None = Field(default=None, max_length=20)
    address: Address | None = None


class OrderItem(StrictModel):
    external_item_id: str = Field(min_length=1, max_length=100)
    seller_sku: str = Field(min_length=1, max_length=100)
    asin: str | None = Field(default=None, max_length=30)
    quantity: Quantity
    unit_price: UnitPrice
    gross_amount: Money
    discount_amount: Money


class Totals(StrictModel):
    currency: Literal["BRL"] = "BRL"
    products: Money
    discount: Money
    freight: Money
    invoice_total: Money


class Payment(StrictModel):
    fiscal_method: str = Field(min_length=2, max_length=2)
    amount: Money
    integration_type: Literal["1", "2"] | None = None


class OrderInput(StrictModel):
    schema_version: Literal["1.0"]
    channel: Literal["amazon"]
    seller_id: str = Field(min_length=1, max_length=80)
    marketplace_id: Literal["A2Q3Y263D00KWC"]
    external_order_id: str = Field(pattern=r"^[0-9]{3}-[0-9]{7}-[0-9]{7}$")
    source_revision: int = Field(gt=0, strict=True)
    order_status: str = Field(min_length=1, max_length=40)
    purchased_at: datetime
    source_updated_at: datetime
    emitter_cnpj: str = Field(pattern=r"^[0-9]{14}$")
    recipient: Recipient | None = None
    items: list[OrderItem] = Field(default_factory=list, max_length=500)
    totals: Totals
    payments: list[Payment] = Field(default_factory=list, max_length=20)
    buyer_paid_total: Money | None = None
    source_evidence: dict[Literal["tax", "recipient", "payment"], str] = Field(
        default_factory=dict
    )

    @field_validator("purchased_at", "source_updated_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("Informe data com fuso horário.")
        return value.astimezone(timezone.utc)


class AccountInput(StrictModel):
    channel: Literal["amazon"] = "amazon"
    seller_id: str = Field(min_length=1, max_length=80)
    marketplace_id: Literal["A2Q3Y263D00KWC"] = "A2Q3Y263D00KWC"
    emitter_cnpj: str = Field(pattern=r"^[0-9]{14}$")
    active: bool = False
    auto_issue_enabled: bool = False
    upload_enabled: bool = False
    discount_policy: Literal["source_discounts", "buyer_payment_total"] = (
        "source_discounts"
    )


class MappingInput(StrictModel):
    account_id: int = Field(gt=0)
    seller_sku: str = Field(min_length=1, max_length=100)
    product_id: int = Field(gt=0)
    active: bool = True


class IssueInput(StrictModel):
    expected_revision: int = Field(gt=0)
    expected_payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReviewInput(StrictModel):
    acknowledge_historical: Literal[True]
