"""Load per-isolate snippy outputs from `results/<sample>/` (as written by scripts/process_isolate.sh)."""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .genome import encode


def finished_samples(results_dir: str | Path) -> list[str]:
    """Samples with a DONE marker AND their data files, in sorted order (a partial run is fine).

    The data files are checked too: after a resume the marker can exist locally while the files are
    still only in the bucket."""
    need = ("snps.aligned.fa.gz", "snps.vcf.gz")
    return sorted(
        p.parent.name for p in Path(results_dir).glob("*/DONE") if all((p.parent / f).exists() for f in need)
    )


def read_aligned(results_dir: str | Path, sample: str) -> np.ndarray:
    """Whole-genome base codes for one isolate from snippy's aligned FASTA.

    snippy writes the reference with this isolate's SNPs and MNPs applied; '-' marks zero coverage and
    N or n marks low coverage or ambiguity. All three become MISSING. Indels are NOT in this file."""
    with gzip.open(Path(results_dir) / sample / "snps.aligned.fa.gz", "rb") as fh:
        lines = [ln.strip() for ln in fh if not ln.startswith(b">")]
    return encode(b"".join(lines))


def read_vcf(results_dir: str | Path, sample: str) -> pd.DataFrame:
    """Variant calls for one isolate: pos, ref, alt, type (snp, mnp, ins, del, complex), depth."""
    with gzip.open(Path(results_dir) / sample / "snps.vcf.gz", "rt") as fh:
        text = "".join(ln for ln in fh if not ln.startswith("##"))
    df = pd.read_csv(io.StringIO(text), sep="\t", usecols=["POS", "REF", "ALT", "INFO"])
    info = df["INFO"].str.extract(r"TYPE=([a-z,]+)")[0].str.split(",").str[0]
    dp = pd.to_numeric(df["INFO"].str.extract(r"DP=(\d+)")[0])
    return pd.DataFrame({"pos": df["POS"], "ref": df["REF"], "alt": df["ALT"], "type": info, "depth": dp})


def read_resistance(results_dir: str | Path, sample: str) -> dict:
    """TB-Profiler lineage and resistance summary for one isolate."""
    r = json.load(open(Path(results_dir) / sample / f"{sample}.results.json"))
    return {
        "sample": sample,
        "main_lineage": r.get("main_lineage"),
        "sub_lineage": r.get("sub_lineage"),
        "drtype": r.get("drtype"),
        "dr_variants": r.get("dr_variants", []),
    }
