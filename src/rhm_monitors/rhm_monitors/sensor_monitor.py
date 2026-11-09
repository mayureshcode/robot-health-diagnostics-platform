"""Lifecycle sensor freshness monitor, using ROS clock exclusively."""
from __future__ import annotations

from threading import RLock

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rcl_interfaces.msg import FloatingPointRange, ParameterDescriptor, SetParametersResult
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry

from rhm_monitors.logic.health import Thresholds, sensor_status


class SensorMonitor(LifecycleNode):
    """Monitor three ROS sensor topics with a lifecycle-controlled timer."""

    def __init__(self) -> None:
        super().__init__('rhm_sensor_monitor')
        self._lock = RLock()
        self._last: dict[str, float | None] = {'scan': None, 'imu': None, 'odom': None}
        self._subscriptions: list[object] = []
        self._timer = None
        self._publisher = None
        self.declare_parameter('warn_age', 0.5, ParameterDescriptor(
            description='Warn when sample age exceeds seconds',
            floating_point_range=[FloatingPointRange(from_value=0.0, to_value=60.0, step=0.0)]))
        self.declare_parameter('error_age', 2.0, ParameterDescriptor(
            description='Mark stale when sample age exceeds seconds',
            floating_point_range=[FloatingPointRange(from_value=0.01, to_value=120.0, step=0.0)]))
        self.add_on_set_parameters_callback(self._validate)

    def _validate(self, parameters: list[Parameter]) -> SetParametersResult:
        values = {'warn_age': float(self.get_parameter('warn_age').value),
                  'error_age': float(self.get_parameter('error_age').value)}
        for parameter in parameters:
            if parameter.name in values:
                values[parameter.name] = float(parameter.value)
        try:
            Thresholds(**values)
        except (ValueError, TypeError) as exc:
            return SetParametersResult(successful=False, reason=str(exc))
        return SetParametersResult(successful=True)

    def on_configure(self, state: object) -> TransitionCallbackReturn:
        try:
            self._limits = Thresholds(float(self.get_parameter('warn_age').value),
                                      float(self.get_parameter('error_age').value))
            self._publisher = self.create_publisher(
                DiagnosticArray, '/diagnostics', QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
            for key, message_type, topic in (
                ('scan', LaserScan, '/scan'), ('imu', Imu, '/imu'), ('odom', Odometry, '/odom')
            ):
                self._subscriptions.append(self.create_subscription(
                    message_type, topic, lambda msg, k=key: self._record(k), qos_profile_sensor_data))
            return TransitionCallbackReturn.SUCCESS
        except Exception as exc:
            self.get_logger().error(f'configure failed: {exc}')
            return TransitionCallbackReturn.FAILURE

    def _record(self, key: str) -> None:
        with self._lock:
            self._last[key] = self.get_clock().now().nanoseconds * 1e-9

    def on_activate(self, state: object) -> TransitionCallbackReturn:
        if self._publisher is None:
            return TransitionCallbackReturn.FAILURE
        self._publisher.on_activate()
        self._timer = self.create_timer(0.2, self._publish)
        return TransitionCallbackReturn.SUCCESS

    def _publish(self) -> None:
        try:
            now = self.get_clock().now().nanoseconds * 1e-9
            with self._lock:
                snapshots = dict(self._last)
            array = DiagnosticArray()
            array.header.stamp = self.get_clock().now().to_msg()
            for key, last in snapshots.items():
                status = sensor_status(now, last, self._limits)
                item = DiagnosticStatus()
                item.name = f'mobile/sensor/{key}'
                item.hardware_id = 'mobile'
                item.level = (DiagnosticStatus.STALE if status.value == 3 else status.value)
                item.message = status.name
                item.values = [KeyValue(key='age_seconds', value='unknown' if last is None else str(max(0.0, now-last)))]
                array.status.append(item)
            if self._publisher is not None:
                self._publisher.publish(array)
        except Exception as exc:
            self.get_logger().error(f'diagnostic callback error: {exc}', throttle_duration_sec=5.0)

    def on_deactivate(self, state: object) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        if self._publisher is not None:
            self._publisher.on_deactivate()
        return TransitionCallbackReturn.SUCCESS

    def on_cleanup(self, state: object) -> TransitionCallbackReturn:
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        for subscription in self._subscriptions:
            self.destroy_subscription(subscription)
        self._subscriptions.clear()
        if self._publisher is not None:
            self.destroy_publisher(self._publisher)
            self._publisher = None
        with self._lock:
            self._last = dict.fromkeys(self._last)
        return TransitionCallbackReturn.SUCCESS


def main() -> None:
    """Spin the lifecycle monitor; transitions are operator-managed."""
    rclpy.init()
    node = SensorMonitor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
