#!/usr/bin/env bash
# Read-only diagnostics for native Ubuntu development environment.
set -Eeuo pipefail
printf '\n=== Native RHM host doctor ===\n'
# shellcheck source=/dev/null
. /etc/os-release
printf 'OS: %s %s\n' "$ID" "$VERSION_ID"
if [[ "$ID:$VERSION_ID" != 'ubuntu:24.04' ]]; then
  echo 'WARNING: the supported host baseline is Ubuntu 24.04.'
fi
check() {
  local description="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '%-27s OK\n' "$description"
  else
    printf '%-27s MISSING / INACTIVE\n' "$description"
  fi
}
check 'ROS 2 Jazzy' test -f /opt/ros/jazzy/setup.bash
check 'Colcon' command -v colcon
check 'ROS dependency resolver' command -v rosdep
check 'Gazebo Harmonic CLI' command -v gz
check 'C++ compiler' command -v g++
check 'Python 3' command -v python3
check 'Ruff (local venv)' test -x .venv/bin/ruff
check 'Mypy (local venv)' test -x .venv/bin/mypy
check 'C++ analysis' command -v cppcheck
check 'Lifecycle CLI' bash -c 'source /opt/ros/jazzy/setup.bash && ros2 lifecycle --help'
check 'NVIDIA GPU (optional)' command -v nvidia-smi
check 'GUI display (optional)' test -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}"
check 'Git (local versioning)' command -v git
check 'GitHub CLI (optional)' command -v gh
if command -v gh >/dev/null 2>&1; then
  check 'GitHub login (optional)' gh auth status
fi
printf '\nFix missing development tools: bash scripts/setup_native.sh\n'
printf 'Run native verification: bash scripts/native_verify.sh\n'
printf 'Docker is optional; native colcon and ROS graph tests are primary on this host.\n'
