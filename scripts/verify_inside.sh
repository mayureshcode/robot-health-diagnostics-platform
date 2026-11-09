#!/usr/bin/env bash
# shellcheck disable=SC1091
set -Eeuo pipefail
source /opt/ros/jazzy/setup.bash
mkdir -p artifacts
exec > >(tee artifacts/inside_verify.log) 2>&1
trap 'rc=$?; echo "INSIDE_EXIT_CODE=$rc"; exit "$rc"' EXIT
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
python3 -m pytest -q pure_tests --cov=src/rhm_monitors/rhm_monitors/logic --cov-report=xml:artifacts/coverage.xml --cov-report=term --cov-fail-under=85
ruff check src/rhm_monitors/rhm_monitors src/rhm_monitors/test src/rhm_bringup
mypy --strict src/rhm_monitors/rhm_monitors/logic
bash -n scripts/*.sh
shellcheck scripts/*.sh
cppcheck --enable=warning,style,performance --error-exitcode=1 --suppress=missingIncludeSystem src/rhm_aggregator/src
clang-tidy -p build/rhm_aggregator src/rhm_aggregator/src/aggregator.cpp
