# Build with --build-arg ROS_BASE_IMAGE=<digest-pinned image> for immutable builds.
ARG ROS_BASE_IMAGE=osrf/ros:jazzy-desktop-full
FROM ${ROS_BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive ROS_DISTRO=jazzy
RUN apt-get update && apt-get install -y --no-install-recommends \
 python3-rosdep python3-colcon-common-extensions python3-pytest python3-pytest-cov \
 python3-hypothesis \
 python3-flake8 python3-pip python3-venv python3-mypy python3-yaml \
 cppcheck clang-tidy shellcheck git curl jq ca-certificates \
 ros-jazzy-ros-gz ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
 ros-jazzy-moveit ros-jazzy-robot-localization ros-jazzy-xacro \
 ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
 ros-jazzy-diagnostic-updater ros-jazzy-lifecycle-msgs \
 ros-jazzy-ament-lint-auto ros-jazzy-ament-lint-common && \
 rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/rhm-venv && \
 /opt/rhm-venv/bin/pip install --no-cache-dir \
 ruff==0.8.6 hypothesis==6.122.3 coverage==7.6.10 mypy==1.14.1 \
 yamllint==1.35.1
ENV PATH=/opt/rhm-venv/bin:$PATH
WORKDIR /workspace
COPY . /workspace
ENTRYPOINT ["/bin/bash", "-lc"]
