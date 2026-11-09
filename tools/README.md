# Native development dependencies

Run `bash scripts/setup_native.sh` on Ubuntu 24.04 to install OS-managed tools and the
isolated, pinned `.venv` tooling. ROS runtime packages stay under `/opt/ros/jazzy`.
Do not replace system Python or use `sudo pip` for ROS packages. A clean native
verification is `bash scripts/native_verify.sh`; no container is used.
