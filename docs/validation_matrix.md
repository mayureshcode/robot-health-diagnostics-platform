# Validation matrix — native Ubuntu redesign (not a release)

Status definitions: **Implemented** means source exists. **Verified in native**
requires logs from Ubuntu 24.04 + ROS Jazzy. **Verified in container** and
**Verified in CI** require separate output artifacts. **Simulated** requires an
actual simulation run; **Hardware-validated** requires hardware tests.

| Feature | Implemented | Verified in native (this revision) | Verified in container | Verified in CI | Simulated | Hardware-validated |
|---|---|---|---|---|---|---|
| Phase 0 native setup and gate | Yes (source) | No | No | No | No | No |
| Phase 1 ROS messages/services/action | Yes | No | No | No | No | No |
| Native bringup package | Yes (source) | No | No | No | No | No |
| Phase 2 diff-drive Gazebo simulation | No | No | No | No | No | No |
| Phase 2 ABB IRB120 cell | No | No | No | No | No | No |
| Phase 3 sensor freshness logic/lifecycle | Partial | No | No | No | No | No |
| Phase 3 other mobile and arm monitors | No | No | No | No | No | No |
| Phase 4 C++ aggregation/score/debounce | Partial | No | No | No | No | No |
| Phase 4 fault events and reset | No | No | No | No | No | No |
| ROS native smoke (missing sensors) | Script created | No | No | No | No | No |
| Phase 5-10 Fault manager/dashboard/release | No | No | No | No | No | No |

Historical user-reported evidence **before** this redesign: `colcon build`
reported three packages finished, and the aggregator GoogleTest suite reported
two passing cases. The monitor test package failed with `NO TESTS RAN` / exit
code 5. These previous outcomes **do not verify this changed source revision**.
