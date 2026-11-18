# Validation matrix — native Ubuntu + Phase 2A mobile simulation (not a release)

Status definitions: **Implemented** means source exists. **Verified in native**
requires logs from Ubuntu 24.04 + ROS Jazzy. **Verified in container** and
**Verified in CI** require separate output artifacts. **Simulated** requires an
actual simulation run; **Hardware-validated** requires hardware tests.

| Feature | Implemented | Verified in native (this revision) | Verified in container | Verified in CI | Simulated | Hardware-validated |
|---|---|---|---|---|---|---|
| Phase 0 native setup and gate | Yes (source) | No | No | No | No | No |
| Phase 1 ROS messages/services/action | Yes | No | No | No | No | No |
| Native bringup package | Yes (source) | No | No | No | No | No |
| Phase 2A diff-drive model/world/bridge/EKF | Yes (source) | No | No | No | No | No |
| Phase 2B ABB IRB120 cell | No | No | No | No | No | No |
| Phase 3 sensor freshness logic/lifecycle | Partial | No | No | No | No | No |
| Phase 3 other mobile and arm monitors | No | No | No | No | No | No |
| Phase 4 C++ aggregation/score/debounce | Partial | No | No | No | No | No |
| Phase 4 fault events and reset | No | No | No | No | No | No |
| ROS native smoke (missing sensors) | Yes | User-reported pass (log excerpt) | No | No | No | No |
| Gazebo mobile headless smoke | Yes (source) | No | No | No | No | No |
| Phase 5-10 Fault manager/dashboard/release | Partial | No | No | No | No | No |

Historical user-reported evidence **before** this redesign: `colcon build`
reported three packages finished, and the aggregator GoogleTest suite reported
two passing cases. The monitor test package failed with `NO TESTS RAN` / exit
code 5. These previous outcomes **do not verify this changed source revision**.

Phase 2A source/static checks run in a non-ROS authoring sandbox are **not**
counted as ROS or simulation verification. Native Gazebo test evidence is
pending `bash scripts/run_native.sh --verify-sim` on Ubuntu.

## Surveillance observer branch — pending Ubuntu integration

| Feature | Implemented | Verified in native | Verified in CI | Simulated | Hardware-validated |
|---|---|---|---|---|---|
| Configurable PointCloud2/IMU/odom adapter | Yes (source) | No | No | No | No |
| Node-presence diagnostics (not lifecycle) | Yes (source) | No | No | No | No |
| FastAPI read-only dashboard / WebSocket | Yes (source) | No | No | No | No |
| Token authentication and CORS restriction | Yes (source) | No | No | No | No |
| Offline pure-logic/API contract tests | Yes (source) | No (sandbox only) | No | No | No |
| Battery/motor/arm health | No | No | No | No | No |

No runtime numbers from the new branch are benchmarked. No hardware tests performed.

### Surveillance lifecycle repair (pending target environment verification)

- Observed on native Ubuntu: ROS adapter configure succeeded, activate failed,
  lifecycle state `unconfigured [1]` (operator log; failure evidence).
- Cause identified from source: lifecycle publisher activated without the
  required `state` argument. Fixed via parent lifecycle callbacks; **unverified
  on Ubuntu until `colcon test` and live launch are rerun**.
- Authoring sandbox: 19 non-ROS source/API tests passed (exit 0); Python syntax,
  Bash syntax, patch whitespace checks passed (exit 0).
- Hardware validated: **No**.
