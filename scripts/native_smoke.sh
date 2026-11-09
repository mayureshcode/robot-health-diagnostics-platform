#!/usr/bin/env bash
# Native ROS graph smoke test without Gazebo or motion; expected missing sensors -> STALE.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts
# Keep the smoke graph isolated from other local ROS projects.
export ROS_DOMAIN_ID="${RHM_SMOKE_DOMAIN_ID:-201}"
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
if [[ ! -f install/setup.bash ]]; then
  echo 'ERROR: build and source workspace before the smoke test.' >&2
  exit 2
fi
# shellcheck source=/dev/null
source install/setup.bash
pids=()
cleanup() {
  local pid
  for pid in "${pids[@]}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  wait "${pids[@]}" 2>/dev/null || true
}
trap cleanup EXIT
ros2 run rhm_monitors sensor_monitor >artifacts/smoke_monitor.log 2>&1 &
pids+=("$!")
ros2 run rhm_aggregator health_aggregator >artifacts/smoke_aggregator.log 2>&1 &
pids+=("$!")
for node in /rhm_sensor_monitor /rhm_aggregator; do
  ready=0
  for _ in {1..30}; do
    if timeout 2 ros2 lifecycle get "$node" >/dev/null 2>&1; then
      ready=1; break
    fi
    sleep 0.2
  done
  if (( ! ready )); then
    echo "ERROR: lifecycle node $node did not become available" >&2
    exit 1
  fi
done
bash scripts/activate_native.sh
# No sensors are launched, so health should be fail-safe STALE; topic must publish.
timeout 15 ros2 topic echo /robot_health rhm_interfaces/msg/HealthStatus --once >artifacts/smoke_health.log
if ! grep -q 'asset_id: mobile' artifacts/smoke_health.log; then
  echo 'ERROR: health message missing mobile asset' >&2; exit 1
fi
if ! grep -Eq '^status: 3$' artifacts/smoke_health.log; then
  echo 'ERROR: expected STALE status without sensors' >&2; exit 1
fi
echo 'Native ROS smoke: observed mobile health STALE with absent sensors.'
cat artifacts/smoke_health.log
