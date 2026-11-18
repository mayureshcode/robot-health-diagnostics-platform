"""Jazzy lifecycle tests; exercise the adapter without running the robot."""

from pathlib import Path

import rclpy
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.parameter import Parameter

from rhm_surveillance_adapter.node import SurveillanceMonitor


def test_observer_lifecycle_and_reconfiguration() -> None:
    """Configure/activate/deactivate/cleanup twice without leaking ROS entities."""
    profile = Path(__file__).resolve().parents[1] / "config" / "surveillance.yaml"
    assert profile.is_file()
    rclpy.init()
    node = None
    try:
        node = SurveillanceMonitor(parameter_overrides=[
            Parameter("profile_path", value=str(profile)),
        ])
        for _ in range(2):
            assert node.trigger_configure() == TransitionCallbackReturn.SUCCESS
            assert len(node._monitored_subscriptions) == 3
            assert node._publisher is not None
            assert not node._publisher.is_activated
            assert node.trigger_activate() == TransitionCallbackReturn.SUCCESS
            assert node._publisher.is_activated
            assert node._timer is not None
            # The read-only adapter should safely report STALE before input arrives.
            node._publish()
            assert node.trigger_deactivate() == TransitionCallbackReturn.SUCCESS
            assert node._timer is None
            assert not node._publisher.is_activated
            assert node.trigger_cleanup() == TransitionCallbackReturn.SUCCESS
            assert node._publisher is None
            assert node._monitored_subscriptions == []
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
