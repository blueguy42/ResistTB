"""Off-target amplification screen with BLAST against human, non-tuberculous mycobacteria and respiratory bacteria.

Database built by scripts/build_offtarget_db.sh; sequence ids start with their group (human|ntm|flora).

Single-primer hits mean nothing against a genome this large: a 16-base primer with two mismatches matches the human
genome about a thousand times by chance. The real question is whether the two primers could make a PRODUCT, so
this counts predicted off-target amplicons, as Primer-BLAST does. A primer binding site must align over at least
16 bases with at most 2 mismatches, reach the primer's own 3' end, and match exactly over the last 5 bases (a primer
extends from its 3' end). A predicted product is a plus-orientation site followed, on the same sequence and within
MAX_PRODUCT bases, by a minus-orientation site. This is a screen with BLAST's sensitivity limits, not a proof."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = Path(os.environ.get("GENOHACK_BLAST_DB", REPO / "ref" / "offtarget" / "offtarget"))
GROUPS = ("human", "ntm", "flora")
MAX_PRODUCT = 3000
THREE_PRIME_EXACT = 5
CACHE_FILE = REPO / "resources" / "offtarget_cache.json"
_cache: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    return _cache


def available(db: Path = DEFAULT_DB) -> bool:
    has_db = Path(str(db) + ".nsq").exists() or Path(str(db) + ".00.nsq").exists()
    return shutil.which("blastn") is not None and has_db


def _sites(primers: dict[str, str], db: Path, threads: int) -> list[tuple[str, str, int, str]]:
    """Primer binding sites as (group, subject id, 5' position, orientation). Orientation '+' means the primer
    matches the plus strand, so it extends toward higher coordinates."""
    with tempfile.TemporaryDirectory() as tmp:
        q = Path(tmp) / "q.fa"
        q.write_text("".join(f">{n}\n{s}\n" for n, s in primers.items()))
        out = subprocess.run(
            ["blastn", "-task", "blastn-short", "-query", str(q), "-db", str(db), "-evalue", "1000", "-word_size", "7",
             "-dust", "no", "-max_target_seqs", "100000", "-num_threads", str(threads),
             "-outfmt", "6 qseqid sseqid sstart send length mismatch gapopen qend qlen qseq sseq"],
            capture_output=True, text=True, check=True,
        ).stdout
    sites = []
    for line in out.splitlines():
        qid, sid, sstart, send, length, mism, gaps, qend, qlen, qseq, sseq = line.split("\t")
        length, mism, gaps, qend, qlen = int(length), int(mism), int(gaps), int(qend), int(qlen)
        if gaps or mism > 2 or length < 16 or qend != qlen:
            continue
        if qseq[-THREE_PRIME_EXACT:] != sseq[-THREE_PRIME_EXACT:]:
            continue
        sstart, send = int(sstart), int(send)
        group = next((t for t in sid.split("|") if t in GROUPS), None)  # BLAST may wrap ids as gnl|<group>|<id>
        if group is None:
            continue
        # sstart is the primer's 5' end on the subject; the orientation says which way it extends.
        sites.append((group, sid, sstart, "+" if send > sstart else "-"))
    return sites


def predict_products(primers: dict[str, str], db: Path = DEFAULT_DB, threads: int = 4) -> dict[str, int] | None:
    """Predicted off-target amplicons per group for a primer set. Uses BLAST when the database is here, else the
    cached result for this exact primer pair (resources/offtarget_cache.json); None when neither exists."""
    key = "|".join(sorted(primers.values()))
    cache = _load()
    if key in cache:
        return cache[key]
    if not available(db):
        return None
    by_subject: dict[str, dict[str, list[int]]] = {}
    group_of: dict[str, str] = {}
    for group, sid, pos, orient in _sites(primers, db, threads):
        group_of[sid] = group
        by_subject.setdefault(sid, {"+": [], "-": []})[orient].append(pos)
    counts = {g: 0 for g in GROUPS}
    for sid, o in by_subject.items():
        minus = sorted(o["-"])
        for p in o["+"]:
            counts[group_of[sid]] += sum(1 for m in minus if 0 < m - p <= MAX_PRODUCT)
    cache[key] = counts
    CACHE_FILE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return counts
