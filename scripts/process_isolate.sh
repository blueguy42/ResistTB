#!/usr/bin/env bash
# Process one SRA run: download, subsample, TB-Profiler, snippy, upload small outputs, delete reads.
# Writes results/<sample>/metadata.json with per-step durations, input sizes and tool versions.
# Usage: BUCKET=gs://... bash scripts/process_isolate.sh SRR... [threads] [coverage]
set -euo pipefail

sample="$1"
threads="${2:-8}"
coverage="${3:-100}"
bucket="${BUCKET:?set BUCKET, e.g. gs://haduh-512512-genohack}"
ref="${REF:-ref/NC_000962.3.fasta}"
genome_size="4.4mb"

work="work/${sample}"
out="results/${sample}"
remote="${bucket}/results/${sample}"

source "${CONDA_BASE:-$HOME/miniforge3}/etc/profile.d/conda.sh"

# Resume: skip if this isolate is already in the bucket.
if gcloud storage ls "${remote}/DONE" >/dev/null 2>&1; then
    echo "${sample}: already done, skipping" >&2
    exit 0
fi

mkdir -p "${work}" "${out}"
trap 'rm -rf "${work}"' EXIT

# Step timing: lap <name> stores seconds since the previous lap.
declare -A dur
start_utc=$(date -u +%FT%TZ)
t_start=$(date +%s)
t_prev=${t_start}
lap() {
    local now
    now=$(date +%s)
    dur[$1]=$((now - t_prev))
    t_prev=${now}
}

r1="${work}/${sample}_1.fastq.gz"
r2="${work}/${sample}_2.fastq.gz"

# Preferred: ENA serves ready-made gzipped FASTQ, so there is no SRA conversion or compression.
download_ena() {
    local urls u
    urls=$(curl -fsS "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=${sample}&result=read_run&fields=fastq_ftp&format=tsv&download=true" \
        | tail -n +2 | cut -f2 | tr ';' '\n' | grep -E '_[12]\.fastq\.gz$' || true)
    [[ -n "${urls}" ]] || return 1
    local pids=() rc=0 p
    for u in ${urls}; do
        # -C - resumes a dropped transfer instead of restarting it.
        # --speed-limit/--speed-time abort a stalled connection (under 20 kB/s for 60 s) so it retries.
        curl -fsS --retry 5 --retry-delay 5 --retry-all-errors -C - \
            --connect-timeout 30 --speed-limit 20000 --speed-time 60 \
            -o "${work}/$(basename "${u}")" "https://${u}" &
        pids+=($!)
    done
    for p in "${pids[@]}"; do wait "${p}" || rc=1; done
    [[ ${rc} -eq 0 && -s "${r1}" && -s "${r2}" ]] || return 1
    # A truncated gzip passes the size check, so test integrity before using it.
    gzip -t "${r1}" & pids=($!)
    gzip -t "${r2}" & pids+=($!)
    for p in "${pids[@]}"; do wait "${p}" || return 1; done
}

conda activate snippy
dur[compress]=0
# ENA is opt-in (DOWNLOAD_SOURCE=ena): from Singapore its connections stalled repeatedly and the
# server does not support resuming, so the SRA path is the default.
if [[ "${DOWNLOAD_SOURCE:-sra}" == "ena" ]] && download_ena; then
    dl_source="ena"
    lap download
