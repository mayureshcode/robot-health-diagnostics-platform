#!/usr/bin/env bash
# One-command Ubuntu integration: OBSERVE an external ROS 2 surveillance robot.
# No motion commands. Existing surveillance project must be launched independently.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo 'ERROR: ROS Jazzy not installed at /opt/ros/jazzy/setup.bash' >&2
  exit 2
fi
set +u
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
set -u
export ROS_DOMAIN_ID="${RHM_SURVEILLANCE_DOMAIN_ID:-188}"
export RHM_DASHBOARD_HOST="${RHM_DASHBOARD_HOST:-127.0.0.1}"
export RHM_DASHBOARD_PORT="${RHM_DASHBOARD_PORT:-8765}"
export RHM_USE_SIM_TIME="${RHM_USE_SIM_TIME:-true}"
if [[ ! "$ROS_DOMAIN_ID" =~ ^[0-9]+$ ]] || (( ROS_DOMAIN_ID > 232 )); then
  echo 'ERROR: ROS_DOMAIN_ID must be an integer in 0..232' >&2; exit 2
fi
if [[ ! "$RHM_DASHBOARD_PORT" =~ ^[0-9]+$ ]] ||
   (( RHM_DASHBOARD_PORT < 1024 || RHM_DASHBOARD_PORT > 65535 )); then
  echo 'ERROR: RHM_DASHBOARD_PORT must be 1024..65535' >&2; exit 2
fi
if [[ "$RHM_DASHBOARD_HOST" != '127.0.0.1' && "$RHM_DASHBOARD_HOST" != localhost && "$RHM_DASHBOARD_HOST" != '::1' && -z "${RHM_DASHBOARD_TOKEN:-}" ]]; then
  echo 'ERROR: set RHM_DASHBOARD_TOKEN before binding the dashboard beyond loopback' >&2; exit 2
fi
bash scripts/setup_dashboard.sh
if [[ "${RHM_NO_BUILD:-0}" != 1 ]]; then
  echo '[RHM] Building observer + dashboard + bringup dependencies ...'
  colcon build --symlink-install --packages-up-to rhm_bringup rhm_dashboard \
    --event-handlers console_direct+ 2>&1 | tee artifacts/surveillance_build.log
fi
set +u
# shellcheck source=/dev/null
source install/setup.bash
set -u
if ! ros2 pkg prefix rhm_surveillance_adapter >/dev/null 2>&1; then
  echo '[RHM] ERROR: adapter package not discoverable after build' >&2; exit 2
