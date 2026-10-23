#!/usr/bin/env bash
# Run the full Bandung workflow detached from any terminal, then shut the VM down.
# Usage: nohup setsid bash scripts/run_full.sh > logs/run_full.log 2>&1 &
# The shutdown runs whether the workflow succeeds or fails, to stop compute billing.
# Disk and bucket results are kept. Restart the VM and rerun this script to resume.
cd "$(dirname "$0")/.." || exit 1
source "${CONDA_BASE:-$HOME/miniforge3}/etc/profile.d/conda.sh"
conda activate design
export BUCKET="${BUCKET:-gs://haduh-512512-genohack}"
mkdir -p logs

echo "start $(date -u +%FT%TZ) on $(nproc) vCPUs"
# 4 isolates at once, 4 threads each (config: threads_per_isolate), 2 retries per isolate.
snakemake -s workflow/Snakefile --cores "$(nproc)" --keep-going --retries 2 --latency-wait 30 --rerun-incomplete
rc=$?
echo "snakemake exit=${rc} at $(date -u +%FT%TZ)"

if [[ "${NO_SHUTDOWN:-0}" != "1" ]]; then
    echo "shutting down the VM"
    sudo shutdown -h now
fi
