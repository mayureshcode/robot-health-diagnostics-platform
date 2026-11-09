#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rhm_interfaces --event-handlers console_direct+
source install/setup.bash
colcon test --packages-select rhm_interfaces --event-handlers console_direct+
colcon test-result --verbose
ros2 interface show rhm_interfaces/msg/HealthStatus
ros2 interface show rhm_interfaces/action/RevalidatePlan
