#!/usr/bin/env python3
"""ROS integration smoke: require a published lidar diagnostic and health output.

This is a read-only observer test; optional --require-lidar-ok asserts live sensor
arrival. Its timeout uses monotonic wall time, whereas monitor freshness uses ROS
clock. Exit 1 if the graph never delivers the expected diagnostics.
"""

from __future__ import annotations

import argparse
import json
from time import monotonic
from typing import Any


def main() -> int:
    """Verify live ROS publications without commanding the robot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--require-lidar-ok", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.timeout <= 180:
        parser.error("--timeout must be within 1..180 seconds")

    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from rhm_interfaces.msg import HealthStatus

    rclpy.init()
    node = rclpy.create_node("rhm_surveillance_live_check")
    reports: list[Any] = []
    subscription = node.create_subscription(
        HealthStatus, "/robot_health", lambda msg: reports.append(msg),
        QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE),
    )
    try:
        deadline = monotonic() + args.timeout
        while monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.3)
            if reports:
                recent = reports[-1]
                subsystems = {sub.subsystem: int(sub.status) for sub in recent.subsystems}
                if "mobile/sensor/lidar" not in subsystems:
                    continue
                if args.require_lidar_ok and subsystems["mobile/sensor/lidar"] != 0:
                    continue
                print(json.dumps({
                    "received_health": True,
                    "asset": recent.asset_id,
                    "lidar_status": subsystems["mobile/sensor/lidar"],
                    "subsystems": subsystems,
                    "ros_stamp_sec": int(recent.header.stamp.sec),
                }, indent=2))
                return 0
        print(json.dumps({
            "received_health": bool(reports),
            "error": "no lidar diagnostic received in a health message satisfying constraints",
            "require_lidar_ok": bool(args.require_lidar_ok),
            "last_seen_subsystems": ([item.subsystem for item in reports[-1].subsystems]
                                     if reports else []),
        }, indent=2))
        return 1
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
