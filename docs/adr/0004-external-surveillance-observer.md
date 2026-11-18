# ADR 0004 — External surveillance adapter and read-only browser dashboard

**Status:** Adopted in source, runtime verification pending.

## Context

The platform needs to observe an existing seaport surveillance robot without
copying confidential code, changing robot control, or recreating the robot.
Existing C++ aggregator accepts `diagnostic_msgs/DiagnosticArray`.

## Decision

Create a separate ROS 2 lifecycle adapter that maps operator-configured topic
names and message types to DiagnosticArray; reuse the C++ aggregator. Feed the
FastAPI dashboard through a separate rclpy-only observer with an isolated ROS
context and thread-safe Pydantic snapshot store. Browser state comes only from
observed data. No dashboard-to-robot control endpoints.

## Alternatives rejected

- Copy the surveillance workspace into this repository: violates separation and
  leaks potential client intellectual property.
- Tie the health system to a Gazebo-only sample robot: reduces reuse.
- Directly connect browser to DDS via rosbridge: expands network attack surface
  and requires exposing more of the robot graph.

## Limitations

Telemetry reception is not sensor content validation; simple Nav2 node presence
is not lifecycle/functional health. The aggregator's score is a preliminary
arithmetic severity score, not an operational safety certification. Fault
manager and physical robot validation remain out of scope for this batch.
