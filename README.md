# Failure-Aware Robot Health & Diagnostics Platform

**Batch A: UNVERIFIED development source; not production ready.**

## Verify in a ROS 2 Jazzy container

```bash
bash scripts/docker_verify.sh
```

This builds a ROS Jazzy image and runs rosdep, colcon build/test, Python tests and static analysis. Requires Docker Engine and network access. Logs appear in `artifacts/`.

**Scope actually written:** Phase 0 verification harness, Phase 1 ROS interface definitions, one Phase 3 lifecycle sensor freshness monitor, and a partial Phase 4 lifecycle aggregator. **Missing:** Phase 2 Gazebo assets, most Phase 3 monitors, fault-event generation, latching/reset, integration tests, verified performance, dashboard, arm monitoring and hardware tests. A successful build is necessary but insufficient for acceptance.

**Container reproducibility limitation:** The base image currently uses a mutable tag rather than a pinned digest. A verified digest is required before release.

No benchmark numbers or runtime claims are made. See [validation matrix](docs/validation_matrix.md), [QoS](docs/qos.md), [runbook](docs/runbook.md), and [ADR](docs/adr/0001-container-gate.md).
