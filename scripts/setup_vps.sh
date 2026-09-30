#!/bin/bash
# One-time setup of a fresh Ubuntu 24.04 server for scripts/run_n10.py (run as root).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nauty python3 tmux software-properties-common > /dev/null
if ! apt-get install -y -qq macaulay2 > /dev/null 2>&1; then
  add-apt-repository -y ppa:macaulay2/macaulay2 > /dev/null
  apt-get update -qq
  apt-get install -y -qq macaulay2 > /dev/null
fi
echo "geng: $(command -v nauty-geng || command -v geng)"
echo "M2:   $(M2 --version)"
echo "python: $(python3 --version)"
echo "cores: $(nproc)  memory: $(free -h | awk '/Mem:/ {print $2}')"
