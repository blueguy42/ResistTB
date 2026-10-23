"""Off-target check with BLAST against human, non-tuberculous mycobacteria and respiratory bacteria.

Database built by scripts/build_offtarget_db.sh; sequence ids start with their group (human|ntm|flora).
A hit counts when the oligo could plausibly act there: a primer must align with at most 2 mismatches over at
least 16 bases AND reach its own 3' end (a primer extends from its 3' end); a probe must align with at most
2 mismatches over at least 18 bases. This is a screen, not a proof, and the BLAST word size limits sensitivity."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path(os.environ.get("GENOHACK_BLAST_DB", REPO / "ref" / "offtarget" / "offtarget"))
GROUPS = ("human", "ntm", "flora")
_cache: dict[tuple, dict[str, int]] = {}


def available(db: Path = DEFAULT_DB) -> bool:
    has_db = Path(str(db) + ".nsq").exists() or Path(str(db) + ".00.nsq").exists()
    return shutil.which("blastn") is not None and has_db


def blast_off_target(oligos: dict[str, tuple[str, str]], db: Path = DEFAULT_DB, threads: int = 4) -> dict[str, dict[str, int]]:
    """oligos maps a name to (sequence 5'->3', kind) where kind is 'primer' or 'probe'.
    Returns, per name, how many off-target alignments fall in each group."""
    todo = {n: v for n, v in oligos.items() if (v[0], v[1]) not in _cache}
    if todo:
        with tempfile.TemporaryDirectory() as tmp:
            q = Path(tmp) / "q.fa"
            q.write_text("".join(f">{n}\n{seq}\n" for n, (seq, _) in todo.items()))
            out = subprocess.run(
                ["blastn", "-task", "blastn-short", "-query", str(q), "-db", str(db), "-evalue", "100", "-word_size", "7",
                 "-dust", "no", "-max_target_seqs", "2000", "-num_threads", str(threads),
                 "-outfmt", "6 qseqid sseqid length mismatch gapopen qend qlen"],
                capture_output=True, text=True, check=True,
            ).stdout
        counts = {n: {g: 0 for g in GROUPS} for n in todo}
        for line in out.splitlines():
            qid, sid, length, mism, gaps, qend, qlen = line.split("\t")
            length, mism, gaps, qend, qlen = int(length), int(mism), int(gaps), int(qend), int(qlen)
            kind = todo[qid][1]
            if gaps or mism > 2:
                continue
            if kind == "primer" and not (length >= 16 and qend == qlen):
                continue
            if kind == "probe" and length < 18:
                continue
            group = sid.split("|", 1)[0]
            if group in counts[qid]:
                counts[qid][group] += 1
        for n, (seq, kind) in todo.items():
            _cache[(seq, kind)] = counts[n]
    return {n: _cache[(v[0], v[1])] for n, v in oligos.items()}
