#!/usr/bin/env bash
# Keeps the full run alive. A systemd timer runs this every 15 minutes as root (see install_watchdog.sh).
#
#   running and progressing  -> nothing
#   running but no new isolate for STALL_SECONDS (default 50 min; a batch takes about 15) -> restart it
#   not running, not complete -> restart it (counts toward MAX_RESTARTS; progress resets the count)
#   complete (first time)     -> write logs/COMPLETE and shut the VM down, once
#   too many restarts without progress -> shut the VM down so a broken run cannot bill all night
#
# DRY_RUN=1 prints what it would do. NO_SHUTDOWN=1 never shuts down.
set -uo pipefail
REPO="${REPO:-/home/afan/genohack}"
RUN_USER="${RUN_USER:-afan}"
cd "${REPO}" || exit 1
mkdir -p logs
LOG=logs/watchdog.log
STATE=logs/watchdog_state       # "<done> <epoch of the last change in done>"
RESTARTS=logs/watchdog_restarts

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "${LOG}"; }
act() { if [[ "${DRY_RUN:-0}" == "1" ]]; then log "DRY RUN: $*"; else "$@"; fi; }
running() { pgrep -f 'snakemak[e]' >/dev/null; }
power_off() { [[ "${NO_SHUTDOWN:-0}" == "1" ]] && { log "NO_SHUTDOWN set, not shutting down"; return; }; act shutdown -h now; }

stop_run() {
    # Stop the launcher first: its own tail must not run while we tear the rest down.
    act pkill -f 'scripts/run_ful[l].sh'
    act pkill -f 'snakemak[e]'
    act pkill -f 'scripts/process_isolat[e].sh'
    act pkill -f 'fasterq-dum[p]|rasus[a]|snipp[y]|tb-profile[r]|samtool[s]|freebaye[s]|snpEf[f]|delly|vcffilte[r]'
    sleep 3
}

start_run() {
    act systemd-run --quiet --unit="genohack-run-$(date +%s)" --uid="${RUN_USER}" --working-directory="${REPO}" \
        --setenv=HOME="/home/${RUN_USER}" bash scripts/run_full.sh
}

read -r done_n total < <(sudo -u "${RUN_USER}" bash scripts/progress.sh)
now=$(date +%s)

if [[ "${total}" -gt 0 && "${done_n}" -ge "${total}" ]]; then
    if [[ ! -f logs/COMPLETE ]]; then
        log "complete (${done_n}/${total}); marking and shutting down"
        touch logs/COMPLETE
        power_off
    fi
    exit 0
fi

read -r last_done last_ts < "${STATE}" 2>/dev/null || { last_done=-1; last_ts=${now}; }
if [[ "${done_n}" != "${last_done}" ]]; then
    echo "${done_n} ${now}" > "${STATE}"
    echo 0 > "${RESTARTS}"
    last_ts=${now}
fi
idle=$(( now - last_ts ))

if running; then
    if [[ "${idle}" -gt "${STALL_SECONDS:-3000}" ]]; then
        log "stalled: no new isolate for ${idle}s at ${done_n}/${total}; restarting the run"
        stop_run
        echo "${done_n} ${now}" > "${STATE}"
        start_run
    else
        log "ok: running, ${done_n}/${total} done, last progress ${idle}s ago"
    fi
    exit 0
fi

n=$(cat "${RESTARTS}" 2>/dev/null || echo 0)
if [[ "${n}" -ge "${MAX_RESTARTS:-8}" ]]; then
    log "giving up: ${n} restarts without progress at ${done_n}/${total}; shutting down to stop billing"
    power_off
    exit 1
fi
echo $(( n + 1 )) > "${RESTARTS}"
echo "${done_n} ${now}" > "${STATE}"
log "run is not running at ${done_n}/${total}; starting it (restart $(( n + 1 )) of ${MAX_RESTARTS:-8})"
start_run
