#!/usr/bin/env bash
# shellcheck disable=SC1091
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
IMAGE="${RHM_IMAGE:-rhm-jazzy-batch-a}"
LOG="artifacts/docker_verify.log"
exec > >(tee "$LOG") 2>&1
trap 'rc=$?; echo "VERIFY_EXIT_CODE=$rc"; exit "$rc"' EXIT
if ! command -v docker >/dev/null; then echo 'ERROR: docker unavailable. Install Docker Engine and rerun.' >&2; exit 127; fi
if ! docker info >/dev/null 2>&1; then echo 'ERROR: Docker daemon inaccessible. Start Docker or fix permissions.' >&2; exit 126; fi
docker build --progress=plain --build-arg "ROS_BASE_IMAGE=${ROS_BASE_IMAGE:-osrf/ros:jazzy-desktop-full}" -t "$IMAGE" .
docker run --rm -e CI=1 -v "$PWD/artifacts:/workspace/artifacts" "$IMAGE" 'bash scripts/verify_inside.sh'
