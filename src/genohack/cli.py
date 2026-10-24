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


def cmd_report(args: argparse.Namespace) -> None:
    import json

    from .assay import build_report

    report = build_report(args.results, request=args.request or "", target_ids=args.targets or None, snapshot=args.snapshot)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2))
    print(f"{len(report['candidates'])} assays on {report['dataset']['isolates']} isolates -> {args.out}")


def cmd_snapshot(args: argparse.Namespace) -> None:
    from .snapshot import write_snapshot

    out = write_snapshot(args.results, args.out, flank=args.flank)
    print(f"snapshot -> {out} ({Path(out).stat().st_size / 1024:.0f} KB)")


def cmd_library(args: argparse.Namespace) -> None:
    from .library import build_library

    lib = build_library(args.snapshot, args.out)
    rows = lib["targets"]
    ok = sum(r["status"] == "designed" for r in rows)
    print(f"{ok} of {len(rows)} targets designed -> {args.out}")


def main() -> None:
    p = argparse.ArgumentParser(prog="genohack")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("windows", help="variant tables and ranked conserved windows around each target")
    w.add_argument("--results", default="results")
    w.add_argument("--out", default="out")
    w.add_argument("--flank", type=int, default=250, help="bases either side of the target mutation")
    w.add_argument("--targets", nargs="*", help="target ids, default all")
    w.set_defaults(func=cmd_windows)
    r = sub.add_parser("report", help="design assays and write the JSON report the interface renders")
    r.add_argument("--results", default="results")
    r.add_argument("--out", default="web/data/report.json")
    r.add_argument("--request", default="")
    r.add_argument("--targets", nargs="*")
    r.add_argument("--snapshot", default=None, help="use a snapshot file instead of reading --results")
    r.set_defaults(func=cmd_report)
    s = sub.add_parser("snapshot", help="precompute the variant windows so the design runs without results/")
    s.add_argument("--results", default="results")
    s.add_argument("--out", default="resources/snapshot_windows.npz")
    s.add_argument("--flank", type=int, default=300)
    s.set_defaults(func=cmd_snapshot)
    lb = sub.add_parser("library", help="design every WHO target once and save a summary the chat lookup reads")
    lb.add_argument("--snapshot", default="resources/snapshot_windows.npz")
    lb.add_argument("--out", default="resources/design_library.json")
    lb.set_defaults(func=cmd_library)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
