#!/usr/bin/env bash
# shellcheck disable=SC1091
set -Eeuo pipefail
set +u  # ROS environment hooks may reference unset optional variables.
source /opt/ros/jazzy/setup.bash
set -u
mkdir -p artifacts
exec > >(tee artifacts/inside_verify.log) 2>&1
trap 'rc=$?; echo "INSIDE_EXIT_CODE=$rc"; exit "$rc"' EXIT
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
set +u  # ROS environment hooks may reference unset optional variables.
source install/setup.bash
set -u
colcon test --event-handlers console_direct+
colcon test-result --verbose
python3 -m pytest -q pure_tests --cov=src/rhm_monitors/rhm_monitors/logic --cov-report=xml:artifacts/coverage.xml --cov-report=term --cov-fail-under=85
python3 -m pytest -q src/rhm_surveillance_adapter/test/test_logic.py \
  src/rhm_dashboard/test/test_api.py src/rhm_dashboard/test/test_store.py
ruff check src/rhm_monitors/rhm_monitors src/rhm_monitors/test src/rhm_bringup \
  src/rhm_surveillance_adapter src/rhm_dashboard
mypy --strict src/rhm_monitors/rhm_monitors/logic
bash -n scripts/*.sh
shellcheck scripts/*.sh
cppcheck --enable=warning,style,performance --error-exitcode=1 --suppress=missingIncludeSystem src/rhm_aggregator/src
clang-tidy -p build/rhm_aggregator src/rhm_aggregator/src/aggregator.cpp
