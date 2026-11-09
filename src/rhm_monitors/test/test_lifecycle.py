"""ROS-local lifecycle regression tests; do not require running Gazebo."""

import rclpy
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.parameter import Parameter

from rhm_monitors.sensor_monitor import SensorMonitor


def test_configure_activate_deactivate_cleanup() -> None:
    """Managed publishers and subscriptions may be safely cleaned and rebuilt."""
    rclpy.init()
    node = None
    try:
        node = SensorMonitor()
        assert node.trigger_configure() == TransitionCallbackReturn.SUCCESS
        assert len(node._subscriptions) == 3
        assert node.trigger_activate() == TransitionCallbackReturn.SUCCESS
        assert node._timer is not None
        assert node.trigger_deactivate() == TransitionCallbackReturn.SUCCESS
        assert node._timer is None
        assert node.trigger_cleanup() == TransitionCallbackReturn.SUCCESS
        assert len(node._subscriptions) == 0
        assert node._publisher is None
        assert node.trigger_configure() == TransitionCallbackReturn.SUCCESS
        assert node.trigger_activate() == TransitionCallbackReturn.SUCCESS
        assert node.trigger_deactivate() == TransitionCallbackReturn.SUCCESS
        assert node.trigger_cleanup() == TransitionCallbackReturn.SUCCESS
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def test_immutable_limits_and_invalid_values() -> None:
    """Startup-only parameters cannot be mutated while the node is running."""
    rclpy.init()
    node = None
    try:
        node = SensorMonitor()
        result = node.set_parameters([Parameter('warn_age', Parameter.Type.DOUBLE, 5.0)])
        assert not result[0].successful
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
