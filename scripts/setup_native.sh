#!/usr/bin/env bash
# Install local build/test tools on Ubuntu 24.04. Does not replace ROS or change GPU drivers.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$(. /etc/os-release; echo "$ID:$VERSION_ID")" != ubuntu:24.04 ]]; then
  echo 'ERROR: native setup targets Ubuntu 24.04; refusing to install on another OS.' >&2
  exit 2
fi
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo 'ERROR: ROS 2 Jazzy is missing. Install it using the ROS Jazzy Ubuntu deb instructions.' >&2
  exit 2
fi
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3-rosdep python3-colcon-common-extensions python3-pytest python3-pytest-cov \
  python3-hypothesis python3-venv python3-pip python3-yaml \
  python3-flake8 python3-mypy \
  cppcheck clang-tidy shellcheck git \
  ros-jazzy-ament-lint-common ros-jazzy-ament-cmake-gtest
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro jazzy -y
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --disable-pip-version-check --requirement tools/native-requirements.txt
echo 'Native development tools installed. Verify: bash scripts/native_verify.sh'
