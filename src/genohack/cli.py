"""Command line: python -m genohack.cli windows --results results --flank 250"""
from __future__ import annotations

import argparse
from pathlib import Path

from .genome import load_genes, load_mask, load_reference
from .isolates import finished_samples
from .targets import default_targets
from .variants import build_region_matrices, position_table
from .windows import rank_windows


def cmd_windows(args: argparse.Namespace) -> None:
    ref, mask, genes = load_reference(), load_mask(), load_genes()
    targets = [t for t in default_targets(genes) if not args.targets or t.id in args.targets]
    samples = finished_samples(args.results)
    print(f"{len(samples)} finished isolates")
    regions = {t.id: (t.pos - args.flank, t.pos + args.flank) for t in targets}
    matrices = build_region_matrices(args.results, regions, samples)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for t in targets:
        rm = matrices[t.id]
        table = position_table(rm, ref, mask)
        table.to_csv(out / f"{t.id}_positions.csv", index=False)
        windows = rank_windows(rm, table, ref, exclude=(t.pos, t.pos))
        windows.to_csv(out / f"{t.id}_windows.csv", index=False)
        variable = int((table["n_alt"] > 0).sum())
        print(f"{t.id}: {len(table)} positions, {variable} variable, {len(windows)} windows pass filters; "
              f"best perfect_frac {windows['perfect_frac'].max():.3f}" if len(windows) else f"{t.id}: no windows")


def main() -> None:
    p = argparse.ArgumentParser(prog="genohack")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("windows", help="variant tables and ranked conserved windows around each target")
    w.add_argument("--results", default="results")
    w.add_argument("--out", default="out")
    w.add_argument("--flank", type=int, default=250, help="bases either side of the target mutation")
    w.add_argument("--targets", nargs="*", help="target ids, default all")
    w.set_defaults(func=cmd_windows)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
