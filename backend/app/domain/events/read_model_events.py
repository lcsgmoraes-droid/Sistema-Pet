from dataclasses import dataclass
from datetime import datetime

@dataclass
class ReadModelUpdatedEvent:
    model: str
    occurred_at: datetime
