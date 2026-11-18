#!/usr/bin/env bash
# Full source-level / ROS build & test gate. Runtime on actual surveillance graph
# is separately validated with scripts/run_surveillance.sh.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts
bash scripts/setup_dashboard.sh
set +u
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
set -u
set -o pipefail
colcon build --symlink-install --packages-up-to rhm_bringup rhm_dashboard \
  --event-handlers console_direct+ 2>&1 | tee artifacts/surveillance_verify_build.log
set +u
# shellcheck source=/dev/null
source install/setup.bash
set -u
# The dashboard's full tests require Pydantic v2 in .venv; colcon collects its
# stdlib-only asset test; the separate pytest call exercises all API contracts.
colcon test --packages-select rhm_surveillance_adapter rhm_dashboard rhm_bringup rhm_aggregator \
  --event-handlers console_direct+ 2>&1 | tee artifacts/surveillance_colcon_test.log
colcon test-result --verbose 2>&1 | tee artifacts/surveillance_test_result.log
.venv/bin/python -m pytest -q src/rhm_surveillance_adapter/test/test_logic.py \
  src/rhm_dashboard/test/test_api.py src/rhm_dashboard/test/test_store.py \
  --cov=rhm_surveillance_adapter.logic --cov=rhm_dashboard.schema \
  --cov-report=term-missing --cov-report=xml:artifacts/surveillance_coverage.xml \
  --cov-fail-under=85 \
  2>&1 | tee artifacts/surveillance_pytest.log
bash -n scripts/run_surveillance.sh scripts/setup_dashboard.sh scripts/verify_surveillance.sh
python3 -m py_compile scripts/check_surveillance_live.py
if command -v shellcheck >/dev/null; then
  shellcheck -s bash scripts/run_surveillance.sh scripts/setup_dashboard.sh scripts/verify_surveillance.sh
fi
if [[ -x .venv/bin/ruff ]]; then
  .venv/bin/ruff check src/rhm_surveillance_adapter src/rhm_dashboard \
    2>&1 | tee artifacts/surveillance_ruff.log
fi
if [[ "${RHM_LIVE_CHECK:-0}" == 1 ]]; then
  echo '[RHM] Running live ROS integration smoke (read-only) ...'
  live_args=()
  if [[ "${RHM_REQUIRE_LIDAR_OK:-0}" == 1 ]]; then live_args+=(--require-lidar-ok); fi
  python3 scripts/check_surveillance_live.py --timeout "${RHM_LIVE_TIMEOUT:-30}" \
    "${live_args[@]}" 2>&1 | tee artifacts/surveillance_live_smoke.log
  curl -fsS --max-time 5 "http://127.0.0.1:${RHM_DASHBOARD_PORT:-8765}/api/healthz" \
    2>&1 | tee artifacts/surveillance_dashboard_smoke.log
  printf '\nPASS: live diagnostics + API readiness.\n'
else
  printf '%s\n' 'PASS: source checks complete. Live surveillance integration NOT RUN (set RHM_LIVE_CHECK=1).'
fi
