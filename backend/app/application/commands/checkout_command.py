from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CheckoutCommand:
    cliente_id: int
    origem: str
    tenant_id: str
    items: List[Dict]
    idempotency_key: str | None = None
