"""ROS-independent validation and sensor freshness/rate calculations.

A rate is calculated from ROS-clock arrival timestamps, never from wall time.
The adapter does not infer measurement quality from message frequency alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import yaml


SUPPORTED_TYPES: dict[str, str] = {
    "PointCloud2": "sensor_msgs/msg/PointCloud2",
    "LaserScan": "sensor_msgs/msg/LaserScan",
    "Imu": "sensor_msgs/msg/Imu",
    "Odometry": "nav_msgs/msg/Odometry",
    "Image": "sensor_msgs/msg/Image",
    "NavSatFix": "sensor_msgs/msg/NavSatFix",
    "JointState": "sensor_msgs/msg/JointState",
}


@dataclass(frozen=True)
class SensorSpec:
    """Validated external ROS topic and expected arrival freshness."""

    name: str
    topic: str
    message_type: str
    warn_age: float = 0.5
    stale_age: float = 2.0
    expected_rate_hz: float | None = None

    def __post_init__(self) -> None:
        if not self.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in self.name):
            raise ValueError("sensor name must contain only lowercase letters, numbers and underscores")
        if not self.topic.startswith("/") or any(c.isspace() for c in self.topic):
            raise ValueError("sensor topic must be an absolute ROS topic without spaces")
        if self.message_type not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported message_type: {self.message_type}")
        if (not isfinite(self.warn_age) or not isfinite(self.stale_age)
                or not 0 <= self.warn_age < self.stale_age):
            raise ValueError("require finite 0 <= warn_age < stale_age")
        if self.expected_rate_hz is not None and (
                not isfinite(self.expected_rate_hz) or self.expected_rate_hz <= 0):
            raise ValueError("expected_rate_hz must be finite and positive")


@dataclass
class StreamState:
    """Mutable per-stream observation state; caller holds node lock."""

    last_time: float | None = None
    previous_time: float | None = None
    count: int = 0
    ewma_hz: float | None = None

    def observe(self, ros_time: float, smoothing: float = 0.25) -> None:
        """Record a sample using the ROS clock; handle time jumps as stale."""
        if not isfinite(ros_time) or ros_time < 0:
            return
        if self.last_time is not None and ros_time < self.last_time:
            self.last_time = None
            self.previous_time = None
            self.ewma_hz = None
            self.count = 0
        if self.last_time is not None and ros_time > self.last_time:
            instant_hz = 1.0 / (ros_time - self.last_time)
            self.ewma_hz = (instant_hz if self.ewma_hz is None
                            else smoothing * instant_hz + (1 - smoothing) * self.ewma_hz)
        self.previous_time = self.last_time
        self.last_time = ros_time
        self.count += 1


def classify(now: float, stream: StreamState, spec: SensorSpec) -> tuple[int, float | None]:
    """Return diagnostic status and age (0 OK, 1 WARN, 3 STALE)."""
    if stream.last_time is None or not isfinite(now):
        return 3, None
    age = now - stream.last_time
    if age < 0 or age > spec.stale_age:
        return 3, max(0.0, age)
    if age > spec.warn_age:
        return 1, age
    return 0, age


def parse_profile(data: Any) -> tuple[str, tuple[SensorSpec, ...], tuple[str, ...]]:
    """Validate a YAML-decoded profile without requiring ROS imports."""
    if not isinstance(data, dict):
        raise ValueError("profile must be a YAML mapping")
    asset_id = data.get("asset_id", "mobile")
    if not isinstance(asset_id, str) or asset_id != "mobile":
        raise ValueError("existing aggregator supports asset_id='mobile' only")
    sensors = data.get("sensors")
    if not isinstance(sensors, list) or not sensors:
        raise ValueError("profile requires a nonempty sensors list")
    if len(sensors) > 32:
        raise ValueError("at most 32 sensor streams allowed")
    parsed: list[SensorSpec] = []
    names: set[str] = set()
    for item in sensors:
        if not isinstance(item, dict):
            raise ValueError("each sensor entry must be a mapping")
        spec = SensorSpec(**item)
        if spec.name in names:
            raise ValueError(f"duplicate sensor name: {spec.name}")
        names.add(spec.name)
        parsed.append(spec)
    nodes = data.get("watch_nodes", [])
    if not isinstance(nodes, list) or any(
            not isinstance(n, str) or not n.startswith("/") or len(n) > 128 for n in nodes):
        raise ValueError("watch_nodes must be a list of absolute ROS node names")
    return asset_id, tuple(parsed), tuple(nodes)


def load_profile(path: str) -> tuple[str, tuple[SensorSpec, ...], tuple[str, ...]]:
    """Read and validate an operator-supplied YAML profile."""
    with open(path, encoding="utf-8") as handle:
        return parse_profile(yaml.safe_load(handle))
