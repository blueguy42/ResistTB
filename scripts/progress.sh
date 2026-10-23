#!/usr/bin/env bash
# Prints "<done> <total>" for the design set (Bandung): isolates with a DONE marker, and isolates planned.
cd "$(dirname "$0")/.." || exit 1
project="${DESIGN_BIOPROJECT:-PRJNA1433044}"
total=0
done_n=0
for s in $(awk -F'\t' -v p="${project}" 'NR>1 && $2==p {print $1}' data/isolates.tsv); do
    total=$((total + 1))
    [[ -f "results/${s}/DONE" ]] && done_n=$((done_n + 1))
done
echo "${done_n} ${total}"
