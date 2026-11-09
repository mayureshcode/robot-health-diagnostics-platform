# Failure-Aware Robot Health & Diagnostics Platform

> **Native Ubuntu 24.04 + ROS 2 Jazzy development baseline — UNVERIFIED REVISION.**
> Not yet production-ready; no hardware safety or complete dual-asset simulation claim.

## Platform

Native Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (planned Phase 2), Python 3.12,
C++17, Nav2 and MoveIt 2 (planned integration). The current source implements
ROS interfaces, a single lifecycle **sensor freshness** monitor, a **partial**
C++ lifecycle aggregator, and a native launch package. The project does **not**
yet integrate a mobile robot, ABB IRB120, navigation, arm planning, or a dashboard.

## Quickstart — native Linux (no Docker)

```bash
cd robot-health-diagnostics-platform
bash scripts/doctor.sh
bash scripts/setup_native.sh     # first time only; installs apt tooling
bash scripts/native_verify.sh    # strict: build + tests + lint + ROS smoke
```

After a verified build, to see data without Gazebo:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch rhm_bringup native_health.launch.py
```

In another terminal, source both setup files, then run
`bash scripts/activate_native.sh` and `ros2 topic echo /robot_health --once`.
Missing sensor streams must show **STALE**. No movement or real hardware
commands are issued. See [native guide](docs/native_development.md).

## Branches and zip-vs-git

The source ZIP does not include `.git`. If you want the **original Batch A
history and the redesigned native branch**, clone the companion Git bundle:

```bash
git clone --branch feat/native-ubuntu-redesign /path/to/rhm-native-ubuntu.bundle rhm-native
cd rhm-native
```

Do not initialize an empty Git repository merely to substitute for a missing
history. This package has no published remote or verified CI run.

## Verification and release rules

`bash scripts/native_verify.sh` writes a step-by-step summary and logs in
`artifacts/` and exits at the first failure. A native pass **does not** imply
Docker, GitHub CI, simulated mobile/arm functionality or hardware verification.
Release gates are described in [validation matrix](docs/validation_matrix.md).

Docker remains optional for local development; CI can run it separately via
`bash scripts/docker_verify.sh`. This is a **development implementation** and
has not been validated in the ROS runtime after these edits.

## Security and intellectual-property boundaries

No site-specific worlds, surveillance project code, credentials, or personal
assets are included. Fault injection is not enabled and no implementation
commands physical robots. The arm cell and RAPID module are **not implemented**.

## Documents

- [Architecture](docs/architecture.md)
- [Native Ubuntu development](docs/native_development.md)
- [QoS](docs/qos.md)
- [Parameters](docs/parameters.md)
- [Runbook](docs/runbook.md)
- [Validation matrix](docs/validation_matrix.md)
- [ADR 0002](docs/adr/0002-native-ubuntu-first.md)
