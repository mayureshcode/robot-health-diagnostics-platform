"""Pure data-model tests: never manufacture absent telemetry."""

from rhm_dashboard.schema import HealthStore


def test_unknown_until_actual_ros_message() -> None:
    """Empty state must remain unknown, not display a fictitious health score."""
    store = HealthStore()
    assert store.snapshot().health_score is None
    assert store.snapshot().sensors == []


def test_real_health_and_rate_metadata() -> None:
    """Diagnostic metadata attaches to actual observed health messages."""
    store = HealthStore()
    store.update_diagnostics([("mobile/sensor/lidar", {"topic": "/points", "rate_hz": "10.5", "samples_received": "42", "age_seconds": "0.1"})])
    store.update_health(ros_time=15, asset_id="mobile", status=0, score=100, subsystems=[
        {"name": "mobile/sensor/lidar", "status": 0, "score": 100, "summary": "diagnostic observed"},
    ])
    report = store.snapshot()
    assert report.health_score == 100
    assert report.sensors[0].rate_hz == 10.5
    assert report.sensors[0].sample_count == 42
    store.update_health(ros_time=16, asset_id="mobile", status=3, score=0, subsystems=[
        {"name": "mobile/sensor/lidar", "status": 3, "score": 0, "summary": "diagnostic observed"},
    ])
    assert len(store.snapshot().events) == 1
    assert store.snapshot().events[0].origin == "transition"
    store.mark_disconnected()
    assert not store.snapshot().connected
