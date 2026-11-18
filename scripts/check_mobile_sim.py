#!/usr/bin/env python3
"""Fail-closed, end-to-end mobile Gazebo health smoke test (no motion).

Wall monotonic time is used only for the test's timeout; robot monitoring
continues to use simulated ROS time.
"""

from __future__ import annotations

import argparse
import sys
import time

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from rhm_interfaces.msg import HealthStatus
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, LaserScan
from tf2_ros import Buffer, TransformListener


class MobileSimProbe(Node):
    """Observe sensor streams, fused TF and health without issuing any motion."""

    def __init__(self) -> None:
        super().__init__('rhm_mobile_sim_probe')
        self.counts: dict[str, int] = {
            '/clock': 0, '/scan': 0, '/imu': 0, '/wheel/odom': 0, '/odom': 0,
        }
        self.saw_healthy_health = False
        self.saw_healthy_sensors = False
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self._keepers = [
            self.create_subscription(
                msg_type, name, lambda _msg, topic=name: self._mark(topic),
                qos_profile_sensor_data,
            )
            for name, msg_type in (
                ('/clock', Clock), ('/scan', LaserScan), ('/imu', Imu),
                ('/wheel/odom', Odometry), ('/odom', Odometry),
            )
        ]
        self._keepers.append(self.create_subscription(
            HealthStatus, '/robot_health', self._on_health, 10,
        ))
        self._keepers.append(self.create_subscription(
            DiagnosticArray, '/diagnostics', self._on_diagnostics, 10,
        ))

    def _mark(self, topic: str) -> None:
        self.counts[topic] += 1

    def _on_health(self, message: HealthStatus) -> None:
        if message.asset_id == 'mobile' and message.status == 0 and message.health_score > 0:
            self.saw_healthy_health = True

    def _on_diagnostics(self, message: DiagnosticArray) -> None:
        expected = {'mobile/sensor/scan', 'mobile/sensor/imu', 'mobile/sensor/odom'}
        levels = {entry.name: entry.level for entry in message.status}
        if expected <= levels.keys() and all(levels[name] == bytes([0]) for name in expected):
            self.saw_healthy_sensors = True

    def tf_ready(self) -> bool:
        """Check unique EKF parent and robot-state-publisher static child paths."""
        stamp = Time()
        return all(self.tf_buffer.can_transform(parent, child, stamp)
                   for parent, child in (
                       ('odom', 'base_link'),
                       ('base_link', 'imu_link'),
                       ('base_link', 'lidar_link'),
                       ('base_link', 'caster_link'),
                       ('base_link', 'left_wheel_link'),
                       ('base_link', 'right_wheel_link'),
                   ))


def main() -> int:
    """Exit nonzero unless clocks, simulated sensor streams, TF and health work."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout', type=float, default=90.0)
    args = parser.parse_args()
    if args.timeout < 1.0 or args.timeout > 600.0:
        parser.error('--timeout must be between 1 and 600 seconds')
    rclpy.init()
    node = MobileSimProbe()
    try:
        start = time.monotonic()
        while time.monotonic() - start < args.timeout:
            rclpy.spin_once(node, timeout_sec=0.2)
            inputs_ready = all(count >= 2 for count in node.counts.values())
            if inputs_ready and node.saw_healthy_health and node.saw_healthy_sensors and node.tf_ready():
                print('PASS sim_smoke | sensors, EKF TF, and healthy diagnostics observed | exit=0')
                print(f'Observed sample counts: {node.counts}')
                return 0
        print(f'FAIL sim_smoke | timeout={args.timeout}s | counts={node.counts} '
              f'healthy_health={node.saw_healthy_health} '
              f'healthy_sensors={node.saw_healthy_sensors} '
              f'tf_ready={node.tf_ready()}', file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
