#!/usr/bin/env bash
# Build a BLAST database of genomes an assay must NOT amplify: human, non-tuberculous mycobacteria, and
# common respiratory bacteria. Sequence ids are prefixed with their group (human|ntm|flora) so hits can be
# counted per group. Runs in its own conda env so it never touches the one the main workflow uses.
# Usage: bash scripts/build_offtarget_db.sh [outdir]   (default: ref/offtarget)
set -uo pipefail
out="${1:-ref/offtarget}"
source "${CONDA_BASE:-$HOME/miniforge3}/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx offtarget; then
    conda create -y -n offtarget -c conda-forge -c bioconda blast ncbi-datasets-cli unzip
fi
conda activate offtarget
mkdir -p "${out}/dl"
cd "${out}"

fetch() {  # group name-or-accession mode(taxon|accession)
    local group="$1" what="$2" mode="$3" tag
    tag=$(echo "${what}" | tr ' ' '_')
    [[ -s "dl/${group}_${tag}.fna" ]] && return 0
    if [[ "${mode}" == "taxon" ]]; then
        datasets download genome taxon "${what}" --reference --include genome --filename "dl/${tag}.zip" >/dev/null 2>&1
    else
        datasets download genome accession "${what}" --include genome --filename "dl/${tag}.zip" >/dev/null 2>&1
    fi
    if [[ ! -s "dl/${tag}.zip" ]]; then echo "skipped ${what} (download failed)" >&2; return 0; fi
    unzip -o -q "dl/${tag}.zip" -d "dl/${tag}" && \
        find "dl/${tag}" -name "*.fna" -print0 | xargs -0 cat | awk -v g="${group}" '/^>/{print ">" g "|" substr($0,2); next} 1' > "dl/${group}_${tag}.fna"
    rm -rf "dl/${tag}" "dl/${tag}.zip"
    echo "fetched ${what}: $(grep -c '>' "dl/${group}_${tag}.fna") sequences" >&2
}

fetch human GCF_000001405.40 accession
for t in "Mycobacterium avium" "Mycobacterium intracellulare" "Mycobacterium abscessus" "Mycobacterium kansasii" \
         "Mycobacterium fortuitum" "Mycobacterium smegmatis" "Mycobacterium marinum"; do fetch ntm "${t}" taxon; done
for t in "Streptococcus pneumoniae" "Staphylococcus aureus" "Pseudomonas aeruginosa" "Klebsiella pneumoniae" \
         "Haemophilus influenzae" "Nocardia farcinica"; do fetch flora "${t}" taxon; done

cat dl/*.fna > offtarget.fna
makeblastdb -in offtarget.fna -dbtype nucl -out offtarget -parse_seqids -title offtarget >/dev/null
echo "done: $(grep -c '>' offtarget.fna) sequences, $(du -sh offtarget.* | tail -1 | cut -f1)" >&2
