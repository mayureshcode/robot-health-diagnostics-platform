# Native Ubuntu development guide (primary workflow)

This workspace is designed for **Ubuntu 24.04.x + ROS 2 Jazzy**, using the system
Python 3.12 from `/usr/bin/python3`, Gazebo Harmonic (`gz sim`, version 8.x),
Nav2, MoveIt 2, and `colcon`. It does **not** assume Docker is installed.

## First-time setup

```bash
cd ~/robot-health-project/robot-health-diagnostics-platform
bash scripts/doctor.sh
bash scripts/setup_native.sh
```

`setup_native.sh` installs deb-managed developer tools and test dependencies,
resolves ROS package dependencies through `rosdep`, and creates a local `.venv`
with pinned Python linters. The script does not modify your Nvidia drivers or
replace the system Python and does not touch other ROS workspaces.

## Full native gate

```bash
bash scripts/native_verify.sh
```

This runs rosdep, shell syntax checks, ShellCheck, a `colcon` build, `colcon`
tests, test-result inspection, Python pure-logic coverage, Ruff, strict Mypy
for pure logic, Cppcheck, Clang-Tidy, and a ROS lifecycle graph smoke test.
The test exits nonzero on the first error. See `artifacts/native-summary.txt`
for command/exit evidence and the step-specific log files.

For an **incomplete preliminary check only**, set:

```bash
RHM_SKIP_SMOKE=1 bash scripts/native_verify.sh
```

This is not a complete runtime gate and must not be reported as one.
`RHM_SKIP_ROSDEP=1` skips dependency installation, not dependency validation.

## One-command native launch (monitor-only or Gazebo mobile)

From the repository root, launch the **currently implemented** components:

```bash
bash scripts/run_native.sh
```

The launcher incrementally builds the workspace, sources both setup files
(safely around Bash `nounset`), launches `rhm_sensor_monitor` and
`rhm_aggregator`, waits for both lifecycle services, activates the nodes, and
prints the first `/robot_health` message. `Ctrl+C` stops the launch process.
See `artifacts/run_native_build.log` and `artifacts/run_native_launch.log`.

Optional usage:

```bash
bash scripts/run_native.sh --no-build    # skip the incremental build
bash scripts/run_native.sh --verify      # run native build/test/lint/smoke instead
RHM_DOMAIN_ID=203 bash scripts/run_native.sh  # override default isolated domain 202
```

No sensor producers are started, so the report should show **STALE**.
This indicates fail-safe behavior, not that a real or simulated robot is
publishing data. **ABB IRB120, Nav2, MoveIt and dashboard are not implemented**. A new
Gazebo mobile launch exists but is **unverified until `--verify-sim` passes**.

## Mobile Gazebo simulation (new source)

```bash
bash scripts/run_native.sh --sim
RHM_SIM_GUI=1 bash scripts/run_native.sh --sim
bash scripts/run_native.sh --verify-sim
```

Read [Phase 2A simulation guide](phase2_mobile_sim.md) for topics, TF,
GPU headless troubleshooting, and what is actually tested.

## Switching to Gazebo later

Use the simulation-specific ROS parameters in
`src/rhm_monitors/config/monitors.sim.yaml` (`use_sim_time: true`) **only if
Gazebo is publishing `/clock`**. Native smoke and non-Gazebo diagnostics use
`use_sim_time: false` to prevent timer callbacks from freezing.

## Known limitations

- The new mobile Gazebo source is unverified; the ABB arm cell is absent.
- The existing C++ aggregator currently summarizes only the `mobile` asset.
- Fault events, fault reset, scenario regression, and predictive modules remain
  incomplete.
- No real hardware is commanded or validated.
- The native smoke test uses missing-sensor behavior, not a simulated robot.
- Lifecycle tests are local direct-transition regression tests. A full
  `launch_testing` process-level test is future work.

## Troubleshooting

**`ament_python` rosdep key missing:** the original manifest incorrectly used
`<buildtool_depend>ament_python</buildtool_depend>`. This was removed from the
revised `src/rhm_monitors/package.xml` (the `<build_type>` export stays).

**`Ran 0 tests / exit 5`:** the original monitor package had no `test_*.py`
files. Regression tests now live in `src/rhm_monitors/test/`.

**Import errors from Python:** source `/opt/ros/jazzy/setup.bash`, use Ubuntu's
Python 3.12 and avoid Conda/foreign virtual environments when calling ROS nodes.

**`git status` says not a Git repository:** the ZIP is source-only. Use the
provided `.bundle` to restore the branch and Git history instead of blindly
running `git init` (see the README).

**CUDA or GPU errors:** the current native smoke test is CPU-only. GPU drivers
are irrelevant until a specific simulation or GPU-heavy workload is enabled.
