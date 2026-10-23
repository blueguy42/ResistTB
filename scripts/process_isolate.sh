#!/usr/bin/env bash
# Process one SRA run: download, subsample, TB-Profiler, snippy, upload small outputs, delete reads.
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

source "$(conda info --base)/etc/profile.d/conda.sh"

# Resume: skip if this isolate is already in the bucket.
if gcloud storage ls "${remote}/DONE" >/dev/null 2>&1; then
    echo "${sample}: already done, skipping" >&2
    exit 0
fi

mkdir -p "${work}" "${out}"
trap 'rm -rf "${work}"' EXIT

conda activate snippy
fasterq-dump "${sample}" -e "${threads}" --split-files --temp "${work}" --outdir "${work}"
pigz -p "${threads}" "${work}"/*.fastq

r1="${work}/${sample}_1.fastq.gz"
r2="${work}/${sample}_2.fastq.gz"
if [[ ! -f "${r1}" || ! -f "${r2}" ]]; then
    echo "${sample}: expected paired reads, got $(ls "${work}")" >&2
    exit 1
fi

rasusa reads --coverage "${coverage}" --genome-size "${genome_size}" --seed 100 \
    -o "${work}/sub_1.fastq.gz" -o "${work}/sub_2.fastq.gz" "${r1}" "${r2}"

snippy --outdir "${work}/snippy" --R1 "${work}/sub_1.fastq.gz" --R2 "${work}/sub_2.fastq.gz" \
    --ref "${ref}" --cpus "${threads}" --force
conda deactivate

conda activate tb-profiler
tb-profiler profile -1 "${work}/sub_1.fastq.gz" -2 "${work}/sub_2.fastq.gz" \
    -p "${sample}" --txt --dir "${work}/tbprofiler" --threads "${threads}"
conda deactivate

# Keep only the small outputs.
cp "${work}/snippy/snps.vcf" "${work}/snippy/snps.aligned.fa" "${work}/snippy/snps.txt" "${out}/"
cp "${work}/tbprofiler/results/${sample}.results.json" "${out}/"
gzip -f "${out}/snps.vcf" "${out}/snps.aligned.fa"

gcloud storage cp -r "${out}/*" "${remote}/"
echo "${sample} $(date -u +%FT%TZ)" > "${out}/DONE"
gcloud storage cp "${out}/DONE" "${remote}/DONE"
echo "${sample}: done" >&2
