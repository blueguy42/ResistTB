#!/usr/bin/env bash
# Build data/isolates.tsv (all Indonesian MTB Illumina WGS runs) and report counts per BioProject.
set -euo pipefail
mkdir -p data
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate duckdb
duckdb -f sql/indonesia_isolates.sql
echo "runs per BioProject:"
tail -n +2 data/isolates.tsv | cut -f2 | sort | uniq -c | sort -rn
