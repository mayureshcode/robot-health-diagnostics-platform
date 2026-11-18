#!/usr/bin/env bash
# Single, fail-closed verification entrypoint for native Ubuntu 24.04 + ROS 2 Jazzy.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts
ARTIFACTS="$ROOT/artifacts"
SUMMARY="$ARTIFACTS/native-summary.txt"
printf 'RHM native verification | %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$SUMMARY"
record() { printf '%s\n' "$*" | tee -a "$SUMMARY"; }
run_step() {
  local name="$1" rc=0
  shift
  record "BEGIN $name | command: $*"
  if "$@" 2>&1 | tee "$ARTIFACTS/${name}.log"; then
    record "PASS $name | exit=0"
  else
    rc=${PIPESTATUS[0]}
    record "FAIL $name | exit=$rc | see artifacts/${name}.log"
    return "$rc"
  fi
}
# shellcheck source=/dev/null
. /etc/os-release
if [[ "${ID:-}:${VERSION_ID:-}" != ubuntu:24.04 ]]; then
  record 'FAIL environment | not Ubuntu 24.04'; exit 2
fi
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  record 'FAIL environment | missing /opt/ros/jazzy/setup.bash'; exit 2
fi
set +u  # ROS environment hooks may reference unset optional variables.
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
set -u
if [[ "${ROS_DISTRO:-}" != jazzy ]]; then
  record "FAIL environment | expected ROS_DISTRO=jazzy, got ${ROS_DISTRO:-unset}"; exit 2
fi
for executable in colcon rosdep cppcheck clang-tidy shellcheck; do
  if ! command -v "$executable" >/dev/null 2>&1; then
    record "FAIL tooling | missing $executable; run bash scripts/setup_native.sh"; exit 2
  fi
done
if [[ ! -x .venv/bin/ruff || ! -x .venv/bin/mypy ]]; then
  record 'FAIL tooling | native Python tools absent; run bash scripts/setup_native.sh'; exit 2
fi
if [[ "${RHM_SKIP_ROSDEP:-0}" != 1 ]]; then
  run_step rosdep rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
fi
run_step bash_syntax bash -n scripts/doctor.sh scripts/setup_native.sh scripts/native_verify.sh scripts/native_smoke.sh scripts/activate_native.sh scripts/run_native.sh scripts/docker_verify.sh
run_step shellcheck shellcheck -s bash scripts/doctor.sh scripts/setup_native.sh scripts/native_verify.sh scripts/native_smoke.sh scripts/activate_native.sh scripts/run_native.sh
run_step phase2_python_syntax python3 -m py_compile scripts/check_mobile_sim.py src/rhm_bringup/launch/mobile_sim.launch.py
run_step xacro_validate xacro src/rhm_description/urdf/rhm_mobile.urdf.xacro
run_step colcon_build colcon build --symlink-install --event-handlers console_direct+ --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
set +u  # ROS environment hooks may reference unset optional variables.
# shellcheck source=/dev/null
source install/setup.bash
set -u
run_step colcon_test colcon test --event-handlers console_direct+
run_step test_results colcon test-result --verbose
run_step coverage .venv/bin/python -m pytest -q src/rhm_monitors/test/test_health.py \
  --cov=rhm_monitors.logic --cov-report=term-missing --cov-report=xml:artifacts/coverage.xml --cov-fail-under=85
run_step ruff .venv/bin/ruff check src/rhm_monitors/rhm_monitors src/rhm_monitors/test src/rhm_bringup
run_step mypy .venv/bin/mypy --strict src/rhm_monitors/rhm_monitors/logic
run_step cppcheck cppcheck --enable=warning,performance --error-exitcode=1 --suppress=missingIncludeSystem --language=c++ --std=c++17 -Isrc/rhm_aggregator/include src/rhm_aggregator/src
run_step clang_tidy clang-tidy -p build/rhm_aggregator src/rhm_aggregator/src/aggregator.cpp
if [[ "${RHM_SKIP_SMOKE:-0}" != 1 ]]; then
  run_step native_smoke bash scripts/native_smoke.sh
else
  record 'SKIP native_smoke | RHM_SKIP_SMOKE=1 (not a full runtime gate)'
fi
record 'Native verification finished. This is not Docker, CI, Gazebo, or hardware validation.'
