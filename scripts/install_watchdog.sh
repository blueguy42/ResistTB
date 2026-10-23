#!/usr/bin/env bash
# Install the 15-minute watchdog as a systemd timer. Run once on the VM: sudo bash scripts/install_watchdog.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="${SUDO_USER:-afan}"

cat > /etc/systemd/system/genohack-watchdog.service <<EOF
[Unit]
Description=Keep the genohack full run alive
[Service]
Type=oneshot
Environment=REPO=${REPO}
Environment=RUN_USER=${RUN_USER}
ExecStart=/bin/bash ${REPO}/scripts/watchdog.sh
EOF

cat > /etc/systemd/system/genohack-watchdog.timer <<EOF
[Unit]
Description=Run the genohack watchdog every 15 minutes
[Timer]
OnBootSec=3min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now genohack-watchdog.timer
systemctl list-timers genohack-watchdog.timer --no-pager
