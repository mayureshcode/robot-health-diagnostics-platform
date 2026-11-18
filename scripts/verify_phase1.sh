#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set +u  # ROS environment hooks may reference unset optional variables.
source /opt/ros/jazzy/setup.bash
set -u
colcon build --packages-select rhm_interfaces --event-handlers console_direct+
set +u  # ROS environment hooks may reference unset optional variables.
source install/setup.bash
set -u
colcon test --packages-select rhm_interfaces --event-handlers console_direct+
colcon test-result --verbose
ros2 interface show rhm_interfaces/msg/HealthStatus
ros2 interface show rhm_interfaces/action/RevalidatePlan
