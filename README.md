# Failure-Aware Robot Health & Diagnostics Platform

> **Native Ubuntu 24.04 + ROS 2 Jazzy — Phase 2A mobile simulation source (UNVERIFIED).**
> Not yet production-ready; no hardware safety or complete dual-asset simulation claim.

## Platform

Native Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (Phase 2A source implemented; runtime unverified), Python 3.12,
C++17, Nav2 and MoveIt 2 (planned integration). The current source implements ROS interfaces, a single lifecycle **sensor
freshness** monitor, a **partial** C++ lifecycle aggregator, and a new
**simulation-only mobile robot** Xacro + Gazebo world + ROS bridge + EKF launch.
The simulation has **not been runtime-verified** in ROS here. The project does
not implement an ABB IRB120 simulation, Nav2 actions, arm planning, or dashboard.

## Quickstart — native Linux (no Docker)

```bash
cd robot-health-diagnostics-platform
bash scripts/doctor.sh
bash scripts/setup_native.sh     # first time only; installs apt tooling
bash scripts/native_verify.sh    # strict: build + tests + lint + ROS smoke
```

Start **all currently implemented runtime nodes** (build + launch + lifecycle
activation + sample health output) with one command:

```bash
bash scripts/run_native.sh
```

`Ctrl+C` stops the stack. The launcher uses isolated `ROS_DOMAIN_ID=202` by
default (override with `RHM_DOMAIN_ID=...`) and records runtime logs in
`artifacts/`. Missing sensor streams should show **STALE**. For the new **mobile-only simulation** (new source, runtime gate pending), use:

```bash
bash scripts/run_native.sh --sim            # sim + diagnostics, headless
RHM_SIM_GUI=1 bash scripts/run_native.sh --sim  # optional Gazebo GUI
bash scripts/run_native.sh --verify-sim     # fail-closed integration smoke
```

No autonomous motion is commanded. The ABB arm, Nav2, MoveIt and dashboard are
not implemented or launched. There are no real hardware commands. See
[native guide](docs/native_development.md).

## Phase 2A delivery (current native users)

For your existing `~/robot-health-project/rhm-native` working tree, download
`rhm-phase2-mobile-ubuntu.patch` and apply it:

```bash
cd ~/robot-health-project/rhm-native
git apply --check ~/Downloads/rhm-phase2-mobile-ubuntu.patch
git apply ~/Downloads/rhm-phase2-mobile-ubuntu.patch
bash scripts/run_native.sh --sim
```

The patch assumes the prior lifecycle, pytest-discovery and ShellCheck fixes are
already present. The standalone ZIP is source-only (no `.git` metadata). The
companion Git bundle preserves the branch `feat/phase2-mobile-gazebo` and its
history, and can be cloned to **a separate directory** instead of patching the
existing checkout. No branch has been pushed to GitHub, and CI is not green or
run by virtue of these source changes.

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
- [Phase 2A mobile simulation and validation](docs/phase2_mobile_sim.md)
- [QoS](docs/qos.md)
- [Parameters](docs/parameters.md)
- [Runbook](docs/runbook.md)
- [Validation matrix](docs/validation_matrix.md)
- [ADR 0002](docs/adr/0002-native-ubuntu-first.md)

## Surveillance robot integration — read-only observer (feature branch)

The `feat/surveillance-health-dashboard` branch adds a standalone ROS 2 adapter
and a local FastAPI dashboard. **This branch is not hardware validated.** The
surveillance repository is **not vendored or modified**; the adapter subscribes
only to its ROS topics. It never sends motion commands, stops the robot,
reconfigures Nav2 or makes recovery decisions.

On Ubuntu 24.04 + ROS 2 Jazzy, first start your existing surveillance simulation
in its own terminal (with its normal project-specific launch command). Then
launch the independent health system from this repository:

```bash
cd ~/robot-health-project/rhm-native
bash scripts/run_surveillance.sh
```

Open `http://127.0.0.1:8765` in Firefox. The script builds its ROS packages,
sets the default `ROS_DOMAIN_ID=188`, starts the surveillance diagnostics
adapter and C++ aggregator, activates their lifecycle nodes, and starts the
local dashboard. It does **not** launch the external surveillance simulation.
Press Ctrl+C to stop the monitoring processes only.

Configuration (environment variables, no hardcoded secrets):

| Variable | Default | Description |
|---|---|---|
| `RHM_SURVEILLANCE_DOMAIN_ID` | `188` | Must match target robot ROS_DOMAIN_ID |
| `RHM_USE_SIM_TIME` | `true` | Requires a working `/clock` from the simulation |
| `RHM_PROFILE_PATH` | bundled example | Absolute YAML path mapping external ROS topics |
| `RHM_DASHBOARD_HOST` | `127.0.0.1` | Only allow public binding with a token |
| `RHM_DASHBOARD_PORT` | `8765` | Dashboard listening port |
| `RHM_DASHBOARD_TOKEN` | unset | Required on any non-loopback bind |
| `RHM_DASHBOARD_ORIGINS` | none | Explicit cross-origin allowed browser origins |
| `RHM_NO_BUILD` | `0` | Set `1` to skip colcon on subsequent launches |

### Inspect your real topic mapping

The bundled example expects `/niihan/legacy/lidar/points` as `PointCloud2`,
`/imu` as `Imu`, and `/odom` as `Odometry`. **Only the LiDAR topic was previously
observed in this project's context; these are NOT confirmed current topic
names.** To inspect actual sources (in a new terminal):

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=188
ros2 topic list -t
ros2 topic info -v /niihan/legacy/lidar/points
```

Copy `src/rhm_surveillance_adapter/config/surveillance.yaml` to a personal
config file outside the public repository, update topic names/types to match
the live ROS graph and pass `RHM_PROFILE_PATH=/absolute/path/to/profile.yaml`.
For different ROS_DOMAIN_IDs or for hardware (which is NOT supported here),
operators must explicitly configure their environment. Without `/clock` in
simulation mode, freshness monitoring cannot be considered verified.

### Verify changes and observe real health

```bash
bash scripts/verify_surveillance.sh
# in another terminal while the surveillance simulation and dashboard run:
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=188
ros2 topic echo /robot_health --once
ros2 topic echo /rhm/surveillance/diagnostics --once
curl -fsS http://127.0.0.1:8765/api/healthz
```

`/api/healthz` checks the API process, **not** sensor health. The dashboard only
renders ROS data actually received. An absent sensor remains `STALE`, missing
score remains `—`, and the ABB IRB120 tile is explicitly `NOT CONNECTED`.
Node-presence checks are not Nav2 lifecycle checks. Diagnostic status
transitions are labeled as observations, not confirmed faults. The C++
aggregator does not yet produce meaningful `/fault_events`.

Runtime logs: `artifacts/surveillance_launch.log`,
`artifacts/dashboard.log`, and `artifacts/surveillance_build.log`.

**No surveillance integration run, robot navigation test, real hardware test,
Docker gate, or CI run has yet verified this new feature branch.**
