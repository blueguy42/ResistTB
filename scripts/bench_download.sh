#!/usr/bin/env bash
# Time a download-only run of one SRA run by one method, with nothing else running.
# Usage: bash scripts/bench_download.sh SRR... ena|sra [timeout_seconds]
set -uo pipefail

sample="$1"
method="$2"
limit="${3:-1200}"
work="work/bench_${sample}_${method}"
rm -rf "${work}"
mkdir -p "${work}"
source "$(conda info --base)/etc/profile.d/conda.sh"

fetch_ena() {
    local urls u
    urls=$(curl -fsS "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${sample}&result=read_run&fields=fastq_ftp&format=tsv&download=true" \
        | tail -n +2 | cut -f2 | tr ';' '\n' | grep -E '_[12]\.fastq\.gz$')
    for u in ${urls}; do
        # No retries on purpose: this measures the raw connection, not the retry logic.
        curl -fsS --connect-timeout 30 --speed-limit 20000 --speed-time 60 \
            -o "${work}/$(basename "${u}")" "https://${u}" &
    done
    wait
}

fetch_sra() {
    conda activate snippy
    fasterq-dump "${sample}" -e 4 --split-files --temp "${work}" --outdir "${work}"
    pigz -p 4 "${work}"/*.fastq
}

start=$(date +%s)
if [[ "${method}" == "ena" ]]; then
    export -f fetch_ena; export sample work
    timeout "${limit}" bash -c fetch_ena
else
    export -f fetch_sra; export sample work
    timeout "${limit}" bash -c "source \"$(conda info --base)/etc/profile.d/conda.sh\"; fetch_sra"
fi
rc=$?
end=$(date +%s)
secs=$((end - start))
bytes=$(du -cb "${work}"/*.fastq.gz 2>/dev/null | tail -1 | cut -f1)
bytes=${bytes:-0}
echo "RESULT sample=${sample} method=${method} exit=${rc} seconds=${secs} bytes=${bytes} MB_per_s=$(awk -v b="${bytes}" -v s="${secs}" 'BEGIN{printf "%.2f", b/1e6/s}')"
rm -rf "${work}"
