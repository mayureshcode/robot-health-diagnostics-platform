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

## Surveillance observer fails the `activate` lifecycle transition

The observer must call `super().on_activate(state)` and
`super().on_deactivate(state)` for its `create_lifecycle_publisher()`.
ROS 2 Jazzy's managed-publisher callbacks accept the lifecycle state argument;
calling `publisher.on_activate()` without it triggers an exception that Jazzy's
lifecycle transition wrapper converts into a failed transition. The supervisor
must validate `inactive [2]` after configure and `active [3]` after activate,
not merely inspect whether `ros2 lifecycle set` printed a success line.

Retrieve the actual error when a transition fails:

```bash
cd ~/robot-health-project/rhm-native
tail -n 100 artifacts/surveillance_launch.log
```

After applying the fix, run `bash scripts/verify_surveillance.sh` to exercise
ROS package tests, including the adapter lifecycle regression test. Start the
surveillance project separately, then run `bash scripts/run_surveillance.sh`.
Do not infer a live dashboard connection from source-level test coverage alone.


### Surveillance aggregator reports `inactive [2]` after `activate`

The launcher requires the aggregator to reach `active [3]`; a successful
transition command alone is insufficient. It now polls for the expected state
and records the discovered ROS node names and matching processes on failure.
The C++ aggregator also logs successful configure/activate and deactivate
callbacks to `artifacts/surveillance_launch.log`.

If the problem repeats, first inspect `artifacts/surveillance_launch.log` and
use the ROS domain configured for the surveillance project:

```bash
export ROS_DOMAIN_ID=188
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 node list --no-daemon | sort | uniq -c | grep -E 'rhm_(aggregator|surveillance_monitor)'
pgrep -af 'health_aggregator|surveillance_monitor'
```

If multiple `/rhm_aggregator` instances exist, stop only the stale health
monitor launch processes before retrying; do not terminate the surveillance
robot itself. Do not suppress the active-state gate or fabricate health data.


### Duplicate RHM nodes after launcher error

If `ros2 node list --no-daemon` displays several instances of
`/rhm_surveillance_monitor` or `/rhm_aggregator`, previously spawned observer
processes may have survived their `ros2 launch` parent. Stop *only* the
processes whose executable paths point to this RHM checkout; never kill
Gazebo, Nav2, or surveillance project nodes. Example diagnosis:

```bash
pgrep -af 'rhm_surveillance_adapter/lib/rhm_surveillance_adapter/surveillance_monitor|rhm_aggregator/lib/rhm_aggregator/health_aggregator'
```

The revised launcher refuses to start when an RHM node already exists. It
starts its own launch process group and shuts down all children when it exits.
After the stale observer processes have stopped, run
`bash scripts/run_surveillance.sh`. Confirm one node of each name and both
lifecycle states `active [3]` before trusting dashboard data.
