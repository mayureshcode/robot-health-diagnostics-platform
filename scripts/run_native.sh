#!/usr/bin/env bash
# One-command native Ubuntu launcher for the currently implemented health nodes.
# Mobile sim is opt-in; no real hardware, Nav2, arm or dashboard is started.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts

usage() {
  cat <<'HELP'
Usage: bash scripts/run_native.sh [--no-build | --verify | --sim | --verify-sim]

  (no option)  Incrementally build the ROS workspace, launch the monitor and
               aggregator, activate both lifecycle nodes, and show a health sample.
  --no-build   Launch already built packages without rebuilding.
  --verify     Run the comprehensive native verification gate instead of launching.
  --sim        Build, launch and smoke-check the Gazebo mobile robot + diagnostics.
  --verify-sim Run the same headless simulation smoke gate, then exit.

Stop with Ctrl+C. --sim and --verify-sim are simulation-only. No real hardware.
Set RHM_SIM_GUI=1 with --sim to launch a Gazebo GUI (off by default).
Set RHM_DOMAIN_ID to override the isolated ROS domain (default: 202).
HELP
}

if (( $# > 1 )); then usage >&2; exit 2; fi

BUILD=1
SIM=0
VERIFY_SIM=0
case "${1:-}" in
  '') ;;
  --no-build) BUILD=0 ;;
  --verify) exec bash scripts/native_verify.sh ;;
  --sim) SIM=1 ;;
  --verify-sim) SIM=1; VERIFY_SIM=1 ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo 'ERROR: ROS 2 Jazzy not found at /opt/ros/jazzy/setup.bash' >&2
  exit 2
fi

# ROS environment hooks may access optional variables before defining them.
set +u
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
set -u

if [[ "${ROS_DISTRO:-}" != jazzy ]]; then
  echo "ERROR: expected ROS 2 Jazzy, got ${ROS_DISTRO:-unset}" >&2
  exit 2
fi

export ROS_DOMAIN_ID="${RHM_DOMAIN_ID:-202}"
# Isolate Gazebo transport from other projects on the same developer machine.
if (( SIM )); then
  export GZ_PARTITION="${RHM_GZ_PARTITION:-rhm_health_${ROS_DOMAIN_ID}}"
  for command in gz xacro; do
    if ! command -v "$command" >/dev/null 2>&1; then
      echo "ERROR: simulation requires $command. Run bash scripts/setup_native.sh" >&2
      exit 2
    fi
  done
fi
echo "[RHM] Native Ubuntu launcher | ROS_DISTRO=$ROS_DISTRO | ROS_DOMAIN_ID=$ROS_DOMAIN_ID"

if (( BUILD )); then
  echo '[RHM] Building workspace (incremental colcon build) ...'
  colcon build --symlink-install --event-handlers console_direct+ \
    > >(tee artifacts/run_native_build.log) 2>&1
fi

if [[ ! -f install/setup.bash ]]; then
  echo 'ERROR: workspace not built; run without --no-build first.' >&2
  exit 2
fi
set +u
# shellcheck source=/dev/null
source install/setup.bash
set -u

if ! ros2 pkg prefix rhm_bringup >/dev/null 2>&1; then
  echo 'ERROR: rhm_bringup is unavailable after sourcing install/setup.bash.' >&2
  exit 2
fi

if (( SIM )); then
  for pkg in rhm_description rhm_sim ros_gz_sim ros_gz_bridge robot_localization; do
    if ! ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
      echo "ERROR: required ROS package $pkg not found; run bash scripts/setup_native.sh" >&2
      exit 2
    fi
  done
fi

LAUNCH_PID=''
cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  if [[ -n "$LAUNCH_PID" ]] && kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo -e '\n[RHM] Stopping ROS launch ...'
    kill -INT "$LAUNCH_PID" 2>/dev/null || true
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if (( SIM )); then
  echo '[RHM] Starting Gazebo Harmonic mobile robot, EKF and diagnostics ...'
  launch_file=mobile_sim.launch.py
  launch_args=("gui:=${RHM_SIM_GUI:-false}")
else
  echo '[RHM] Starting lifecycle monitor and aggregator ...'
  launch_file=native_health.launch.py
  launch_args=()
fi
ros2 launch rhm_bringup "$launch_file" "${launch_args[@]}" \
  > >(tee artifacts/run_native_launch.log) 2>&1 &
LAUNCH_PID=''

# Lifecycle transitions are explicit: merely starting a lifecycle node is not enough.
for node in /rhm_sensor_monitor /rhm_aggregator; do
  ready=0
  for _ in {1..40}; do
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
      echo "ERROR: ROS launch exited before $node was available." >&2
      tail -n 40 artifacts/run_native_launch.log >&2 || true
      exit 1
    fi
    if timeout 3 ros2 lifecycle get "$node" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.25
  done
  if (( ! ready )); then
    echo "ERROR: lifecycle node $node did not appear. See artifacts/run_native_launch.log" >&2
    exit 1
  fi
done

bash scripts/activate_native.sh

if (( SIM )); then
  echo '[RHM] Checking live simulated sensors, EKF TF and healthy diagnostics ...'
  if ! python3 scripts/check_mobile_sim.py --timeout "${RHM_SIM_TIMEOUT:-90}" \
      > >(tee artifacts/sim_smoke.log) 2>&1; then
    echo 'ERROR: simulated sensor/TF/health smoke test failed; see artifacts/sim_smoke.log' >&2
    exit 1
  fi
  echo '[RHM] Mobile simulation health check passed.'
  if (( VERIFY_SIM )); then
    echo '[RHM] --verify-sim gate completed; terminating launch.'
    exit 0
  fi
  echo '[RHM] Gazebo mobile robot and diagnostics running. Ctrl+C to stop.'
  wait "$LAUNCH_PID"
  exit $?
fi

echo '[RHM] Waiting for the first /robot_health message ...'
if ! timeout 15 ros2 topic echo /robot_health rhm_interfaces/msg/HealthStatus --once; then
  echo 'ERROR: no health sample within 15 seconds; see artifacts/run_native_launch.log' >&2
  exit 1
fi

echo '[RHM] Running. Missing sensor streams should report STALE (this is expected).'
echo '[RHM] This baseline does not include a simulated robot, arm, or dashboard.'
echo '[RHM] Ctrl+C to stop; logs: artifacts/run_native_launch.log'
wait "$LAUNCH_PID"