else
    [[ "${DOWNLOAD_SOURCE:-sra}" == "ena" ]] && echo "${sample}: ENA download failed, falling back to fasterq-dump" >&2
    dl_source="sra"
    rm -f "${work}"/*.fastq.gz
    fasterq-dump "${sample}" -e "${threads}" --split-files --temp "${work}" --outdir "${work}"
    lap download
    # Leave the reads uncompressed: rasusa reads plain FASTQ and writes the small subsample gzipped.
    # Compressing the full-size reads took 5-10 minutes per isolate in the 3-isolate test.
    r1="${work}/${sample}_1.fastq"
    r2="${work}/${sample}_2.fastq"
fi

if [[ ! -f "${r1}" || ! -f "${r2}" ]]; then
    echo "${sample}: expected paired reads, got $(ls "${work}")" >&2
    exit 1
fi
bytes_raw=$(( $(stat -c %s "${r1}") + $(stat -c %s "${r2}") ))

rasusa reads --coverage "${coverage}" --genome-size "${genome_size}" --seed 100 \
    -o "${work}/sub_1.fastq.gz" -o "${work}/sub_2.fastq.gz" "${r1}" "${r2}"
lap subsample
bytes_sub=$(( $(stat -c %s "${work}/sub_1.fastq.gz") + $(stat -c %s "${work}/sub_2.fastq.gz") ))

snippy --outdir "${work}/snippy" --R1 "${work}/sub_1.fastq.gz" --R2 "${work}/sub_2.fastq.gz" \
    --ref "${ref}" --cpus "${threads}" --force
lap snippy
# Version capture must never abort the run, so every pipeline here is guarded with || true.
ver_snippy=$(snippy --version 2>&1 | head -1 || true)
ver_rasusa=$(rasusa --version 2>&1 | head -1 || true)
ver_sra=$(fasterq-dump --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
conda deactivate

conda activate tb-profiler
tb-profiler profile -1 "${work}/sub_1.fastq.gz" -2 "${work}/sub_2.fastq.gz" \
    -p "${sample}" --txt --dir "${work}/tbprofiler" --threads "${threads}"
lap tbprofiler
ver_tbp=$(tb-profiler version 2>&1 | head -1 || true)
conda deactivate

# Keep only the small outputs.
cp "${work}/snippy/snps.vcf" "${work}/snippy/snps.aligned.fa" "${work}/snippy/snps.txt" "${out}/"
cp "${work}/tbprofiler/results/${sample}.results.json" "${out}/"
gzip -f "${out}/snps.vcf" "${out}/snps.aligned.fa"

# Source metadata row from the isolate list, if present (header-aware, tab-separated).
src_meta="{}"
if [[ -f data/isolates.tsv ]]; then
    src_meta=$(awk -F'\t' -v s="${sample}" 'NR==1{for(i=1;i<=NF;i++)h[i]=$i;next} $1==s{
        printf "{"; for(i=1;i<=NF;i++){gsub(/"/,"\\\"",$i); printf "%s\"%s\":\"%s\"", (i>1?",":""), h[i], $i} printf "}"}' \
        data/isolates.tsv)
    [[ -n "${src_meta}" ]] || src_meta="{}"
fi

write_metadata() {
    local end_utc total
    end_utc=$(date -u +%FT%TZ)
    total=$(( $(date +%s) - t_start ))
    cat > "${out}/metadata.json" <<EOF
{
  "sample": "${sample}",
  "source": ${src_meta},
  "run": {
    "start_utc": "${start_utc}",
    "end_utc": "${end_utc}",
    "machine_type": "$(curl -s -m 2 -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/machine-type 2>/dev/null | awk -F/ '{print $NF}')",
    "download_source": "${dl_source}",
    "threads": ${threads},
    "target_coverage": ${coverage},
    "genome_size": "${genome_size}"
  },
  "duration_seconds": {
    "download": ${dur[download]},
    "compress": ${dur[compress]},
    "subsample": ${dur[subsample]},
    "snippy": ${dur[snippy]},
    "tbprofiler": ${dur[tbprofiler]},
    "upload": ${dur[upload]:-0},
    "total": ${total}
  },
  "input_bytes": { "raw_fastq": ${bytes_raw}, "subsampled_fastq_gz": ${bytes_sub} },
  "tool_versions": {
    "snippy": "${ver_snippy}", "tb-profiler": "${ver_tbp}",
    "rasusa": "${ver_rasusa}", "sra-tools": "${ver_sra}"
  }
}
EOF
}

# Upload data, then rewrite metadata with the upload time included and upload it last.
write_metadata
gcloud storage cp -r "${out}/*" "${remote}/"
lap upload
write_metadata
gcloud storage cp "${out}/metadata.json" "${remote}/metadata.json"
echo "${sample} $(date -u +%FT%TZ)" > "${out}/DONE"
gcloud storage cp "${out}/DONE" "${remote}/DONE"
echo "${sample}: done in $(( $(date +%s) - t_start ))s" >&2
