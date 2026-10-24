"""Validation figures for the ResistTB design.

Fig 1 analog (after TOAST, BMC Genomics 2025, Fig 1): resistance genes as a circos plot with WHO-catalogue positions,
variants observed in the 222 isolates and the four designed amplicons, plus a per-target zoom that checks every
oligo sits where it claims (primers and probes against the H37Rv sequence, SNP inside the amplicon and probe).

Fig 5 analog (after Behruznia et al., eLife 97870, Fig 5): gene presence/absence across the 222 isolates, grouped by
lineage, from the zero-coverage ('-') calls in snippy's aligned FASTA. Only regions present in H37Rv can be seen.

Run: PYTHONPATH=src .venv/bin/python scripts/validation_figures.py [results_dir] [out_dir]
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pycirclize import Circos
from scipy.cluster.hierarchy import leaves_list, linkage

from genohack.genome import decode, load_genes, load_mask, load_reference
from genohack.isolates import finished_samples, read_resistance, read_vcf
from genohack.targets import default_targets

REPO = Path(__file__).resolve().parents[1]
RESULTS = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "figures"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "cache"
CACHE.mkdir(exist_ok=True)
PAD = 150  # bases of flank around each gene in the circos, so promoters show

COMP = str.maketrans("ACGT", "TGCA")
rc = lambda s: s.translate(COMP)[::-1]  # noqa: E731

samples = finished_samples(RESULTS)
n_iso = len(samples)
genes = load_genes()
by_locus = {g.locus: g for g in genes.values()}
ref = decode(load_reference())
report = json.load(open(REPO / "web" / "data" / "report.json"))
targets = {t.id: t for t in default_targets()}
lin = {s: read_resistance(RESULTS, s) for s in samples}
main_lin = {s: (lin[s]["main_lineage"] or "unknown").replace("lineage", "L") for s in samples}

# ---------------------------------------------------------------- observed variants (isolates per position)
vc_path = CACHE / "variant_counts.json"
if vc_path.exists():
    var_count = Counter({int(k): v for k, v in json.load(open(vc_path)).items()})
else:
    var_count = Counter()
    for s in samples:
        var_count.update(set(read_vcf(RESULTS, s)["pos"].tolist()))
    json.dump(var_count, open(vc_path, "w"))

ac_path = CACHE / "alt_counts.json"
if ac_path.exists():
    alt_count = Counter(json.load(open(ac_path)))
else:
    alt_count = Counter()
    for s in samples:
        v = read_vcf(RESULTS, s)
        alt_count.update({f"{p}:{a}" for p, a, ty in zip(v["pos"], v["alt"], v["type"]) if ty == "snp"})
    json.dump(alt_count, open(ac_path, "w"))

who = pd.read_csv(REPO / "resources" / "who_catalogue_2023_assoc_with_R.csv")
who_pos = sorted({int(p) for p in who["pos"].dropna()})


def gene_of(name: str):
    return genes.get(name) or by_locus.get(name)


# ---------------------------------------------------------------- oligo position checks against H37Rv
def check_oligos() -> pd.DataFrame:
    rows = []
    for c in report["candidates"]:
        t = targets[c["id"]]
        olg = {o["role"]: o for o in c["oligos"]}
        probe_wt = olg["probe_wt"]
        for o in c["oligos"]:
            g = ref[o["start"] - 1 : o["end"]]
            genomic = rc(o["sequence"]) if o["strand"] == "-" else o["sequence"]
            mism = [i for i, (a, b) in enumerate(zip(genomic, g)) if a != b]
            rows.append(
                dict(
                    target=c["id"], oligo=o["role"], start=o["start"], end=o["end"], strand=o["strand"],
                    length=len(o["sequence"]), mismatches_vs_H37Rv=len(mism),
                    mismatch_genomic_pos=",".join(str(o["start"] + i) for i in mism),
                    covers_snp=(o["start"] <= t.pos <= o["end"]) if o["role"].startswith("probe") else None,
                    snp_inside_amplicon=c["amplicon_start"] <= t.pos <= c["amplicon_end"],
                )
            )
        # the two probes must differ only at the SNP, and carry ref / alt there
        wt = probe_wt["sequence"]
        mut = olg["probe_mut"]["sequence"]
        k = t.pos - probe_wt["start"]
        ix = k if probe_wt["strand"] == "+" else len(wt) - 1 - k
        base = (lambda b: b) if probe_wt["strand"] == "+" else (lambda b: b.translate(COMP))
        diff = [i for i, (a, b) in enumerate(zip(wt, mut)) if a != b]
        rows.append(
            dict(
                target=c["id"], oligo="probe_pair_check", start=probe_wt["start"], end=probe_wt["end"],
                strand=probe_wt["strand"], length=len(wt), mismatches_vs_H37Rv=len(diff),
                mismatch_genomic_pos=str(t.pos) if diff == [ix] else f"unexpected {diff}",
                covers_snp=(diff == [ix]) and base(wt[ix]) == t.ref and base(mut[ix]) == t.alt,
                snp_inside_amplicon=c["amplicon_start"] <= t.pos <= c["amplicon_end"],
            )
        )
    return pd.DataFrame(rows)


checks = check_oligos()
checks.to_csv(OUT / "oligo_position_checks.csv", index=False)

# ---------------------------------------------------------------- Fig 1: circos + per-target zoom
who_genes = sorted({g for g in who["gene"].unique() if g != "gene"})
wanted = {gene_of(n) for n in who_genes if gene_of(n)} | {gene_of(n) for n in ("rpoB", "katG", "fabG1", "inhA", "gyrA")}
spans = sorted((max(1, g.start - PAD), g.end + PAD, g) for g in wanted)
regions: list[dict] = []
for s, e, g in spans:  # merge neighbours whose padded windows overlap (fabG1 / inhA)
    if regions and s <= regions[-1]["end"]:
        regions[-1]["end"] = max(regions[-1]["end"], e)
        regions[-1]["genes"].append(g)
    else:
        regions.append(dict(start=s, end=e, genes=[g]))
for r in regions:
    r["label"] = "/".join(g.name for g in r["genes"])
    r["name"] = r["label"]
    r["size"] = r["end"] - r["start"] + 1
target_genes = {"rpoB", "katG", "fabG1", "inhA", "gyrA"}
cmap = plt.get_cmap("tab20")

fig = plt.figure(figsize=(18, 10))
gs = GridSpec(4, 2, width_ratios=[1.05, 1], wspace=0.12, hspace=0.75, left=0.02, right=0.98, top=0.88, bottom=0.11)
ax_c =fig.add_subplot(gs[:, 0], polar=True)

circos = Circos({r["name"]: r["size"] for r in regions}, space=2.2)
for i, (sector, r) in enumerate(zip(circos.sectors, regions)):
    rs = r["start"]
    is_target = any(g.name in target_genes for g in r["genes"])
    sector.text(r["label"], r=107, size=8.5, color="crimson" if is_target else "black",
                weight="bold" if is_target else "normal")
    t1 = sector.add_track((86, 94))
    for j, g in enumerate(r["genes"]):
        t1.rect(max(g.start, rs) - rs, min(g.end, r["end"]) - rs, fc=cmap((i + j) % 20), ec="white", lw=0.4)
    t2 = sector.add_track((77, 84))  # WHO catalogue positions
    t2.axis(fc="#f4f4f4", ec="none")
    for p in who_pos:
        if r["start"] <= p <= r["end"]:
            t2.rect(max(0, p - rs - 1), min(r["size"], p - rs + 2), fc="black", ec="none")
    t3 = sector.add_track((68, 75))  # variants observed in this study; deeper = more isolates
    t3.axis(fc="#f4f4f4", ec="none")
    for p, c in var_count.items():
        if r["start"] <= p <= r["end"]:
            t3.rect(max(0, p - rs - 1), min(r["size"], p - rs + 2), fc=plt.get_cmap("Reds")(0.2 + 0.8 * np.log(c) / np.log(n_iso)), ec="none")
    t4 = sector.add_track((59, 66))  # designed amplicons
    t4.axis(fc="#f4f4f4", ec="none")
    for cand in report["candidates"]:
        if r["start"] <= cand["genome_pos"] <= r["end"]:
            t4.rect(max(0, cand["amplicon_start"] - rs), min(r["size"], cand["amplicon_end"] - rs), fc="#2563eb", ec="#1e3a8a", lw=0.6)
            t4.scatter([cand["genome_pos"] - rs], [0.5], vmin=0, vmax=1, marker="v", s=55, c="red", ec="black", lw=0.6)
circos.plotfig(ax=ax_c)
fig.text(0.02, 0.925, "A  Resistance loci, variants and designed amplicons", fontsize=13, weight="bold")
ax_c.text(0, 0, f"ResistTB\n4 amplicons\n{n_iso} isolates", ha="center", va="center", fontsize=12, weight="bold")
fig.legend(
    handles=[
        Patch(fc="#d9d9d9", ec="gray", label="Outer ring: resistance genes (WHO grade 1-2 list)"),
        Patch(fc="black", label="Ring 2: WHO catalogue SNV positions"),
        Patch(fc=plt.get_cmap("Reds")(0.7), label=f"Ring 3: variants in our {n_iso} isolates (deeper = more isolates)"),
        Patch(fc="#2563eb", ec="#1e3a8a", label="Ring 4: designed amplicon"),
        Line2D([], [], marker="v", color="red", mfc="red", mec="black", ls="", label="Target SNP"),
    ],
    loc="lower left", bbox_to_anchor=(0.01, 0.0), fontsize=8.5, frameon=False, ncol=2,
)

colors = dict(forward="#16a34a", reverse="#ea580c", probe_wt="#7c3aed", probe_mut="#c026d3")
labels = dict(forward="Forward primer", reverse="Reverse primer", probe_wt="Probe, wild type", probe_mut="Probe, mutant")
for k, cand in enumerate(report["candidates"]):
    ax = fig.add_subplot(gs[k, 1])
    t = targets[cand["id"]]
    lo, hi = cand["amplicon_start"] - 25, cand["amplicon_end"] + 25
    ax.set_xlim(lo, hi)
    ax.set_ylim(-1.55, 1.15)
    ax.axhspan(-0.12, 0.12, xmin=(cand["amplicon_start"] - lo) / (hi - lo), xmax=(cand["amplicon_end"] - lo) / (hi - lo),
               color="#cbd5e1")
    ypos = dict(forward=0.45, reverse=-0.45, probe_wt=0.78, probe_mut=-0.78)
    for o in cand["oligos"]:
        a, b = (o["start"] - 0.5, o["end"] + 0.5) if o["strand"] == "+" else (o["end"] + 0.5, o["start"] - 0.5)
        ax.annotate("", xy=(b, ypos[o["role"]]), xytext=(a, ypos[o["role"]]),
                    arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.8", lw=5, color=colors[o["role"]],
                                    shrinkA=0, shrinkB=0))
    ax.axvline(t.pos, color="red", ls="--", lw=1)
    # variants seen in the isolates inside the window (stem height = share of isolates)
    exact = alt_count.get(f"{t.pos}:{t.alt}", 0)
    for p, c in var_count.items():
        if lo <= p <= hi:
            h = 0.9 * np.log1p(c) / np.log1p(n_iso)  # log scale so single-isolate variants stay visible
            ax.vlines(p, -1.5, -1.5 + h, color="#b91c1c", lw=1.6)
            if p == t.pos:
                ax.text(p + 1.5, -1.5 + h + 0.05, f"SNP: snippy target allele {exact}/{n_iso}", ha="left", fontsize=7.5, color="#7f1d1d", weight="bold")
            elif c / n_iso >= 0.03:
                ax.text(p, -1.5 + h + 0.05, f"{p}: {c}/{n_iso}", ha="center", fontsize=7, color="#7f1d1d")
    for p in who_pos:
        if lo <= p <= hi:
            ax.plot(p, -1.5, marker="^", color="black", ms=6, clip_on=False)
    snp_carriers = exact
    ch = checks[checks.target == cand["id"]]
    prb = ch[ch.oligo.isin(["probe_wt", "probe_mut", "probe_pair_check"])]
    ok = bool(prb.covers_snp.all() and ch.snp_inside_amplicon.all())
    bad = int(ch[ch.oligo.isin(["forward", "reverse", "probe_wt"])].mismatches_vs_H37Rv.sum())
    ax.set_title(
        f"{'BCDE'[k]}  {cand['gene']} {cand['mutation']} (pos {t.pos:,}): SNP {'in amplicon and probes' if ok else 'CHECK FAILED'}; "
        f"{bad} WT oligo base(s) differ from H37Rv; snippy target-allele SNP in {snp_carriers}/{n_iso}",
        loc="left", fontsize=9.2, weight="bold",
    )
    ax.set_yticks([])
    ax.ticklabel_format(useOffset=False, style="plain", axis="x")
    ax.tick_params(axis="x", labelsize=8)
    for sp in ("left", "right", "top"):
        ax.spines[sp].set_visible(False)
    if k == 0:
        ax.legend(
            handles=[Line2D([], [], color=colors[r], lw=5, label=labels[r]) for r in colors]
            + [Line2D([], [], color="#cbd5e1", lw=8, label="Amplicon"),
               Line2D([], [], color="#b91c1c", lw=2, label="Variant in isolates (stem = log of count)"),
               Line2D([], [], marker="^", color="black", ls="", label="WHO position")],
            loc="lower left", bbox_to_anchor=(0, 1.35), ncol=4, fontsize=8, frameon=False,
        )
fig.suptitle("Fig 1 analog: do the designed oligos sit on the intended resistance loci?", fontsize=15, weight="bold", x=0.02, y=0.985, ha="left")
fig.savefig(OUT / "fig1_position_validation.png", dpi=170)
plt.close(fig)

# ---------------------------------------------------------------- Fig 5: gene presence/absence by lineage
cov_path = CACHE / "gene_dash_fraction.npy"
gnames = sorted(genes.values(), key=lambda g: g.start)
if cov_path.exists():
    frac = np.load(cov_path)
else:
    frac = np.zeros((n_iso, len(gnames)), dtype=np.float32)
    starts = np.array([g.start - 1 for g in gnames])
    ends = np.array([g.end for g in gnames])
    for i, s in enumerate(samples):
        with gzip.open(RESULTS / s / "snps.aligned.fa.gz", "rb") as fh:
            seq = np.frombuffer(fh.read().split(b"\n", 1)[1].replace(b"\n", b""), dtype=np.uint8)
        cs = np.concatenate([[0], np.cumsum(seq == 45, dtype=np.int64)])  # '-' = no read coverage
        frac[i] = (cs[ends] - cs[starts]) / (ends - starts)
    np.save(cov_path, frac)

mask = load_mask()
mfrac = np.array([mask[g.start - 1 : g.end].mean() for g in gnames])
ABSENT = 0.9
absent = frac >= ABSENT
usable = mfrac < 0.5  # repeat-rich, poorly mappable genes (PE/PPE etc.) cannot call absence reliably
variable = usable & (absent.sum(0) >= 1) & (absent.sum(0) < n_iso)
cols = np.where(variable)[0]

lin_names = sorted(set(main_lin.values()))
lin_color = dict(zip(lin_names, ["#3b1d63", "#4f46a5", "#38a3d9", "#2f8f83", "#d97706"]))
order = []
for ln in lin_names:  # cluster isolates inside each lineage by their absence pattern
    idx = [i for i, s in enumerate(samples) if main_lin[s] == ln]
    if len(idx) > 2 and absent[np.ix_(idx, cols)].any():
        z = linkage(absent[np.ix_(idx, cols)].astype(float), "average", metric="hamming")
        idx = [idx[j] for j in leaves_list(z)]
    order += idx
col_order = cols[leaves_list(linkage(absent[:, cols].T.astype(float), "average", metric="hamming"))]
mat = ~absent[np.ix_(order, col_order)]  # True = present

fig = plt.figure(figsize=(16, 10))
gs = GridSpec(2, 3, width_ratios=[0.025, 1, 0.16], height_ratios=[1, 0.16], wspace=0.02, hspace=0.12, left=0.04, right=0.97, top=0.9, bottom=0.07)
ax_s = fig.add_subplot(gs[0, 0])
ax_h = fig.add_subplot(gs[0, 1])
ax_t = fig.add_subplot(gs[1, 1], sharex=ax_h)
ax_l = fig.add_subplot(gs[0, 2])
ax_h.imshow(mat, aspect="auto", cmap=matplotlib.colors.ListedColormap(["white", "#3f3d9e"]), interpolation="nearest")
ax_s.imshow(np.array([[matplotlib.colors.to_rgb(lin_color[main_lin[samples[i]]])] for i in order]), aspect="auto")
for a in (ax_s,):
    a.set_xticks([]); a.set_yticks([])
ax_h.set_yticks([]); ax_h.tick_params(labelbottom=False)
for sp in ax_h.spines.values():
    sp.set_color("#999")
# target loci: absent in any isolate? (bottom strip = share of isolates with the gene absent, for variable genes)
tgt = {"rpoB", "katG", "fabG1", "inhA", "gyrA"}
tgt_abs = {g.name: int((frac[:, k] >= ABSENT).sum()) for k, g in enumerate(gnames) if g.name in tgt}
ax_t.bar(range(len(col_order)), absent[:, col_order].mean(0), width=1.0, color="#6b7280")
ax_t.set_ylim(0, 1); ax_t.set_ylabel("share absent", fontsize=8)
ax_t.set_xlabel(f"{len(col_order)} variable genes (columns clustered by absence pattern); genome-order block table in lineage_deletion_blocks.csv", fontsize=9)
ax_t.tick_params(labelsize=7)
ax_l.axis("off")
ax_l.legend(
    handles=[Patch(fc=lin_color[l], label=f"{l} (n={sum(1 for s in samples if main_lin[s] == l)})") for l in lin_names]
    + [Patch(fc="#3f3d9e", label="Gene present"), Patch(fc="white", ec="#999", label=f"Gene absent (>= {int(ABSENT*100)}% of bases uncovered)")],
    loc="upper left", fontsize=9, frameon=False, title="Lineage", title_fontsize=10,
)
ax_l.text(0, 0.28, "Target genes absent in:\n" + "\n".join(f"{n}: {tgt_abs.get(n, 0)}/{n_iso} isolates" for n in ("rpoB", "katG", "fabG1", "inhA", "gyrA")),
          fontsize=9, va="top", transform=ax_l.transAxes)
fig.suptitle(
    f"Fig 5 analog: H37Rv gene presence/absence across {n_iso} Bandung isolates ({int((~usable).sum())} repeat-rich genes excluded)",
    fontsize=14, weight="bold", x=0.04, ha="left",
)
fig.savefig(OUT / "fig5_lineage_presence_absence.png", dpi=170)
plt.close(fig)

# ---------------------------------------------------------------- deletion blocks (RD analog) and oligo-site coverage by lineage
blocks, cur = [], None
for k in np.where(variable)[0]:
    sig = tuple(np.where(absent[:, k])[0])
    if cur and sig == cur["sig"] and gnames[k].start - cur["end"] < 5000:
        cur["genes"].append(gnames[k]); cur["end"] = gnames[k].end
    else:
        cur = dict(sig=sig, start=gnames[k].start, end=gnames[k].end, genes=[gnames[k]])
        blocks.append(cur)
rows = []
for b in blocks:
    comp = Counter(main_lin[samples[i]] for i in b["sig"])
    tot = Counter(main_lin.values())
    top = max(comp, key=comp.get)
    rows.append(dict(
        start=b["start"], end=b["end"], bp=b["end"] - b["start"] + 1, n_genes=len(b["genes"]),
        genes=";".join(g.name for g in b["genes"][:8]) + ("..." if len(b["genes"]) > 8 else ""),
        isolates_absent=len(b["sig"]), top_lineage=top, top_lineage_share_of_absent=round(comp[top] / len(b["sig"]), 2),
        share_of_top_lineage=round(comp[top] / tot[top], 2), subl_absent=";".join(sorted({str(lin[samples[i]]["sub_lineage"]) for i in b["sig"]}))[:60],
    ))
bt = pd.DataFrame(rows).sort_values("isolates_absent", ascending=False)
bt.to_csv(OUT / "lineage_deletion_blocks.csv", index=False)

# zero-coverage inside the oligo binding sites, by lineage
raw = {}
for i, s in enumerate(samples):
    pass
site_rows = []
with_dash = {}
for s in samples:
    with gzip.open(RESULTS / s / "snps.aligned.fa.gz", "rb") as fh:
        seq = fh.read().split(b"\n", 1)[1].replace(b"\n", b"")
    for c in report["candidates"]:
        for o in c["oligos"]:
            w = seq[o["start"] - 1 : o["end"]]
            with_dash[(s, c["id"], o["role"])] = (w.count(b"-"), w.count(b"N") + w.count(b"n"))
for c in report["candidates"]:
    for o in c["oligos"]:
        for ln in lin_names:
            ss = [s for s in samples if main_lin[s] == ln]
            site_rows.append(dict(target=c["id"], oligo=o["role"], lineage=ln, isolates=len(ss),
                                  uncovered=sum(with_dash[(s, c["id"], o["role"])][0] > 0 for s in ss),
                                  ambiguous=sum(with_dash[(s, c["id"], o["role"])][1] > 0 for s in ss)))
pd.DataFrame(site_rows).to_csv(OUT / "oligo_site_coverage_by_lineage.csv", index=False)

print(checks.to_string(index=False))
print("\nvariable genes:", len(col_order), "| usable genes:", int(usable.sum()), "| blocks:", len(bt))
print(bt.head(15).to_string(index=False))
print("\ntarget genes absent counts:", tgt_abs)
sr = pd.DataFrame(site_rows)
print("\noligo sites with any zero coverage:\n", sr[sr.uncovered > 0].to_string(index=False) if (sr.uncovered > 0).any() else "none")
print("oligo sites with any N:", int(sr.ambiguous.sum()))
