# Architecture and interface contract (Phase 1)

```mermaid
flowchart LR
  M[Mobile monitors] --> D[DiagnosticArray]
  A[Arm monitors] --> D
  D --> G[C++ Aggregator]
  G --> H[/robot_health]
  G --> F[/fault_events]
  F --> FM[Python Fault Manager]
  FM --> R[/recommendations]
  FM --> RV[RevalidatePlan action]
  RV --> N[Nav2 / MoveIt planning]
  H --> L[Logs and dashboard]
  F --> L
  R --> L
```

## Interface table

| Kind | Name | Type | Owner | Purpose |
|---|---|---|---|---|
| Topic | `/diagnostics` | `diagnostic_msgs/msg/DiagnosticArray` | monitors | Standard diagnostics; include `asset_id` and `subsystem` key-values |
| Topic | `/robot_health` | `rhm_interfaces/msg/HealthStatus` | aggregator | Per-asset status and scores |
| Topic | `/fault_events` | `rhm_interfaces/msg/FaultEvent` | aggregator | Edge-triggered fault transitions |
| Topic | `/recommendations` | `rhm_interfaces/msg/Recommendation` | fault manager | Ranked candidate mitigations |
| Service | `/health/get_report` | `rhm_interfaces/srv/GetReport` | aggregator | Snapshot report |
| Service | `/health/reset_faults` | `rhm_interfaces/srv/ResetFaults` | aggregator | Clear latches, not physical faults |
| Service | `/fault_injector/inject` | `rhm_interfaces/srv/InjectFault` | injector | Simulation-only fault request |
| Action | `/fault_manager/revalidate_plan` | `rhm_interfaces/action/RevalidatePlan` | fault manager | Plan-only validation; never executes motion |

## Contract decisions

- `asset_id` is `mobile` or `arm` by default, but is configurable.
- Status precedence: `ERROR > STALE > WARN > OK` for aggregation; stale is a separate state, not evidence of a healthy subsystem.
- Health scores are bounded to 0–100 and must not be interpreted as safety certifications.
- Fault events have stable `event_id` values; consumers deduplicate by ID and transition.
- Timestamps use ROS time; wall-clock logs should also record UTC when implemented.
- Reset clears stored latches only, never overrides active detection or a hardware e-stop.
- InjectFault is simulation-only and must be disabled in hardware configurations.
- Revalidation is dry-run planning, not permission to command the robot. Approval is mandatory before executing recommended motion.
- Message types are defined here; runtime publishers/subscribers are **not implemented** in Phase 1.

## TF contracts planned for Phase 2

Mobile: `map -> odom -> base_link -> {laser_link, imu_link}` (and wheel frames via URDF). `map -> odom` from localization; `odom -> base_link` from EKF. Avoid duplicate TF broadcasters.

Arm: `world -> arm_base_link -> ... -> tool0` via fixed world mount and `robot_state_publisher` driven by joint states. Exact link names depend on the verified IRB120 description.

## Deferred implementation

Monitors, simulation, aggregator, fault manager, dashboard, tests and CI are not yet implemented. No ROS runtime build has been performed in this environment.
