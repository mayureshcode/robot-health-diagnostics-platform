"""Public Pydantic schemas for all dashboard API and WebSocket messages."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field


class SensorView(BaseModel):
    """Health record with explicit data provenance."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    status: int = Field(ge=0, le=3)
    score: float = Field(ge=0, le=100)
    summary: str = Field(max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    rate_hz: float | None = Field(default=None, ge=0)
    age_seconds: float | None = Field(default=None, ge=0)
    sample_count: int | None = Field(default=None, ge=0)
    last_ros_time: float | None = None


class FaultView(BaseModel):
    """Observed status change or an explicitly published fault event."""

    id: str = Field(max_length=120)
    origin: str = Field(pattern="^(transition|fault_event)$")
    subsystem: str = Field(max_length=160)
    severity: int = Field(ge=0, le=3)
    text: str = Field(max_length=300)
    time_utc: str


class Snapshot(BaseModel):
    """Entire UI state, with unknown values represented as null."""

    asset_id: str = "mobile"
    connected: bool = False
    received_health: bool = False
    status: int | None = Field(default=None, ge=0, le=3)
    health_score: float | None = Field(default=None, ge=0, le=100)
    last_ros_time: float | None = None
    sensors: list[SensorView] = Field(default_factory=list)
    events: list[FaultView] = Field(default_factory=list)
    information: str = "Awaiting live ROS health messages"


class WebSocketMessage(BaseModel):
    """Versioned WebSocket envelope for clients and API smoke tests."""

    type: str = Field(pattern="^snapshot$")
    version: int = 1
    data: Snapshot


class WebSocketAuth(BaseModel):
    """First WebSocket message required when a dashboard token is configured."""

    token: str = Field(min_length=1, max_length=1024)


class HealthStore:
    """Thread-safe data store shared between ROS callbacks and ASGI requests."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot = Snapshot()
        self._details: dict[str, dict[str, str]] = {}
        self._counter = 0

    def snapshot(self) -> Snapshot:
        """Return a deep copy to avoid mutations across threads."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def update_diagnostics(self, entries: list[tuple[str, dict[str, str]]]) -> None:
        """Cache detailed diagnostic attributes; no sensor messages are invented."""
        with self._lock:
            for name, info in entries:
                self._details[name] = {str(k)[:80]: str(v)[:200] for k, v in info.items()}

    def update_health(self, *, ros_time: float, asset_id: str, status: int,
                      score: float, subsystems: list[dict[str, object]]) -> None:
        """Merge genuine health and diagnostic reports, recording transitions."""
        with self._lock:
            previous = {item.name: item.status for item in self._snapshot.sensors}
            parsed: list[SensorView] = []
            for entry in subsystems[:64]:
                name = str(entry["name"])[:160]
                metadata = self._details.get(name, {})
                rate = _parse_nonnegative(metadata.get("rate_hz"))
                age = _parse_nonnegative(metadata.get("age_seconds"))
                count = _parse_count(metadata.get("samples_received"))
                item = SensorView(
                    name=name, status=int(entry["status"]),
                    score=max(0.0, min(100.0, float(entry["score"]))),
                    summary=str(entry.get("summary", ""))[:200],
                    topic=metadata.get("topic"), rate_hz=rate,
                    age_seconds=age, sample_count=count,
                    last_ros_time=ros_time,
                )
                parsed.append(item)
                if name in previous and previous[name] != item.status:
                    self._counter += 1
                    self._snapshot.events.insert(0, FaultView(
                        id=f"transition-{self._counter}", origin="transition",
                        subsystem=name, severity=item.status,
                        text=f"Observed status {previous[name]} → {item.status}",
                        time_utc=datetime.now(timezone.utc).isoformat(),
                    ))
            self._snapshot.events = self._snapshot.events[:80]
            self._snapshot.sensors = parsed
            self._snapshot.asset_id = str(asset_id)[:100]
            self._snapshot.status = max(0, min(3, int(status)))
            self._snapshot.health_score = max(0.0, min(100.0, float(score)))
            self._snapshot.last_ros_time = float(ros_time)
            self._snapshot.received_health = True
            self._snapshot.connected = True
            self._snapshot.information = "Live ROS diagnostics; simulation/telemetry source"

    def add_fault(self, *, event_id: str, subsystem: str, severity: int,
                  description: str) -> None:
        """Record a real /fault_events message without inferring a new failure."""
        with self._lock:
            self._snapshot.events.insert(0, FaultView(
                id=event_id[:120], origin="fault_event", subsystem=subsystem[:160],
                severity=max(0, min(3, severity)), text=description[:300],
                time_utc=datetime.now(timezone.utc).isoformat(),
            ))
            self._snapshot.events = self._snapshot.events[:80]

    def mark_disconnected(self) -> None:
        """Fail safe if ROS subscription thread dies or stops."""
        with self._lock:
            self._snapshot.connected = False
            self._snapshot.information = "ROS dashboard bridge disconnected; last readings are historical"


def _parse_nonnegative(value: str | None) -> float | None:
    """Ignore missing and invalid numeric fields rather than inventing values."""
    if not value:
        return None
    try:
        n = float(value)
        if not (0 <= n < float("inf")):
            return None
        return n
    except (TypeError, ValueError):
        return None


def _parse_count(value: str | None) -> int | None:
    """Accept nonnegative counters, reject malformed metadata."""
    if value is None:
        return None
    try:
        count = int(value)
        return count if count >= 0 else None
    except (TypeError, ValueError):
        return None
