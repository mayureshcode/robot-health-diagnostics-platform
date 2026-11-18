"""Pure Python tests for external telemetry handling, no ROS installation required."""

from math import inf, nan
from pathlib import Path

import pytest

from rhm_surveillance_adapter.logic import SensorSpec, StreamState, classify, load_profile, parse_profile


def spec() -> SensorSpec:
    """Create reusable sensor definition."""
    return SensorSpec("lidar", "/scan", "LaserScan", 0.5, 2.0)


def test_stale_before_first_sample() -> None:
    """Disconnected sensor must never show as healthy."""
    assert classify(5, StreamState(), spec()) == (3, None)


def test_fresh_warning_stale() -> None:
    """Age thresholds are strict, and future timestamps fail safe."""
    state = StreamState()
    state.observe(5.0)
    assert classify(5.5, state, spec())[0] == 0
    assert classify(5.6, state, spec())[0] == 1
    assert classify(7.01, state, spec())[0] == 3
    assert classify(4.5, state, spec())[0] == 3
    assert classify(nan, state, spec())[0] == 3


def test_observed_rate_and_clock_reset() -> None:
    """Estimate arrival rate without guessing before second sample."""
    state = StreamState()
    state.observe(1.0)
    assert state.ewma_hz is None
    state.observe(1.1)
    assert state.ewma_hz == pytest.approx(10)
    state.observe(0.1)
    assert state.ewma_hz is None
    assert state.count == 1


@pytest.mark.parametrize("values", [
    dict(name="x", topic="scan", message_type="LaserScan"),
    dict(name="bad name", topic="/scan", message_type="LaserScan"),
    dict(name="x", topic="/scan", message_type="NoSuchType"),
    dict(name="x", topic="/scan", message_type="LaserScan", warn_age=2, stale_age=1),
    dict(name="x", topic="/scan", message_type="LaserScan", expected_rate_hz=0),
    dict(name="x", topic="/scan", message_type="LaserScan", warn_age=inf),
])
def test_reject_bad_sensor_config(values: dict) -> None:
    """Invalid input fails configuration before ROS subscription creation."""
    with pytest.raises((ValueError, TypeError)):
        SensorSpec(**values)


def test_profile_rejects_duplicates_and_wrong_asset() -> None:
    """Reject ambiguous names and future unsupported asset routing."""
    base = {"sensors": [{"name": "lidar", "topic": "/scan", "message_type": "LaserScan"}]}
    assert parse_profile(base)[0] == "mobile"
    with pytest.raises(ValueError):
        parse_profile({**base, "asset_id": "arm"})
    with pytest.raises(ValueError):
        parse_profile({**base, "sensors": base["sensors"] * 2})


def test_shipped_profile_parses() -> None:
    """Validate committed operator profile as executable configuration."""
    path = Path(__file__).resolve().parents[1] / "config" / "surveillance.yaml"
    asset, sensors, nodes = load_profile(str(path))
    assert asset == "mobile"
    assert len(sensors) >= 3
    assert "/planner_server" in nodes
