#!/usr/bin/env bash
# One-time setup on the Debian VM: system packages, Miniforge, conda envs, reference files.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y git curl wget build-essential unzip

if [[ ! -d "${HOME}/miniforge3" ]]; then
    curl -fsSL -o /tmp/miniforge.sh \
        "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-$(uname -m).sh"
    bash /tmp/miniforge.sh -b -p "${HOME}/miniforge3"
    "${HOME}/miniforge3/bin/conda" init bash
fi
source "${HOME}/miniforge3/etc/profile.d/conda.sh"

for env in snippy tbprofiler duckdb design; do
    name=$(grep '^name:' "envs/${env}.yml" | awk '{print $2}')
    if conda env list | awk '{print $1}' | grep -qx "${name}"; then
        echo "env ${name} exists, skipping"
    else
        conda env create -f "envs/${env}.yml"
    fi
done

# H37Rv reference (NC_000962.3) from NCBI.
mkdir -p ref data
if [[ ! -s ref/NC_000962.3.fasta ]]; then
    curl -fsSL "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NC_000962.3&rettype=fasta&retmode=text" \
        -o ref/NC_000962.3.fasta
fi

# Low-confidence region mask used by the Nextstrain TB build (Marin et al. 2022).
if [[ ! -s ref/mask.bed ]]; then
    curl -fsSL "https://raw.githubusercontent.com/nextstrain/tb/master/defaults/AF14_RLC_Regions.Plus.LowPmapK50E4.H37Rv.bed" \
        -o ref/mask.bed
fi

echo "setup done. Open a new shell so conda is on PATH."
