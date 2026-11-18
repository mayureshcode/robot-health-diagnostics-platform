# ADR 0003 — One Xacro model; EKF owns mobile odometry TF

Status: Accepted for **unverified** Phase 2A source (2026-11-09).

## Decision

Spawn the same Xacro-expanded URDF used by `robot_state_publisher` into Gazebo
Harmonic. Do not duplicate an independent SDF robot model. Bridge wheel
odometry and IMU to `robot_localization` and publish filtered `/odom` and
`odom -> base_link` from a single EKF. Do not bridge the Gazebo DiffDrive TF.

## Why

Reduces diverging inertial/joint definitions, avoids competing TF sources,
and lets the health monitor observe a standard EKF odometry feed.

## Alternatives

- Embed full robot SDF directly in the world: simpler to start, but duplicates
  geometry, fixed frame offsets and joint names maintained in URDF.
- Bridge Gazebo `/tf` directly: simplifies initial demo, but will compete with
  the EKF when `publish_tf` is enabled.
- Static `map -> odom`: deliberately rejected; no map localization yet.

## Risks and validation

Gazebo's URDF to SDF conversion must preserve the custom sensor and controller
plugins. We must verify with the native `--verify-sim` gate. The decision is
revisitable if conversion fails; no hardware safety assertion is made.