fi
LAUNCH_PID=''
DASH_PID=''
cleanup(){
  local rc=$?
  trap - EXIT INT TERM
  if [[ -n "$DASH_PID" ]] && kill -0 "$DASH_PID" 2>/dev/null; then
    kill -TERM "$DASH_PID" 2>/dev/null || true
    wait "$DASH_PID" 2>/dev/null || true
  fi
  if [[ -n "$LAUNCH_PID" ]]; then
    # ros2 launch runs in its own session. Terminate the *whole* session's
    # process group, not just the launch parent: Gazebo/ROS children may
    # otherwise survive and register duplicate lifecycle nodes.
    kill -TERM -- "-$LAUNCH_PID" 2>/dev/null || true
    for _ in {1..30}; do
      if ! kill -0 -- "-$LAUNCH_PID" 2>/dev/null; then break; fi
      sleep 0.1
    done
    if kill -0 -- "-$LAUNCH_PID" 2>/dev/null; then
      echo "[RHM] Force stopping remaining RHM launch processes" >&2
      kill -KILL -- "-$LAUNCH_PID" 2>/dev/null || true
    fi
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Lifecycle CLI operations use separate ROS graph queries. A successful transition
# response should lead to the requested steady state; allow discovery to settle
# and reject duplicate fully qualified names instead of trusting an arbitrary
# service response from a different process.
lifecycle_diagnostics() {
  local node="$1"
  echo "[RHM] Lifecycle diagnostics for $node (ROS_DOMAIN_ID=$ROS_DOMAIN_ID)" >&2
  echo '[RHM] Discovered RHM nodes:' >&2
  timeout 8 ros2 node list --no-daemon 2>&1 | grep -E 'rhm_(aggregator|surveillance_monitor)' >&2 || true
  echo '[RHM] Lifecycle state:' >&2
  timeout 5 ros2 lifecycle get "$node" >&2 || true
  echo '[RHM] Relevant processes:' >&2
  pgrep -af 'health_aggregator|surveillance_monitor' >&2 || true
  echo '[RHM] Last ROS launch output:' >&2
  tail -n 80 artifacts/surveillance_launch.log >&2 || true
}

wait_lifecycle_state() {
  local node="$1" expected="$2" state=''
  for _ in {1..24}; do
    state="$(timeout 4 ros2 lifecycle get "$node" 2>/dev/null || true)"
    if [[ "$state" == "$expected" ]]; then
      echo "[RHM] $node: $state"
      return 0
    fi
    sleep 0.25
  done
  echo "ERROR: $node did not reach $expected (last state: ${state:-unavailable})" >&2
  lifecycle_diagnostics "$node"
  return 1
}

require_unique_node() {
  local node="$1" nodes='' count=0
  nodes="$(timeout 8 ros2 node list --no-daemon 2>/dev/null || true)"
  if [[ -z "$nodes" ]]; then
    echo "ERROR: unable to inspect ROS graph before activating $node" >&2
    lifecycle_diagnostics "$node"
    return 1
  fi
  count="$(printf '%s\n' "$nodes" | awk -v target="$node" '$0 == target {n++} END {print n + 0}')"
  if [[ "$count" != 1 ]]; then
    echo "ERROR: expected one $node, observed $count. An older process may still be running." >&2
    lifecycle_diagnostics "$node"
    return 1
  fi
}
# Do not start another observer if one already exists in this ROS domain.
# This is intentionally read-only: never terminate unrelated ROS processes.
existing_nodes="$(timeout 8 ros2 node list --no-daemon 2>/dev/null | \
  grep -E '^/rhm_(aggregator|surveillance_monitor)$' || true)"
if [[ -n "$existing_nodes" ]]; then
  echo '[RHM] ERROR: RHM nodes are already running in this ROS domain:' >&2
  printf '%s\n' "$existing_nodes" >&2
  echo '[RHM] Stop the older RHM processes before starting a new instance.' >&2
  exit 1
fi

# Existing robot is untouched; only subscriber nodes are started here.
echo "[RHM] Observing surveillance ROS_DOMAIN_ID=${ROS_DOMAIN_ID}, use_sim_time=${RHM_USE_SIM_TIME}"
# Start ROS launch in a separate session/process group so cleanup includes
# its Python/C++ children even if ros2 launch stops unexpectedly.
setsid ros2 launch rhm_bringup surveillance_health.launch.py \
  > artifacts/surveillance_launch.log 2>&1 &
LAUNCH_PID=$!
for node in /rhm_surveillance_monitor /rhm_aggregator; do
  ready=0
  for _ in {1..45}; do
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
      echo "ERROR: launch process stopped while waiting for $node" >&2
      tail -n 60 artifacts/surveillance_launch.log >&2; exit 1
    fi
    if timeout 2 ros2 lifecycle get "$node" >/dev/null 2>&1; then
      ready=1; break
    fi
    sleep 0.5
  done
  if (( ! ready )); then
    echo "ERROR: lifecycle node $node unavailable" >&2
    tail -n 60 artifacts/surveillance_launch.log >&2; exit 1
  fi
  require_unique_node "$node"
  if ! timeout 15 ros2 lifecycle set "$node" configure; then
    echo "ERROR: configure transition returned failure: $node" >&2
    lifecycle_diagnostics "$node"
    exit 1
  fi
  wait_lifecycle_state "$node" 'inactive [2]'
  if ! timeout 15 ros2 lifecycle set "$node" activate; then
    echo "ERROR: activate transition returned failure: $node" >&2
    lifecycle_diagnostics "$node"
    exit 1
  fi
  wait_lifecycle_state "$node" 'active [3]'

done
.venv/bin/python -m rhm_dashboard.server > artifacts/dashboard.log 2>&1 &
DASH_PID=$!
ready=0
for _ in {1..35}; do
  if ! kill -0 "$DASH_PID" 2>/dev/null; then
    echo '[RHM] ERROR: dashboard process exited' >&2
    tail -n 70 artifacts/dashboard.log >&2;exit 1
  fi
  if curl -fsS --max-time 2 "http://127.0.0.1:${RHM_DASHBOARD_PORT}/api/healthz" >/dev/null 2>&1; then
    ready=1;break
  fi
  sleep 0.4
done
if (( ! ready )); then
  echo '[RHM] ERROR: dashboard did not become ready' >&2
  tail -n 70 artifacts/dashboard.log >&2;exit 1
fi
echo
printf '[RHM] Open in Firefox: http://127.0.0.1:%s\n' "$RHM_DASHBOARD_PORT"
echo '[RHM] This dashboard does NOT start the surveillance simulation.'
echo '[RHM] All readouts are from real incoming ROS traffic (or unavailable).'
echo '[RHM] Logs: artifacts/surveillance_launch.log and artifacts/dashboard.log'
echo '[RHM] Ctrl+C stops only these monitoring processes.'
wait "$LAUNCH_PID"
