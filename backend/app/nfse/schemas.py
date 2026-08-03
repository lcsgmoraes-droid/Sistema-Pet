from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class NfseConfigUpdate(BaseModel):
    service_list_item: str | None = None
    cnae_code: str | None = None
    iss_rate: Decimal | None = Field(default=None, ge=0, le=100)
    iss_withheld: bool | None = None
    operation_nature: str | None = None
    special_tax_regime: str | None = None
    simple_national: bool | None = None
    cultural_incentive: bool | None = None
    provider_company_reference: str | None = None
    environment: str | None = None


class NfseConsultationIssue(BaseModel):
    service_amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    customer_municipality_code: str | None = Field(
        default=None, min_length=7, max_length=7
    )
    customer_email: str | None = Field(default=None, max_length=255)


class NfseCancelRequest(BaseModel):
    justification: str = Field(min_length=15, max_length=255)
