"""ROS-independent health logic; all timestamps are caller-supplied ROS time."""
from dataclasses import dataclass
from enum import IntEnum
from math import isfinite


class Status(IntEnum):
    """Ordered severity except STALE, which is treated as most severe."""

    OK = 0
    WARN = 1
    ERROR = 2
    STALE = 3


@dataclass(frozen=True)
class Thresholds:
    """Maximum acceptable age of a sensor sample, in seconds."""

    warn_age: float = 0.5
    error_age: float = 2.0

    def __post_init__(self) -> None:
        if (not isfinite(self.warn_age) or not isfinite(self.error_age)
                or not 0 <= self.warn_age < self.error_age):
            raise ValueError('require finite 0 <= warn_age < error_age')


def sensor_status(now: float, last_seen: float | None, limits: Thresholds) -> Status:
    """Classify staleness; absent, future and non-finite timestamps fail safe."""
    if last_seen is None or not isfinite(now) or not isfinite(last_seen):
        return Status.STALE
    age = now - last_seen
    if age < 0:
        return Status.STALE
    if age > limits.error_age:
        return Status.STALE
    if age > limits.warn_age:
        return Status.WARN
    return Status.OK


def battery_status(percent: float) -> Status:
    """Evaluate battery percentage with invalid measurements failing safe."""
    if not isfinite(percent) or percent < 0 or percent > 100:
        return Status.STALE
    if percent < 10:
        return Status.ERROR
    if percent < 25:
        return Status.WARN
    return Status.OK


def health_score(statuses: list[Status]) -> float:
    """Arithmetic mean of fixed severity scores; empty input is zero."""
    weights = {Status.OK: 100.0, Status.WARN: 65.0,
               Status.ERROR: 20.0, Status.STALE: 0.0}
    if not statuses:
        return 0.0
    return sum(weights[s] for s in statuses) / len(statuses)


class Debouncer:
    """Require consecutive observations before changing severity."""

    def __init__(self, required: int = 3) -> None:
        if required < 1:
            raise ValueError('required must be >= 1')
        self.required = required
        self.status = Status.STALE
        self._candidate = self.status
        self._count = 0

    def update(self, observed: Status) -> Status:
        """Update stable state; STALE propagates immediately for fail safety."""
        if observed == Status.STALE:
            self.status = observed
            self._candidate = observed
            self._count = 0
            return self.status
        if observed == self.status:
            self._candidate = observed
            self._count = 0
        else:
            self._count = self._count + 1 if observed == self._candidate else 1
            self._candidate = observed
            if self._count >= self.required:
                self.status = observed
                self._count = 0
        return self.status
