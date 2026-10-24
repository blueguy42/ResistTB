#!/usr/bin/env bash
# Install the 15-minute stall watchdog on a VM run by scripts/vm_startup.sh. Run once as root:
#   sudo bash scripts/install_watchdog_vm.sh [env file to copy to /etc/genohack-run.env]
# The env file holds this run's settings: REPO, RUN_USER, BUCKET, DESIGN_BIOPROJECT, SHARD_INDEX, SHARD_COUNT.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -n "${1:-}" ]]; then install -m 644 "$1" /etc/genohack-run.env; fi
[[ -f /etc/genohack-run.env ]] || { echo "missing /etc/genohack-run.env"; exit 1; }

cat > /etc/systemd/system/genohack-watchdog.service <<EOF
[Unit]
Description=Kill stuck isolates and restart a dead genohack run
[Service]
Type=oneshot
ExecStart=/bin/bash ${REPO}/scripts/watchdog_vm.sh
EOF

cat > /etc/systemd/system/genohack-watchdog.timer <<EOF
[Unit]
Description=Run the genohack watchdog every 15 minutes
[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now genohack-watchdog.timer
systemctl list-timers genohack-watchdog.timer --no-pager
