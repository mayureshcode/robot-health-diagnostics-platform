# ADR 0001: Container-first verification
Status: Accepted (implementation unverified)

Use the same Jazzy Dockerfile for local and CI verification. Prefer failing closed to claiming tests pass without ROS runtime evidence. Alternatives: host ROS installation (less reproducible), mock-only testing (cannot validate ROS ABI). The image tag is currently mutable: release hardening requires a verified registry digest.
