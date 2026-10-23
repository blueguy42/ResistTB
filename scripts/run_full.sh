#!/usr/bin/env bash
# Run the full Bandung workflow once. Detached launch: setsid nohup bash scripts/run_full.sh > logs/run_full.log 2>&1 &
# Normally started and restarted by scripts/watchdog.sh, which also stops the run from silently dying overnight.
#
# Shutdown rule: the VM shuts down ONLY when every isolate is done (to stop compute billing). If Snakemake
# ends early, the VM stays up so the watchdog can restart the run. Set NO_SHUTDOWN=1 to never shut down.
cd "$(dirname "$0")/.." || exit 1
source "${CONDA_BASE:-$HOME/miniforge3}/etc/profile.d/conda.sh"
conda activate design
export BUCKET="${BUCKET:-gs://haduh-512512-genohack}"
mkdir -p logs

echo "start $(date -u +%FT%TZ) on $(nproc) vCPUs"
# Leftovers from an interrupted run: nothing else is running here, so clear partial work and stale locks.
rm -rf work/*
snakemake -s workflow/Snakefile --unlock >/dev/null 2>&1 || true

# Isolates run mostly I/O-bound, so a little oversubscription uses idle CPU: with 3 threads per isolate
# (config: threads_per_isolate), cores = nproc + 2 allows 6 isolates at once on 16 vCPUs.
CORES="${CORES:-$(( $(nproc) + 2 ))}"
snakemake -s workflow/Snakefile --cores "${CORES}" --keep-going --retries 2 --latency-wait 30 --rerun-incomplete
rc=$?

read -r done_n total < <(bash scripts/progress.sh)
echo "snakemake exit=${rc} at $(date -u +%FT%TZ): ${done_n}/${total} isolates done"
if [[ "${done_n}" -ge "${total}" && "${total}" -gt 0 ]]; then
    touch logs/COMPLETE
    if [[ "${NO_SHUTDOWN:-0}" != "1" ]]; then
        echo "complete: shutting down the VM"
        sudo shutdown -h now
    fi
else
    echo "incomplete: leaving the VM up so the watchdog can restart the run"
fi
