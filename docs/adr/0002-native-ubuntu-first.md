# ADR 0002 — Native Ubuntu first; Docker for reproducibility

Status: Accepted for development (not yet runtime-verified)

## Decision

Use Ubuntu 24.04 + ROS 2 Jazzy deb packages as the primary build/test/debug
path. The operator launches Gazebo Harmonic and robotics components natively.
Retain Docker-based verification in CI as a supplementary reproducibility
gate; do not require local Docker to iterate.

## Rationale

The development host already has ROS Jazzy, Gazebo Harmonic, Nav2, MoveIt 2,
colcon and Python 3.12 installed. Requiring a large desktop ROS image added
avoidable driver, GUI, network and authentication dependencies and prevented
use of the host's working hardware-accelerated GUI.

## Alternatives

- Docker only: reproducible but high-friction on this host; retained in CI.
- Host only: simple but cannot independently validate build reproducibility;
  rejected for release.
- Conda ROS environment: can conflict with apt-managed ROS Python/C++
  extensions; rejected for this workspace.

## Consequences

Native build and tests are evidence of **native** verification only. CI green,
headless Gazebo, MoveIt planning, Docker clean clone, and hardware validation
remain separate gated claims. This ADR supersedes container-first development
in ADR 0001, not the need for release CI verification.
