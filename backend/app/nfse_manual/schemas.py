from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class NfsePrepareRequest(BaseModel):
    service_amount: Optional[Decimal] = Field(
        default=None, gt=0, le=Decimal("9999999999.99")
    )
    description: Optional[str] = Field(default=None, min_length=3, max_length=4000)


class NfseDraftUpdate(BaseModel):
    service_amount: Decimal = Field(gt=0, le=Decimal("9999999999.99"))
    description: str = Field(min_length=3, max_length=4000)


class NfseRegisterRequest(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=80)
    verification_code: Optional[str] = Field(default=None, max_length=120)
    issued_at: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class NfseCancelRequest(BaseModel):
    confirm: bool = False
    reason: str = Field(min_length=5, max_length=2000)
