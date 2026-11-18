"""Isolated rclpy subscriber feeding a thread-safe in-process dashboard store."""

from __future__ import annotations

import logging
from threading import Event, Thread
from typing import Any

from rhm_dashboard.schema import HealthStore


LOG = logging.getLogger(__name__)


class RosFeed:
    """Separate ROS context and executor; observes only diagnostic topics."""

    def __init__(self, store: HealthStore) -> None:
        self.store = store
        self._stop = Event()
        self._thread: Thread | None = None
        self._executor: Any = None

    def start(self) -> None:
        """Start read-only ROS subscriptions in an isolated worker thread."""
        self._stop.clear()
        self._thread = Thread(target=self._run, name="rhm-dashboard-ros", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Request ROS shutdown and wait for bounded thread cleanup."""
        self._stop.set()
        if self._executor is not None:
            self._executor.wake()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                LOG.error("ROS worker did not stop within 5 seconds")
        self.store.mark_disconnected()

    def _run(self) -> None:
        import rclpy
        from diagnostic_msgs.msg import DiagnosticArray
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, ReliabilityPolicy
        from rhm_interfaces.msg import FaultEvent, HealthStatus

        context = Context()
        node = None
        executor = None
        try:
            rclpy.init(context=context)
            node = Node("rhm_dashboard_observer", context=context)
            executor = SingleThreadedExecutor(context=context)
            self._executor = executor
            qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
            node.create_subscription(HealthStatus, "/robot_health", self._on_health, qos)
            node.create_subscription(FaultEvent, "/fault_events", self._on_fault, qos)
            node.create_subscription(DiagnosticArray, "/rhm/surveillance/diagnostics", self._on_diagnostics, qos)
            while not self._stop.is_set() and context.ok():
                executor.spin_once(timeout_sec=0.25)
        except Exception:
            LOG.exception("ROS dashboard observer failed")
        finally:
            self.store.mark_disconnected()
            self._executor = None
            if executor is not None:
                executor.shutdown(timeout_sec=2.0)
            if node is not None:
                node.destroy_node()
            if context.ok():
                rclpy.shutdown(context=context)

    def _on_health(self, msg: Any) -> None:
        """Handle health snapshot messages from existing aggregator."""
        try:
            self.store.update_health(
                ros_time=float(msg.header.stamp.sec) + msg.header.stamp.nanosec * 1e-9,
                asset_id=str(msg.asset_id), status=int(msg.status),
                score=float(msg.health_score),
                subsystems=[{
                    "name": item.subsystem, "status": int(item.status),
                    "score": float(item.score), "summary": item.summary,
                } for item in msg.subsystems],
            )
        except Exception:
            LOG.exception("invalid health message")

    def _on_diagnostics(self, msg: Any) -> None:
        """Read optional metadata such as ROS topic and actual rate."""
        try:
            self.store.update_diagnostics([
                (str(item.name), {kv.key: kv.value for kv in item.values})
                for item in msg.status
            ])
        except Exception:
            LOG.exception("invalid diagnostics metadata")

    def _on_fault(self, msg: Any) -> None:
        """Display only events emitted by an actual fault producer."""
        try:
            self.store.add_fault(
                event_id=str(msg.event_id), subsystem=str(msg.subsystem),
                severity=int(msg.severity), description=str(msg.description),
            )
        except Exception:
            LOG.exception("invalid fault event")
