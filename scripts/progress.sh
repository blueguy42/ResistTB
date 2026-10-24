#!/usr/bin/env bash
# Prints "<done> <total>" for this run's isolates: those with a DONE marker, and those planned.
# DESIGN_BIOPROJECT can be a comma-separated list; SHARD_INDEX / SHARD_COUNT select this VM's share (see workflow/Snakefile).
cd "$(dirname "$0")/.." || exit 1
project="${DESIGN_BIOPROJECT:-PRJNA1433044}"
total=0
done_n=0
for s in $(awk -F'\t' -v p="${project}" -v n="${SHARD_COUNT:-1}" -v k="${SHARD_INDEX:-0}" \
    'BEGIN{m=split(p,a,","); for(i=1;i<=m;i++) want[a[i]]=1} NR>1 && ($2 in want){ if ((c++ % n)==k) print $1 }' data/isolates.tsv); do
    total=$((total + 1))
    [[ -f "results/${s}/DONE" ]] && done_n=$((done_n + 1))
done
echo "${done_n} ${total}"
