# Verification runbook

Run `bash scripts/doctor.sh` to diagnose host prerequisites, then `bash scripts/docker_verify.sh`.
Logs are written to `artifacts/docker_verify.log` and `artifacts/inside_verify.log`.
If the image cannot be built, check Docker daemon and registry connectivity. If `rosdep` fails, inspect the first missing dependency. If a ROS interface fails compilation, do not proceed to simulation. The nightly job currently deliberately fails because a real headless integration test is not yet implemented.
