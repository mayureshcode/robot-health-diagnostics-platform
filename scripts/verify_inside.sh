#!/usr/bin/env bash
set -Eeuo pipefail
source /opt/ros/jazzy/setup.bash
mkdir -p artifacts
exec > >(tee artifacts/inside_verify.log) 2>&1
trap 'rc=$?; echo "INSIDE_EXIT_CODE=$rc"; exit "$rc"' EXIT
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
python3 -m pytest -q pure_tests --cov=src/rhm_monitors/rhm_monitors/logic --cov-report=xml:artifacts/coverage.xml --cov-report=term --cov-fail-under=85
ruff check src/rhm_monitors/rhm_monitors pure_tests
mypy --strict src/rhm_monitors/rhm_monitors/logic
bash -n scripts/*.sh
shellcheck scripts/*.sh
cppcheck --enable=warning,style,performance --error-exitcode=1 --suppress=missingIncludeSystem src/rhm_aggregator/src
clang-tidy src/rhm_aggregator/src/*.cpp -- -std=c++17 -Isrc/rhm_aggregator/include || exit 1
