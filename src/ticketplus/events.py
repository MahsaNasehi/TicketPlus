"""Small idempotent event bus used by the local reference environment."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: str
    payload: dict[str, object]


Handler = Callable[[DomainEvent], None]


class EventBus:
    """Synchronous local adapter with the idempotency contract used by Kafka consumers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._processed: set[tuple[int, str]] = set()
        self._events: list[DomainEvent] = []
        self._lock = RLock()

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, object],
        *,
        event_id: str | None = None,
    ) -> DomainEvent:
        event = DomainEvent(
            event_id=event_id or str(uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at=datetime.now(UTC).isoformat(),
            payload=payload,
        )
        with self._lock:
            self._events.append(event)
            for handler in self._handlers[event_type]:
                delivery_key = (id(handler), event.event_id)
                if delivery_key not in self._processed:
                    handler(event)
                    self._processed.add(delivery_key)
        return event

    @property
    def events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._events)

