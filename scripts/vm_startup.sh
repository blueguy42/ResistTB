#!/usr/bin/env bash
# GCE startup script: set up one VM and process its share of isolates with no one logged in.
# Passed with: gcloud compute instances create ... --metadata-from-file startup-script=scripts/vm_startup.sh
# Instance metadata it reads: BUNDLE (gs:// tarball of scripts/ workflow/ envs/ resources/), BUCKET (gs://...),
# DESIGN_BIOPROJECT (comma list), SHARD_INDEX, SHARD_COUNT, optional MAX_HOURS (hard stop, default 14).
# Progress: results go to $BUCKET/results; logs are copied to $BUCKET/runlogs/<vm name>/ every 10 minutes.
# The VM shuts itself down when its share is done, or after MAX_HOURS whatever happens.
set -uo pipefail

meta() { curl -fs -H 'Metadata-Flavor: Google' "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1" || true; }
VM="$(curl -fs -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/name)"
BUNDLE="$(meta BUNDLE)"; BUCKET="$(meta BUCKET)"; PROJECTS="$(meta DESIGN_BIOPROJECT)"
SHARD_INDEX="$(meta SHARD_INDEX)"; SHARD_COUNT="$(meta SHARD_COUNT)"; MAX_HOURS="$(meta MAX_HOURS)"
MAX_HOURS="${MAX_HOURS:-14}"
LOG=/var/log/genohack_startup.log
exec >>"${LOG}" 2>&1
echo "== startup $(date -u +%FT%TZ) on ${VM}: projects=${PROJECTS} shard=${SHARD_INDEX}/${SHARD_COUNT} max_hours=${MAX_HOURS}"

# Hard stop, so a broken run cannot bill all night. Reboots re-run this script, so only arm it once per boot.
shutdown -h "+$((MAX_HOURS * 60))" "genohack: max run time reached" || true

id runner >/dev/null 2>&1 || useradd -m -s /bin/bash runner
echo "runner ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/runner
chmod 440 /etc/sudoers.d/runner
HOME_DIR=/home/runner
REPO=${HOME_DIR}/genohack

if [[ ! -d "${REPO}/scripts" ]]; then
    mkdir -p "${REPO}"
    gcloud storage cp "${BUNDLE}" /tmp/bundle.tgz && tar -xzf /tmp/bundle.tgz -C "${REPO}"
    chown -R runner:runner "${HOME_DIR}"
fi
mkdir -p "${REPO}/data" "${REPO}/logs"
cp "${REPO}/resources/isolates_extra.tsv" "${REPO}/data/isolates.tsv"
chown -R runner:runner "${REPO}"

# Settings for the stall watchdog (scripts/watchdog_vm.sh), which runs from a systemd timer with no environment of its own.
cat > /etc/genohack-run.env <<EOF
REPO=${REPO}
RUN_USER=runner
BUCKET=${BUCKET}
DESIGN_BIOPROJECT=${PROJECTS}
SHARD_INDEX=${SHARD_INDEX:-0}
SHARD_COUNT=${SHARD_COUNT:-1}
EOF
bash "${REPO}/scripts/install_watchdog_vm.sh" || echo "watchdog install failed (the run continues without it)"

# Copy logs to the bucket every 10 minutes (a background loop, so it also covers a crash).
( while true; do
    gcloud storage cp "${LOG}" "${REPO}/logs/run_full.log" "${BUCKET}/runlogs/${VM}/" >/dev/null 2>&1
    sleep 600
  done ) &

run_as_runner() {
    sudo -u runner -H env BUCKET="${BUCKET}" DESIGN_BIOPROJECT="${PROJECTS}" SHARD_INDEX="${SHARD_INDEX:-0}" \
        SHARD_COUNT="${SHARD_COUNT:-1}" NO_SHUTDOWN=1 bash -lc "cd ${REPO} && $*"
}

echo "== setup $(date -u +%FT%TZ)"
run_as_runner "bash scripts/setup_vm.sh" || { echo "setup failed"; gcloud storage cp "${LOG}" "${BUCKET}/runlogs/${VM}/" || true; exit 1; }

for attempt in 1 2 3; do
    echo "== run attempt ${attempt} $(date -u +%FT%TZ)"
    run_as_runner "bash scripts/run_full.sh >> logs/run_full.log 2>&1"
    read -r done_n total < <(run_as_runner "bash scripts/progress.sh")
    echo "progress ${done_n}/${total}"
    [[ "${done_n}" -ge "${total}" && "${total}" -gt 0 ]] && break
done

gcloud storage cp "${LOG}" "${REPO}/logs/run_full.log" "${BUCKET}/runlogs/${VM}/" || true
if [[ "${done_n:-0}" -ge "${total:-1}" && "${total:-0}" -gt 0 ]]; then
    echo "== complete $(date -u +%FT%TZ): shutting down"
    gcloud storage cp "${LOG}" "${BUCKET}/runlogs/${VM}/" || true
    shutdown -h now
else
    echo "== incomplete: leaving the VM up for inspection; the hard stop will shut it down"
fi
