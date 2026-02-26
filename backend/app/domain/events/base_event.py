from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid


@dataclass(frozen=True, kw_only=True)
class BaseDomainEvent:
    """
    Base metadata para todos eventos de domínio.
    Backward compatible.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_version: int = 1
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def timestamp(self) -> datetime:
        return self.occurred_at

    @property
    def causation_id(self):
        return None

    def to_dict(self):
        data = asdict(self)
        data["event_type"] = self.event_type
        occurred_at = data.get("occurred_at")
        if isinstance(occurred_at, datetime):
            data["occurred_at"] = occurred_at.isoformat()
        return data