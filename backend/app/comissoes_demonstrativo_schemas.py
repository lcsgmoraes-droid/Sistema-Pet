from datetime import date
from typing import Optional

from pydantic import BaseModel


class FecharComissoesRequest(BaseModel):
    """Schema para fechamento de comissoes."""

    comissoes_ids: list[int]
    data_pagamento: date
    observacao: Optional[str] = None
