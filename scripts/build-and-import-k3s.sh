#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker

sudo docker build -t agent-blueprint-agent:local "$ROOT/images/agent"
sudo docker build -t agent-blueprint-orchestrator:local "$ROOT/images/orchestrator"

sudo docker save agent-blueprint-agent:local | sudo k3s ctr images import -
sudo docker save agent-blueprint-orchestrator:local | sudo k3s ctr images import -
