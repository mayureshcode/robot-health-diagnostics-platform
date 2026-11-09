# ADR 0003 — Explicit lifecycle management and read-only thresholds

Status: Implemented in source; pending ROS Jazzy runtime verification

## Decision

Use ROS-native lifecycle publishers (`create_lifecycle_publisher` and
`destroy_lifecycle_publisher`) in Python. Activate managed entities via the
parent callbacks, destroy resources on cleanup/error/shutdown, and reconfigure
from scratch. Parameters `warn_age`, `error_age`, `debounce_samples`, and
`stale_timeout` are read-only after startup.

## Why

The original sensor monitor created an ordinary publisher and then attempted
lifecycle activation; Python rclpy Jazzy requires the explicit managed
publisher constructor. The original update callbacks accepted parameter
changes without updating cached limits, which could cause the parameter
server and effective logic to disagree.

## Alternatives

- Dynamic parameter updates: possible with post-set callbacks/atomic state
  updates but increases concurrency and validation complexity; deferred.
- Always-active publisher: simpler but violates the operator-managed lifecycle
  requirement.

## Risks

ROS clock discontinuities, publisher cleanup/reconfiguration and lifecycle
state transitions require verification on the actual Jazzy runtime. The
`test_lifecycle.py` regression suite and `native_smoke.sh` are proposed gates;
these tests have not been run on the modified code in this sandbox.
