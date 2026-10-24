#!/usr/bin/env bash
# Stall watchdog for VMs started by scripts/vm_startup.sh. A systemd timer runs it every 15 minutes as root
# (see install_watchdog_vm.sh). It reads this run's settings from /etc/genohack-run.env, so it always counts progress
# for the right project list and shard.
#
#   isolate running longer than MAX_ISOLATE_SECONDS (default 1 h; one takes about 15 min) -> kill just that isolate;
#       Snakemake sees the failure and retries it (--retries 2) while the others keep going
#   run not running at two checks in a row, work left -> restart it (counts toward MAX_RESTARTS; progress resets the count)
#   too many restarts without progress -> shut the VM down so a broken run cannot bill all night
#   complete -> upload logs and shut the VM down, once (the startup script normally does this first)
#
# DRY_RUN=1 only prints what it would do. NO_SHUTDOWN=1 never shuts down.
set -uo pipefail
ENV_FILE="${RUN_ENV:-/etc/genohack-run.env}"
if [[ -f "${ENV_FILE}" ]]; then set -a; source "${ENV_FILE}"; set +a; fi
REPO="${REPO:-/home/runner/genohack}"
RUN_USER="${RUN_USER:-runner}"
cd "${REPO}" || exit 1
mkdir -p logs
LOG=logs/watchdog.log
STATE=logs/watchdog_state      # "<done> <epoch of the last change in done>"
RESTARTS=logs/watchdog_restarts
DOWN=logs/watchdog_down        # created the first time the run is seen not running

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "${LOG}"; }
act() { if [[ "${DRY_RUN:-0}" == "1" ]]; then log "DRY RUN: $*"; else "$@"; fi; }
running() { pgrep -f 'snakemak[e]' >/dev/null || pgrep -f 'scripts/run_ful[l].sh' >/dev/null; }
upload_log() { [[ -n "${BUCKET:-}" ]] && act gcloud storage cp "${LOG}" "${BUCKET}/runlogs/$(hostname)/" >/dev/null 2>&1; return 0; }
power_off() {
    upload_log
    [[ "${NO_SHUTDOWN:-0}" == "1" ]] && { log "NO_SHUTDOWN set, not shutting down"; return; }
    act shutdown -h now
}
kill_tree() { local p="$1" c; for c in $(pgrep -P "${p}"); do kill_tree "${c}"; done; act kill -TERM "${p}" 2>/dev/null; return 0; }

progress() {
    sudo -u "${RUN_USER}" env DESIGN_BIOPROJECT="${DESIGN_BIOPROJECT:-}" SHARD_INDEX="${SHARD_INDEX:-0}" \
        SHARD_COUNT="${SHARD_COUNT:-1}" bash scripts/progress.sh
}

start_run() {
    act systemd-run --quiet --unit="genohack-run-$(date +%s)" --uid="${RUN_USER}" --working-directory="${REPO}" \
        --setenv=HOME="/home/${RUN_USER}" --setenv=BUCKET="${BUCKET:-}" --setenv=DESIGN_BIOPROJECT="${DESIGN_BIOPROJECT:-}" \
        --setenv=SHARD_INDEX="${SHARD_INDEX:-0}" --setenv=SHARD_COUNT="${SHARD_COUNT:-1}" --setenv=NO_SHUTDOWN=1 \
        --property=StandardOutput="append:${REPO}/logs/run_full.log" --property=StandardError=inherit \
        bash scripts/run_full.sh
}

read -r done_n total < <(progress)
now=$(date +%s)

if [[ "${total}" -gt 0 && "${done_n}" -ge "${total}" ]]; then
    if [[ ! -f logs/COMPLETE ]]; then
        log "complete (${done_n}/${total}); marking and shutting down"
        touch logs/COMPLETE
        power_off
    fi
    exit 0
fi

if [[ -f "${STATE}" ]]; then read -r last_done last_ts < "${STATE}"; else last_done=-1; last_ts=${now}; fi
if [[ "${done_n}" != "${last_done}" ]]; then
    echo "${done_n} ${now}" > "${STATE}"
    echo 0 > "${RESTARTS}"
    last_ts=${now}
fi
idle=$(( now - last_ts ))

if running; then
    rm -f "${DOWN}"
    killed=0
    # Only this run's isolates: bash scripts/process_isolate.sh <sample> ... with this repo as the working directory.
    while read -r pid secs sample; do
        [[ -n "${pid}" && "${secs}" -gt "${MAX_ISOLATE_SECONDS:-3600}" ]] || continue
        [[ "$(readlink "/proc/${pid}/cwd" 2>/dev/null)" == "${REPO}" ]] || continue
        log "isolate ${sample} has run ${secs}s (limit ${MAX_ISOLATE_SECONDS:-3600}s); killing it so Snakemake retries it"
        kill_tree "${pid}"
        killed=$(( killed + 1 ))
    done < <(ps -eo pid=,etimes=,args= | awk '$3=="bash" && $4 ~ /scripts\/process_isolate\.sh$/ {print $1, $2, $5}')
    log "ok: running, ${done_n}/${total} done, last progress ${idle}s ago, killed ${killed} stuck"
    upload_log
    exit 0
fi

# Not running. The startup script's own loop restarts it between attempts, so act only on the second sighting.
if [[ ! -f "${DOWN}" ]]; then
    touch "${DOWN}"
    log "run is not running at ${done_n}/${total}; will restart it if it is still down at the next check"
    exit 0
fi
n=$(cat "${RESTARTS}" 2>/dev/null || echo 0)
if [[ "${n}" -ge "${MAX_RESTARTS:-3}" ]]; then
    log "giving up: ${n} restarts without progress at ${done_n}/${total}; shutting down to stop billing"
    power_off
    exit 1
fi
echo $(( n + 1 )) > "${RESTARTS}"
echo "${done_n} ${now}" > "${STATE}"
rm -f "${DOWN}"
log "run is down at ${done_n}/${total}; starting it (restart $(( n + 1 )) of ${MAX_RESTARTS:-3})"
start_run
upload_log
