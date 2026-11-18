"""ROS 2 Jazzy lifecycle sensor freshness monitor (no hardware commands)."""
from __future__ import annotations

from threading import RLock
from typing import Any

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan

from rhm_monitors.logic.health import Status, Thresholds, sensor_status


def diagnostic_level_byte(status: Status) -> bytes:
    """Encode Jazzy DiagnosticStatus.level (IDL byte), not Python int."""
    return bytes((int(status),))


class SensorMonitor(LifecycleNode):
    """Lifecycle publisher for /scan, /imu and /odom timestamp freshness.

    Thresholds are startup parameters and intentionally read-only thereafter.
    Input callbacks record arrival time in ROS time, not wall time.
    """

    def __init__(self) -> None:
        super().__init__('rhm_sensor_monitor')
        self._lock = RLock()
        self._last: dict[str, float | None] = {'scan': None, 'imu': None, 'odom': None}
        self._sensor_subscriptions: list[Any] = []
        self._timer: Any = None
        self._publisher: Any = None
        self.declare_parameter(
            'warn_age', 0.5,
            ParameterDescriptor(
                description='WARN when age (ROS seconds) exceeds this value. Startup only.',
                read_only=True,
                floating_point_range=[FloatingPointRange(from_value=0.0, to_value=60.0)],
            ),
        )
        self.declare_parameter(
            'error_age', 2.0,
            ParameterDescriptor(
                description='STALE when age (ROS seconds) exceeds this value. Startup only.',
                read_only=True,
                floating_point_range=[FloatingPointRange(from_value=0.01, to_value=120.0)],
            ),
        )
        self.add_on_set_parameters_callback(self._validate)
        # Reject invalid startup overrides before any ROS publishers are created.
        self._limits = Thresholds(
            float(self.get_parameter('warn_age').value),
            float(self.get_parameter('error_age').value),
        )

    def _validate(self, parameters: list[Parameter]) -> SetParametersResult:
        """Reject invalid combinations even if parameter mutability is later enabled."""
        values = {'warn_age': self._limits.warn_age, 'error_age': self._limits.error_age}
        try:
            for parameter in parameters:
                if parameter.name in values:
                    values[parameter.name] = float(parameter.value)
            Thresholds(**values)
        except (ValueError, TypeError, OverflowError) as exc:
            return SetParametersResult(successful=False, reason=str(exc))
        return SetParametersResult(successful=True)

    def on_configure(self, state: object) -> TransitionCallbackReturn:
        """Construct managed ROS resources, or clean up after a partial failure."""
        try:
            self._publisher = self.create_lifecycle_publisher(
                DiagnosticArray, '/diagnostics',
                QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE),
            )
            for key, message_type, topic in (
                ('scan', LaserScan, '/scan'),
                ('imu', Imu, '/imu'),
                ('odom', Odometry, '/odom'),
            ):
                self._sensor_subscriptions.append(self.create_subscription(
                    message_type, topic,
                    lambda msg, name=key: self._record(name),
                    qos_profile_sensor_data,
                ))
            return TransitionCallbackReturn.SUCCESS
        except Exception as exc:
            self.get_logger().error(f'configure failed: {exc}')
            self._release_resources()
            return TransitionCallbackReturn.FAILURE

    def _record(self, key: str) -> None:
        """Store the sensor reception time from the node's ROS clock."""
        try:
            stamp = self.get_clock().now().nanoseconds * 1e-9
            with self._lock:
                self._last[key] = stamp
        except Exception as exc:
            self.get_logger().error(f'record error: {exc}', throttle_duration_sec=5.0)

    def on_activate(self, state: object) -> TransitionCallbackReturn:
        """Start periodic publishing only while active."""
        if self._publisher is None:
            return TransitionCallbackReturn.FAILURE
        result = super().on_activate(state)
        if result != TransitionCallbackReturn.SUCCESS:
            return result
        try:
            self._timer = self.create_timer(0.2, self._publish)
        except Exception as exc:
            self.get_logger().error(f'activation failed: {exc}')
            super().on_deactivate(state)
            return TransitionCallbackReturn.FAILURE
        return TransitionCallbackReturn.SUCCESS

    def _publish(self) -> None:
        """Emit STALE rather than raising when inputs are missing or invalid."""
        try:
            clock = self.get_clock().now()
            now = clock.nanoseconds * 1e-9
            with self._lock:
                snapshot = dict(self._last)
            output = DiagnosticArray()
            output.header.stamp = clock.to_msg()
            for key, last in snapshot.items():
                status = sensor_status(now, last, self._limits)
                entry = DiagnosticStatus()
                entry.name = f'mobile/sensor/{key}'
                entry.hardware_id = 'mobile'
                entry.level = diagnostic_level_byte(status)
                entry.message = status.name
                entry.values = [KeyValue(
                    key='age_seconds',
                    value='unknown' if last is None else str(max(0.0, now - last)),
                )]
                output.status.append(entry)
            if self._publisher is not None:
                self._publisher.publish(output)
        except Exception as exc:
            self.get_logger().error(f'diagnostic publish error: {exc}', throttle_duration_sec=5.0)

    def on_deactivate(self, state: object) -> TransitionCallbackReturn:
        """Stop the ROS timer and deactivate all managed lifecycle entities."""
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        return super().on_deactivate(state)

    def _release_resources(self) -> None:
        """Release subscriptions, publisher and timer idempotently."""
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        for subscription in self._sensor_subscriptions:
            self.destroy_subscription(subscription)
        self._sensor_subscriptions.clear()
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        with self._lock:
            self._last = dict.fromkeys(self._last)

    def on_cleanup(self, state: object) -> TransitionCallbackReturn:
        """Release all lifecycle-managed resources after deactivation."""
        self._release_resources()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: object) -> TransitionCallbackReturn:
        """Release all entities during graceful lifecycle shutdown."""
        self._release_resources()
        return TransitionCallbackReturn.SUCCESS

    def on_error(self, state: object) -> TransitionCallbackReturn:
        """Fail closed and clean up after a transition error."""
        self._release_resources()
        return TransitionCallbackReturn.SUCCESS


def main() -> None:
    """Spin the monitor; lifecycle transitions are initiated by the operator."""
    rclpy.init()
    node = SensorMonitor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
