#!/usr/bin/env bash
# Activate independently-launched lifecycle nodes (run after source install/setup.bash).
set -Eeuo pipefail
for node in /rhm_sensor_monitor /rhm_aggregator; do
  echo "Configuring ${node}"
  timeout 15 ros2 lifecycle set "$node" configure
  echo "Activating ${node}"
  timeout 15 ros2 lifecycle set "$node" activate
  state="$(timeout 10 ros2 lifecycle get "$node")"
  echo "${node}: ${state}"
  if [[ "$state" != *active* ]]; then
    echo "ERROR: $node is not active" >&2
    exit 1
  fi
done
