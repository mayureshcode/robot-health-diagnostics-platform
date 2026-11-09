# Operations runbook — Ubuntu 24.04 / ROS 2 Jazzy

## Entry points

- `bash scripts/doctor.sh` — read-only host inventory.
- `bash scripts/setup_native.sh` — install development dependencies once.
- `bash scripts/native_verify.sh` — strict native build, test, lint and smoke.
- `bash scripts/native_smoke.sh` — short ROS lifecycle smoke test without Gazebo.
- `ros2 launch rhm_bringup native_health.launch.py` — monitor + aggregator,
  with explicit lifecycle activation via `scripts/activate_native.sh`.
- `bash scripts/docker_verify.sh` — optional container verification (CI gate).

## Failure policy

Every verification step records its command and exit status under `artifacts/`.
If a step fails, stop at that step, preserve the first meaningful compiler or
runtime error, and fix it before interpreting subsequent checks. `colcon
 test-result` can report zero failed test cases even when pytest exits 5 because
no tests were collected: always inspect the `colcon test` process exit code.

## Native versus simulation

`/diagnostics` and `/robot_health` can exist when no sensor source exists.
Missing input must produce `STALE`, never an invented healthy status. A Gazebo
world, /clock, TF frames, actual simulated sensors, and a running planning
stack are separate evidence requirements.

## Existing branch restoration

Source ZIPs often exclude `.git`. Prefer the companion Git bundle for a
working local branch with history; do not mark manual `git init` as restoration
of original commits.
