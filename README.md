# Failure-Aware Robot Health & Diagnostics Platform

**ROS 2 Jazzy · Ubuntu 24.04 · Python · C++17 · Gazebo Harmonic · FastAPI**

A development-stage platform for observing ROS 2 robot health, detecting stale sensor streams, aggregating subsystem statuses, and presenting received telemetry in a local web dashboard.

> **Status: development / simulation-only.** Native ROS 2 lifecycle nodes and `/robot_health` publishing have been observed in Ubuntu testing. The dashboard has been observed loading locally. This is **not** a production safety system, not hardware validated, and not a demonstrated two-robot failure-recovery solution.

[**Dashboard guide**](docs/dashboard.md) · [**Dashboard source**](src/rhm_dashboard/) · [**Architecture**](docs/architecture.md) · [**Native development**](docs/native_development.md) · [**Validation matrix**](docs/validation_matrix.md) · [**GitHub profile**](https://github.com/mayureshcode)

## At a glance

| Implemented foundation | Still in development |
|:--|:--|
| ROS 2 interface messages, services and action definitions | Complete failure-manager Detect → Search → Recommend → Revalidate |
| Python lifecycle sensor freshness monitor | Full battery, thermal, stall, EKF, Nav2 and arm monitor suite |
| C++ lifecycle aggregation and `/robot_health` topic | Production health-scoring/analytics and validated fault handling |
| Mobile robot Xacro, Gazebo warehouse, bridge/EKF integration source | Reproducibly demonstrated end-to-end navigation and faults |
| Local FastAPI / WebSocket monitoring dashboard | Public dashboard hosting and fully verified fault timeline |
| Tests and native Ubuntu verification scripts | ABB IRB120 / MoveIt 2 and real-hardware validation |

## Architecture

```text
Mobile robot ROS topics / diagnostics
              │
       Lifecycle monitors
              │  diagnostic_msgs/DiagnosticArray
              ▼
       C++ health aggregator
              │ /robot_health
              ▼
         FastAPI bridge
              │ WebSocket
              ▼
      Browser health dashboard

Future: fault manager + revalidation + ABB IRB120 monitors
```

## Dashboard

The dashboard is a **local read-only control-room view** with a mobile-robot status card, placeholders for an industrial manipulator, time-series history, subsystem status table and event timeline. It displays missing data as unknown or stale, **not as fabricated healthy sensor readings**.

**[Explore the dashboard and launch steps →](docs/dashboard.md)**

## Native Ubuntu quickstart

Required: Ubuntu 24.04, ROS 2 Jazzy and the dependencies documented in [native development](docs/native_development.md).

```bash
bash scripts/doctor.sh
bash scripts/setup_native.sh      # first-time setup
bash scripts/native_verify.sh     # build, unit tests, lint and smoke checks
```

Launch the standalone diagnostics pipeline:

```bash
bash scripts/run_native.sh
```

Start the local dashboard in a separate terminal:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=202
ros2 run rhm_dashboard dashboard
```

Then open **http://127.0.0.1:8765**. This is **localhost only**, not a hosted GitHub Pages dashboard. Without active sensor topics, STALE status is expected.

Optional mobile Gazebo development launch:

```bash
RHM_SIM_GUI=1 bash scripts/run_native.sh --sim
```

Its full sensor + EKF + diagnostics integration must be verified on the target Ubuntu installation. `Ctrl+C` stops the launch.

## Testing and evidence

```bash
bash scripts/native_verify.sh
bash scripts/verify_surveillance.sh  # optional experimental adapter verification
```

A successful native test is **not** evidence of Docker CI, hardware functionality or a tested arm cell. Consult [validation matrix](docs/validation_matrix.md) for phase-by-phase scope. The current GitHub Actions state should be checked on the [Actions page](https://github.com/mayureshcode/robot-health-diagnostics-platform/actions); no green CI claim is made here.

## Safety, provenance and boundaries

This is an independent portfolio project; the experimental read-only external surveillance observer is **not required** for the standalone demonstration. It does not command a robot, and its example topic mappings are not verified universal integrations. Before reusing any adapter against another project, check permissions and verify all topic names.

No physical robot actuation, MoveIt collision-checked recovery or RobotStudio execution is asserted.

## Documentation

[Architecture](docs/architecture.md) · [Parameters](docs/parameters.md) · [QoS](docs/qos.md) · [Runbook](docs/runbook.md) · [Mobile simulation](docs/phase2_mobile_sim.md) · [Dashboard](docs/dashboard.md) · [Validation matrix](docs/validation_matrix.md)

## Roadmap

1. Deterministic standalone telemetry and sensor-fault scenarios.
2. Verified Gazebo-to-dashboard mobile robot demonstration.
3. Measured detection/recovery latency and recorded demo evidence.
4. Nav2/EKF diagnostics, failure-aware recommendations and path revalidation.
5. ABB IRB120 + MoveIt 2 simulation and manipulator diagnostics.
6. CI stabilization, security review, portfolio video and release.

MIT license. Contributions and security reports: [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md).
