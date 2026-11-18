# Robot Health Dashboard

> **Development status:** the dashboard runs locally; it is **not a public hosted website**, and a working ROS telemetry feed must be connected for live readings. The standalone mobile simulation and surveillance-adapter integrations are not hardware validated.

## What it displays

The FastAPI console provides a read-only overview of robot health: a mobile asset card, a future ABB IRB120 placeholder, health-score history, subsystem diagnostics, and an event timeline. The frontend intentionally uses **UNKNOWN / STALE** and unavailable values when no observations are received; a missing reading is not an actual zero health score.

- **Dashboard source:** [FastAPI and static frontend](../src/rhm_dashboard/)
- **ROS subscriber:** [ros_feed.py](../src/rhm_dashboard/rhm_dashboard/ros_feed.py)
- **Web UI:** [HTML](../src/rhm_dashboard/rhm_dashboard/static/index.html), [CSS](../src/rhm_dashboard/rhm_dashboard/static/app.css), [JavaScript](../src/rhm_dashboard/rhm_dashboard/static/app.js)
- **API tests:** [Dashboard tests](../src/rhm_dashboard/test/)
- **System design:** [Architecture](architecture.md)
- **Verification record:** [Validation matrix](validation_matrix.md)

## Run locally on Ubuntu 24.04

Install the repository's native ROS dependencies and build:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

**Standalone diagnostic nodes** (ROS domain 202 by default):

```bash
bash scripts/run_native.sh
```

Start the dashboard from a separate terminal in the **same ROS domain**:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=202
ros2 run rhm_dashboard dashboard
```

Open **http://127.0.0.1:8765** on the same computer. This address is local to your machine and is *not* an online demo.

The standalone diagnostics launcher does **not** start the dashboard or guarantee live sensor data. If no compatible ROS sensor messages arrive, the health report may remain STALE.

### Optional observer integration

`bash scripts/run_surveillance.sh` starts the separate read-only observer and dashboard on its configured ROS domain. It does not launch an external robot or control its motion. That adapter was experimental; do not interpret its sample topic profile as universally correct.

## Evidence for reviewers

For a convincing demonstration, record **real runtime output** from a verified test session: a Gazebo scene, the dashboard, sensor dropout, subsequent status change, and a saved test report. Do not edit in numerical status values or claim automated fault-manager recovery before implementation.

**Current limitations:** the C++ aggregator is partial, fault-event and recovery logic are incomplete, ABB IRB120 is not integrated, and no hardware validation has been conducted.
