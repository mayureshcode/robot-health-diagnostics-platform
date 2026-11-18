# Phase 2A: native Gazebo Harmonic mobile simulation

**Status:** source implemented, **ROS/Gazebo runtime UNVERIFIED** in the authoring sandbox.
All scenarios are simulation-only; nothing commands physical hardware.

## Native one-command demo

After pulling/applying this batch from the repository root:

```bash
# First time if rosdep reports missing packages (does not reinstall ROS):
bash scripts/setup_native.sh
# Start a headless Gazebo simulation, robot, bridge, EKF and diagnostics:
bash scripts/run_native.sh --sim
# Optional visual Gazebo window (requires an Xorg/Wayland display):
RHM_SIM_GUI=1 bash scripts/run_native.sh --sim
# Headless integration test and exit, returning nonzero on any missing feed:
bash scripts/run_native.sh --verify-sim
# Existing no-Gazebo native unit/lint/smoke gate:
bash scripts/run_native.sh --verify
```

`--sim` *first* builds all ROS packages, then starts Gazebo, the simulation
transport bridges, `robot_state_publisher`, EKF and the existing two lifecycle
nodes. `scripts/check_mobile_sim.py` must see clock, LiDAR, IMU, wheel odom,
EKF odom, TF (including wheel joints) and a healthy aggregated report before the launcher announces
readiness. If any are missing it fails with a nonzero exit status. Leave the
terminal open; Ctrl+C shuts down the launch. Logs:
`artifacts/run_native_build.log`, `artifacts/run_native_launch.log`,
`artifacts/sim_smoke.log`.

When using a second terminal, source the installed workspace and use the
isolated domain:

```bash
source /opt/ros/jazzy/setup.bash
source ~/robot-health-project/rhm-native/install/setup.bash
export ROS_DOMAIN_ID=202
ros2 topic list | grep -E '^/(scan|imu|odom|wheel/odom|robot_health|diagnostics|clock)$'
ros2 topic echo /robot_health rhm_interfaces/msg/HealthStatus --once
ros2 run tf2_ros tf2_echo odom base_link
```

## Source of truth

`rhm_description/urdf/rhm_mobile.urdf.xacro` is the **single robot** model.
ROS 2 `robot_state_publisher` and Gazebo spawn use the same expanded Xacro.
The world in `rhm_sim/worlds/warehouse.sdf` contains the flat ground and two
static obstacle racks. The robot spawns at x=0, y=0, yaw=0, z=0.25 m by
default; no autonomous velocity command is published. Alternative
spawn poses can be passed to `ros2 launch rhm_bringup mobile_sim.launch.py`
using `spawn_x:=`, `spawn_y:=` and `spawn_yaw:=` when using manual launch.

The Xacro Gazebo plugins implement:
- `DiffDrive` on the two wheel joints, with constrained simulated velocities,
  producing Gazebo `/wheel/odom` and consuming `/rhm/cmd_vel` only.
- IMU at `/imu` with frame `imu_link`.
- 2D GPU LiDAR at `/scan` with frame `lidar_link`.
- Joint state publisher for wheel joint motion.

Gazebo world plugins provide the physics, sensor rendering and IMU systems.
`rhm_sim/config/bridge.yaml` maps Gazebo transport to ROS. All sensor
streams use `SENSOR_DATA` QoS; `/clock` uses `CLOCK`. The ROS `/odom`
stream is produced by `robot_localization` EKF from `/wheel/odom` and
`/imu`. The Gazebo odom->base transform is deliberately **not** bridged so
that only the EKF publishes that TF in ROS.

## TF contract

```text
odom                         [robot_localization EKF]
└── base_link                 [robot_state_publisher robot root]
    ├── lidar_link            [static URDF]
    ├── imu_link              [static URDF]
    ├── caster_link           [static URDF]
    ├── left_wheel_link       [joint_states]
    └── right_wheel_link      [joint_states]
```

**No `map -> odom` transform** is created; a map/SLAM stack is not present
in this milestone. Claiming complete map-frame localization would be wrong.
Nav2 navigation is not launched. The EKF configuration is a simulation-first
example, not an accuracy-validated localization model.

## Verification

1. `bash scripts/run_native.sh --verify`: unit tests, `xacro` expansion,
   existing code lint and native diagnostic smoke test.
2. `bash scripts/run_native.sh --verify-sim`: headless Gazebo sensor and TF
   integration smoke test. The tool reports counts and exits nonzero if any
   required sensor, TF, or healthy status is absent at the timeout.
3. With `RHM_SIM_GUI=1`, inspect the robot and obstacles. This visual step
   is **not covered** by the headless test.

### Known limitations

- Gazebo GPU LiDAR uses OGRE2 and may fail with unsupported headless graphics
  drivers. Check `artifacts/run_native_launch.log` for renderer/plugin errors.
- The simulation is stationary unless someone explicitly sends a velocity
  command to the **simulation-only** `/rhm/cmd_vel` bridge. No motion behavior
  is part of the smoke test.
- No physical devices, Nav2 actions, collision recovery, or arm cell run.
- Timing/accuracy, load, performance, thermal, and collision benchmarks are
  not measured. Native host/CI/Docker validation remains pending until logs
  from those environments are captured.

## References

- Gazebo Harmonic sensor systems: https://gazebosim.org/docs/harmonic/sensors/
- Gazebo DiffDrive parameters: https://gazebosim.org/api/sim/9/classgz_1_1sim_1_1systems_1_1DiffDrive.html
- ROS Gazebo bridge: https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_bridge/README.md
- Nav2 guide to EKF odometry: https://docs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/odom/setup_robot_localization/
