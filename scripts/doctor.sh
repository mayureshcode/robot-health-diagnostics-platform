#!/usr/bin/env bash
set -u
check(){ printf '%-18s' "$1"; shift; if "$@" >/dev/null 2>&1; then echo OK; else echo MISSING; fi; }
check Docker command -v docker
check 'Docker daemon' docker info
check 'NVIDIA GPU' nvidia-smi
check 'Display variable' test -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}"
check 'GitHub CLI' command -v gh
check 'GitHub auth' gh auth status
cat <<'EOF'
Fix commands (Ubuntu 24.04):
  sudo apt-get update && sudo apt-get install -y docker.io git gh
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"  # log out/in before retrying
  gh auth login
For headless CI, DISPLAY and NVIDIA GPU are optional.
EOF
