#!/usr/bin/env bash
# Pull finished per-isolate results from the bucket (works on the VM or a laptop with gcloud).
set -euo pipefail
bucket="${BUCKET:-gs://haduh-512512-genohack}"
mkdir -p results
gcloud storage rsync -r "${bucket}/results" results
