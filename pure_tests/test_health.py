"""Property and boundary tests for pure health functions."""
import pytest
from hypothesis import given, strategies as st
from rhm_monitors.logic.health import (Debouncer, Status, Thresholds,
                                       battery_status, health_score, sensor_status)


def test_threshold_validation() -> None:
    """Invalid ordering is rejected."""
    with pytest.raises(ValueError):
        Thresholds(2, 1)


def test_missing_sensor_is_stale() -> None:
    """No input is fail-safe."""
    assert sensor_status(10, None, Thresholds()) == Status.STALE
    assert sensor_status(10, 7, Thresholds()) == Status.STALE
    assert sensor_status(10, 9.7, Thresholds()) == Status.OK
    assert sensor_status(10, 9, Thresholds()) == Status.WARN


def test_battery_boundaries() -> None:
    """Threshold comparisons are strict."""
    assert battery_status(9.99) == Status.ERROR
    assert battery_status(10) == Status.WARN
    assert battery_status(25) == Status.OK
    assert battery_status(float('nan')) == Status.STALE


@given(st.lists(st.sampled_from(list(Status)), min_size=1, max_size=40))
def test_score_monotonic(statuses: list[Status]) -> None:
    """Replacing a status by OK cannot reduce score."""
    old = health_score(statuses)
    for index in range(len(statuses)):
        changed = list(statuses)
        changed[index] = Status.OK
        assert health_score(changed) >= old


@given(st.integers(min_value=1, max_value=20))
def test_debounce(required: int) -> None:
    """Exactly N consistent observations trigger a change."""
    debounce = Debouncer(required)
    for _ in range(required - 1):
        assert debounce.update(Status.OK) == Status.STALE
    assert debounce.update(Status.OK) == Status.OK
    assert debounce.update(Status.STALE) == Status.STALE
