"""Read-only lifecycle adapter: external ROS topics -> isolated diagnostics.

No motion commands, action clients, service calls or fault injection are created.
All sensor rates and freshness use the ROS clock for sim-time compatibility.
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import Image, Imu, JointState, LaserScan, NavSatFix, PointCloud2

from rhm_surveillance_adapter.logic import StreamState, classify, load_profile


TYPES: dict[str, type[Any]] = {
    "PointCloud2": PointCloud2,
    "LaserScan": LaserScan,
    "Imu": Imu,
    "Odometry": Odometry,
    "Image": Image,
    "NavSatFix": NavSatFix,
    "JointState": JointState,
}


class SurveillanceMonitor(LifecycleNode):
    """Subscribe to configured topics and publish fail-safe health indicators."""

    def __init__(self, *, parameter_overrides: list[Parameter] | None = None) -> None:
        """Initialize a read-only lifecycle observer with optional ROS parameter overrides."""
        super().__init__("rhm_surveillance_monitor", parameter_overrides=parameter_overrides)
        self._guard = RLock()
        self._monitored_subscriptions: list[Any] = []
        self._timer: Any = None
        self._publisher: Any = None
        self._specs: tuple[Any, ...] = ()
        self._nodes: tuple[str, ...] = ()
        self._samples: dict[str, StreamState] = {}
        self.declare_parameter("profile_path", "", ParameterDescriptor(
            description="Absolute YAML surveillance profile; restart/reconfigure to change",
            read_only=True,
        ))

    def on_configure(self, state: Any) -> TransitionCallbackReturn:
        """Load profile, create read-only subscriptions and lifecycle publisher."""
        try:
            profile_path = str(self.get_parameter("profile_path").value)
            if not profile_path or not Path(profile_path).is_file():
                raise ValueError(f"profile_path not found: {profile_path!r}")
            _, self._specs, self._nodes = load_profile(profile_path)
            with self._guard:
                self._samples = {spec.name: StreamState() for spec in self._specs}
            self._publisher = self.create_lifecycle_publisher(
                DiagnosticArray, "/rhm/surveillance/diagnostics", QoSProfile(
                    depth=10, reliability=ReliabilityPolicy.RELIABLE,
                ),
            )
            for spec in self._specs:
                subscription = self.create_subscription(
                    TYPES[spec.message_type], spec.topic,
                    lambda msg, name=spec.name: self._record(name),
                    qos_profile_sensor_data,
                )
                self._monitored_subscriptions.append(subscription)
            self.get_logger().info(f"surveillance profile: {len(self._specs)} sensor streams; no robot control")
            return TransitionCallbackReturn.SUCCESS
        except Exception as exc:
            self.get_logger().error(f"configure failed: {exc}")
            self._release()
            return TransitionCallbackReturn.FAILURE

    def _record(self, name: str) -> None:
        """Record ROS-clock reception timestamp for an incoming sensor sample."""
        try:
            now = self.get_clock().now().nanoseconds / 1e9
            with self._guard:
                self._samples[name].observe(now)
        except Exception as exc:
            self.get_logger().error(f"topic callback error: {exc}", throttle_duration_sec=5.0)

    def on_activate(self, state: Any) -> TransitionCallbackReturn:
        """Activate managed publishers and start the periodic health timer."""
        if self._publisher is None:
            self.get_logger().error("activation refused: configure did not create publisher")
            return TransitionCallbackReturn.FAILURE
        # Jazzy managed publishers require on_activate(state). The lifecycle
        # parent's callback invokes this for every managed publisher.
        result = super().on_activate(state)
        if result != TransitionCallbackReturn.SUCCESS:
            self.get_logger().error("managed publisher activation failed")
            return result
        try:
            self._timer = self.create_timer(0.5, self._publish)
        except Exception as exc:
            self.get_logger().error(f"activation timer failed: {exc}")
            super().on_deactivate(state)
            return TransitionCallbackReturn.FAILURE
        return TransitionCallbackReturn.SUCCESS

    def _publish(self) -> None:
        """Publish freshness and observed ROS graph presence, including unknown data."""
        try:
            stamp = self.get_clock().now()
            now = stamp.nanoseconds / 1e9
            with self._guard:
                samples = {key: StreamState(**vars(value)) for key, value in self._samples.items()}
            array = DiagnosticArray()
            array.header.stamp = stamp.to_msg()
            for spec in self._specs:
                sample = samples[spec.name]
                status, age = classify(now, sample, spec)
                entry = DiagnosticStatus()
                entry.name = f"mobile/sensor/{spec.name}"
                entry.hardware_id = "surveillance_rover"
                entry.level = bytes([status])
                entry.message = ("OK" if status == 0 else "WARN" if status == 1 else "STALE")
                entry.values = [
                    KeyValue(key="topic", value=spec.topic),
                    KeyValue(key="message_type", value=spec.message_type),
                    KeyValue(key="age_seconds", value="unavailable" if age is None else f"{age:.3f}"),
                    KeyValue(key="rate_hz", value="unavailable" if sample.ewma_hz is None else f"{sample.ewma_hz:.2f}"),
                    KeyValue(key="samples_received", value=str(sample.count)),
                    KeyValue(key="source", value="ROS message reception, simulation/telemetry"),
                ]
                array.status.append(entry)
            present = {f"{namespace.rstrip('/')}/{name}".replace("//", "/")
                       for name, namespace in self.get_node_names_and_namespaces()}
            for node_name in self._nodes:
                entry = DiagnosticStatus()
                entry.name = "mobile/node/" + node_name.lstrip("/")
                entry.hardware_id = "surveillance_rover"
                entry.level = bytes([0 if node_name in present else 3])
                entry.message = "NODE_PRESENT (not lifecycle validated)" if node_name in present else "NODE_NOT_FOUND"
                entry.values = [KeyValue(key="node", value=node_name),
                                KeyValue(key="check", value="ROS graph presence only")]
                array.status.append(entry)
            if self._publisher is not None:
                self._publisher.publish(array)
        except Exception as exc:
            self.get_logger().error(f"publish callback error: {exc}", throttle_duration_sec=5.0)

    def on_deactivate(self, state: Any) -> TransitionCallbackReturn:
        """Stop the timer and deactivate all managed publishers."""
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        return super().on_deactivate(state)

    def on_error(self, state: Any) -> TransitionCallbackReturn:
        """Return to unconfigured without leaking resources after a lifecycle error."""
        self.get_logger().error("lifecycle error; releasing monitoring resources")
        self._release()
        return TransitionCallbackReturn.SUCCESS

    def _release(self) -> None:
        """Release this node's resources without modifying rclpy's internal lists."""
        if self._timer is not None:
            self.destroy_timer(self._timer)
            self._timer = None
        for subscription in self._monitored_subscriptions:
            self.destroy_subscription(subscription)
        self._monitored_subscriptions.clear()
        if self._publisher is not None:
            self.destroy_lifecycle_publisher(self._publisher)
            self._publisher = None
        with self._guard:
            self._samples.clear()

    def on_cleanup(self, state: Any) -> TransitionCallbackReturn:
        """Destroy subscriptions and publisher, allowing clean reconfiguration."""
        self._release()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: Any) -> TransitionCallbackReturn:
        """Stop and dispose all resources during node shutdown."""
        self._release()
        return TransitionCallbackReturn.SUCCESS


def main() -> None:
    """Run the lifecycle adapter until interrupted."""
    rclpy.init()
    node = SurveillanceMonitor()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
