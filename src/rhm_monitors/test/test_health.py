"""Logic tests collected by colcon's ament_python pytest runner."""
from math import inf, nan

import pytest
from hypothesis import given, strategies as st
from rhm_monitors.logic.health import (
    Debouncer, Status, Thresholds, battery_status, health_score, sensor_status,
)


def test_sensor_threshold_boundaries() -> None:
    """Age thresholds are strict comparisons and missing input is stale."""
    limits = Thresholds(warn_age=0.5, error_age=2.0)
    assert sensor_status(10.0, 9.5, limits) == Status.OK
    assert sensor_status(10.0, 9.49, limits) == Status.WARN
    assert sensor_status(10.0, 8.0, limits) == Status.WARN
    assert sensor_status(10.0, 7.99, limits) == Status.STALE
    assert sensor_status(10.0, None, limits) == Status.STALE
    assert sensor_status(10.0, 10.1, limits) == Status.STALE


@pytest.mark.parametrize('value', [nan, inf, -inf, -0.1, 101.0])
def test_invalid_battery_readings_are_stale(value: float) -> None:
    """Never accept an out-of-domain battery measurement as healthy."""
    assert battery_status(value) == Status.STALE


@pytest.mark.parametrize('warn,error', [(1, 1), (2, 1), (-1, 2), (nan, 2), (0.1, inf)])
def test_invalid_age_config_rejected(warn: float, error: float) -> None:
    """Threshold configuration must be ordered and finite."""
    with pytest.raises(ValueError):
        Thresholds(warn_age=warn, error_age=error)


def test_battery_exact_thresholds() -> None:
    """Battery thresholds are exclusive on the low side."""
    assert battery_status(9.99) == Status.ERROR
    assert battery_status(10.0) == Status.WARN
    assert battery_status(24.99) == Status.WARN
    assert battery_status(25.0) == Status.OK


def test_missing_health_has_zero_score() -> None:
    """No observed subsystems must not yield a positive health score."""
    assert health_score([]) == 0.0
    assert health_score([Status.STALE]) == 0.0


@given(st.lists(st.sampled_from(list(Status)), min_size=1, max_size=50))
def test_health_score_monotonic(statuses: list[Status]) -> None:
    """Improving a sample to OK must not decrease the health score."""
    prior = health_score(statuses)
    assert 0 <= prior <= 100
    for index in range(len(statuses)):
        changed = list(statuses)
        changed[index] = Status.OK
        assert health_score(changed) >= prior


@given(st.integers(min_value=1, max_value=25))
def test_debouncer_change_after_n(required: int) -> None:
    """A stable state changes after exactly N consecutive observations."""
    d = Debouncer(required)
    for _ in range(required - 1):
        assert d.update(Status.OK) == Status.STALE
    assert d.update(Status.OK) == Status.OK
    for _ in range(required - 1):
        assert d.update(Status.WARN) == Status.OK
    assert d.update(Status.WARN) == Status.WARN
    assert d.update(Status.STALE) == Status.STALE


def test_debounce_cancels_interrupted_candidate() -> None:
    """Nonconsecutive observations cannot trigger a severity change."""
    d = Debouncer(2)
    assert d.update(Status.WARN) == Status.STALE
    assert d.update(Status.ERROR) == Status.STALE
    assert d.update(Status.WARN) == Status.STALE
    assert d.update(Status.WARN) == Status.WARN


def test_nonfinite_sensor_time_is_stale() -> None:
    """ROS clock anomalies and malformed sample times fail safe."""
    limits = Thresholds()
    assert sensor_status(float('nan'), 2.0, limits) == Status.STALE
    assert sensor_status(3.0, float('inf'), limits) == Status.STALE


def test_invalid_debouncer_configuration() -> None:
    """Zero consecutive samples is never a valid debounce configuration."""
    with pytest.raises(ValueError):
        Debouncer(0)


def test_debouncer_repeated_stable_observation() -> None:
    """Reobserving a stable state clears a pending transition."""
    debouncer = Debouncer(2)
    assert debouncer.update(Status.OK) == Status.STALE
    assert debouncer.update(Status.OK) == Status.OK
    assert debouncer.update(Status.WARN) == Status.OK
    assert debouncer.update(Status.OK) == Status.OK
    assert debouncer.update(Status.WARN) == Status.OK
    assert debouncer.update(Status.WARN) == Status.WARN
