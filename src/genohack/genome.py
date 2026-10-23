"""Reference genome, gene annotation and the low-confidence mask. All coordinates are 1-based, inclusive,
on NC_000962.3 (H37Rv)."""
from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Base codes used everywhere: 0-3 are A, C, G, T; 4 means no usable base (no coverage, N or a gap).
CODES = {"A": 0, "C": 1, "G": 2, "T": 3}
MISSING = 4
LETTERS = "ACGT"
GENOME_LENGTH = 4_411_532

REPO = Path(__file__).resolve().parents[2]
DEFAULT_REF = REPO / "ref" / "NC_000962.3.fasta"
DEFAULT_GFF = REPO / "resources" / "H37Rv_ASM19595v2.gff"
DEFAULT_MASK = REPO / "ref" / "mask.bed"

_TO_CODE = np.full(256, MISSING, dtype=np.uint8)
for _b, _c in CODES.items():
    _TO_CODE[ord(_b)] = _c
    _TO_CODE[ord(_b.lower())] = _c


def encode(seq: str | bytes) -> np.ndarray:
    """Letters to codes. Anything that is not A, C, G or T (including N, n and -) becomes MISSING."""
    raw = seq.encode() if isinstance(seq, str) else seq
    return _TO_CODE[np.frombuffer(raw, dtype=np.uint8)]


def decode(codes: np.ndarray) -> str:
    return "".join(LETTERS[c] if c < MISSING else "N" for c in codes)


def read_fasta_codes(path: str | Path) -> np.ndarray:
    """Read a single-sequence FASTA (plain or gzip) into a code array."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as fh:
        lines = [ln.strip() for ln in fh if not ln.startswith(b">")]
    return encode(b"".join(lines))


def load_reference(path: str | Path = DEFAULT_REF) -> np.ndarray:
    ref = read_fasta_codes(path)
    if len(ref) != GENOME_LENGTH:
        raise ValueError(f"reference has length {len(ref)}, expected {GENOME_LENGTH}")
    return ref


@dataclass(frozen=True)
class Gene:
    name: str
    locus: str
    start: int
    end: int
    strand: str  # "+" or "-"

    def coding_pos(self, index: int) -> int:
        """Genome position of the 1-based coding base `index` (strand aware)."""
        if index < 1:
            raise ValueError("coding index starts at 1")
        return self.start + index - 1 if self.strand == "+" else self.end - index + 1

    def upstream_pos(self, offset: int) -> int:
        """Genome position of promoter base c.-`offset` (offset counted back from the start codon)."""
        return self.start - offset if self.strand == "+" else self.end + offset

    def codon_pos(self, codon: int, base: int = 2) -> int:
        """Genome position of base 1, 2 or 3 of a codon."""
        return self.coding_pos((codon - 1) * 3 + base)


def load_genes(path: str | Path = DEFAULT_GFF) -> dict[str, Gene]:
    genes: dict[str, Gene] = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 9 or f[2] != "gene":
                continue
            attrs = dict(kv.split("=", 1) for kv in f[8].split(";") if "=" in kv)
            locus = attrs.get("gene_id", attrs.get("ID", "").replace("gene:", ""))
            name = attrs.get("Name", locus)
            genes[name] = Gene(name, locus, int(f[3]), int(f[4]), f[6])
    return genes


def load_mask(path: str | Path = DEFAULT_MASK, length: int = GENOME_LENGTH) -> np.ndarray:
    """Boolean array indexed by 0-based position: True where the position is masked.

    The BED file is 0-based half-open, and names the chromosome NC_000962 (no version)."""
    mask = np.zeros(length, dtype=bool)
    if not Path(path).exists():
        return mask
    with open(path) as fh:
        for line in fh:
            f = line.split()
            if len(f) >= 3:
                mask[int(f[1]) : int(f[2])] = True
    return mask
