from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class NfseConfigUpdate(BaseModel):
    provider_company_reference: str | None = None
    environment: str | None = None


class NfseMunicipalCredentialsUpdate(BaseModel):
    login: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=1, max_length=255)
    clear: bool = False


class NfseFocusCredentialsUpdate(BaseModel):
    master_token: str | None = Field(default=None, min_length=8, max_length=500)
    homologation_token: str | None = Field(default=None, min_length=8, max_length=500)
    production_token: str | None = Field(default=None, min_length=8, max_length=500)
    clear: bool = False


class NfseFocusOnboardingRequest(BaseModel):
    mode: Literal["reuse_existing", "manual"]
    confirm: bool
    manual_setup_completed: bool = False


class NfseConsultationIssue(BaseModel):
    service_amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    customer_municipality_code: str | None = Field(
        default=None, min_length=7, max_length=7
    )
    customer_email: str | None = Field(default=None, max_length=255)


class NfseCancelRequest(BaseModel):
    justification: str = Field(min_length=15, max_length=255)
