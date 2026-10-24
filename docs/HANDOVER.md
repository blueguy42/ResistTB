# ResistTB handover (version 3)

Written 2026-10-25 about 01:15 WIB (2026-10-24 18:15 UTC), replacing version 2 (2026-10-24 evening). It is meant for a new chat
that continues the work. Facts were checked against the repo, the cloud project and the live service on that date unless a line
says "not verified". Read this file first, then `README.md`, then the memory notes (section 21).

Numbers in square brackets, like [8], refer to the reference list in section 22. The short status report is
`docs/ResistTB_report.pdf` (source `docs/ResistTB_report.html`).

**The one thing to know first:** all data processing is finished and deployed, and the site is live at both
`https://resist-tb.afanhandoyo.com` (custom domain, valid Google certificate, confirmed about 01:20 WIB) and
`https://resisttb-66604371416.asia-southeast1.run.app`. What remains is validation work and design improvements (section 18), not
operations.

---

## 1. Summary

ResistTB (formerly "ChatGP-TB"; renamed on 2026-10-25) turns public *Mycobacterium tuberculosis* (TB) genomes into qPCR primer and
allele-specific probe designs for drug-resistance variants. A cloud VM processed sequencing reads into per-isolate variant calls
(done, VM deleted). A Python library designs primers and probes on the **population consensus** of those isolates, checks them
against every isolate (overall, by lineage, by region), screens for off-target amplification with BLAST, scores them and checks
multiplexing. A Gemini agent on Vertex AI turns a free-text question into a design call; a Next.js interface shows the ranked
assays, a browsable library of designs for **205 WHO-catalogue resistance variants** (192 designed), saved chats and one report per
chat. **Everything is in silico. Nothing has been tested in a tube.**

What changed since version 2 (written 19:15 WIB on 2026-10-24):

| Then (v2) | Now (v3) |
|---|---|
| VM run still going (about 150 of 234 new isolates) | Run finished: **456 isolates** (Bandung 222, Guangdong 173, Tamil Nadu 61). 13 isolates failed on truncated SRA downloads and were redone through ENA |
| Library, snapshot, report on Bandung only | Rebuilt on all 456 isolates; every one of the 192 designs is now BLAST-screened (109 primer pairs in the cache) |
| rpoB S450L scored 83 (Bandung) then 61 (first pooled rebuild) | Primer selection fixed to try looser variable-site tolerances when the best design has H37Rv near-matches: rpoB S450L **80**, specificity 100 |
| Cloud Run `chatgp-tb`, old build | Cloud Run **`resisttb`** (new service, new service account), current build, public. Old service, account and images deleted |
| VM `genohack-run-0` and 100 GB disk | **Deleted** (no snapshot, by the user's decision). Nothing but Cloud Run and two buckets remains |
| Name ChatGP-TB | **ResistTB** everywhere in code, UI, docs and storage keys |
| No custom domain | `https://resist-tb.afanhandoyo.com` live (Cloud Run domain mapping, Cloudflare DNS only) |
| FASTA exported for Bandung only | `fasta_export/` now covers all 456 isolates |

Team (from the master document): Hanifa Syifa Kamila, Yudisto P Nadapdap, Hefina Aissa Gunawan, Ahmad Alfani Handoyo. The
proposal deadline was 15:00 WIB on 2026-10-24 (3 A4 pages); whether it was submitted is not known to this chat. The draft is in the
master document, pages 68-72, and says "ChatGP-TB", not ResistTB.

---

## 2. Status snapshot (2026-10-25 ~01:15 WIB)

| Area | State |
|---|---|
| Stage A (per-isolate variant calls) | **Done.** 456 result folders in the bucket, 456 DONE markers |
| Isolate QC | Done: most isolates good; 4 look contaminated or mixed (section 6.2) |
| Design library (Python) | **Done**, 35 tests pass |
| WHO target library | 205 targets; **192 designed**, 13 not designed (section 7.3) |
| Off-target (BLAST) screen | **Done for all 192 designs**; cache `resources/offtarget_cache.json` holds 109 pairs |
| Agent (Gemini) and API | Done and deployed (includes the `region_mutations` tool and optional region from commit `5c6a3b3`) |
| Web interface | Done and deployed |
| Cloud Run `resisttb` | **Live and public**, revision `resisttb-00001-nvs`, URLs `https://resisttb-66604371416.asia-southeast1.run.app` and `https://resist-tb.afanhandoyo.com` |
| Custom domain `resist-tb.afanhandoyo.com` | **Live** over HTTPS (Google Trust Services certificate); it took about an hour after the mapping showed Ready (section 9.3) |
| VM and disk | **Deleted.** Recreate only for held-out validation or new BLAST pairs |
| FASTA export | Done for all 456 (`genohack/fasta_export/`, git-ignored, 1.4 GB) |
| Held-out validation (779 other Indonesian runs) | **Not started** |
| Leave-one-region-out validation | Not started (needs no new data) |
| Wet-lab validation | Not started (out of scope for the hackathon) |
| Business case | Separate chat (section 3) |

Repo: `github.com/blueguy42/genohack` (private), branch `main`, HEAD `a923266` ("Handover: point to the new resisttb service URL and
revision"), working tree clean at the time of writing before this file and the report were added. Local path
`/Users/afan/Documents/Repos/mtb-hackathon/genohack`.

---

## 3. Parallel chats and shared state (read before touching anything)

Several Claude sessions work in the same folder. They share **one git working tree, one branch (`main`), one cloud project and the
same local ports**. That is the main source of confusion. The original session for this thread is
`local_cbe979e7-ae08-4171-b80f-63723135c7ab` (the one that wrote this file). Session ids below come from `list_sessions` on
2026-10-25.

| Session | What it is | State / what to know |
|---|---|---|
| `local_cbe979e7…` (this chat) | OCR of the master PDF, VM run completion (ENA retry), pooled rebuild, BLAST rerun, primer selection fix, FASTA export, FASTA/validation research, commit and deploy, rename to ResistTB, new Cloud Run service, custom domain, this handover | Ends here. Its transcript is the best source for the "why" behind section 19 |
| `local_5137a6cf…` "OCR on PDF images (fork)" | Fork of this chat. Built the `region_mutations` lookup, made the region optional in chat, committed `5c6a3b3` (`agent.py`, `lookup.py`) | Idle. Its report: "backend needs a restart, per-region answers need the pooled rebuild" (both now done) |
| `local_c9750d2c…` "OCR on PDF images" | Second fork. Last active about 00:46 WIB on 2026-10-25. In its visible tail it answered a side question about the Cloud Run framework (section 9.2). Its earlier 500+ messages were not reviewed | Idle. The local web and API servers were **restarted at 00:47 WIB** by something other than this chat, most likely this fork or the app; not verified |
| `local_6e8a81cd…` "Active Google Cloud resources (fork)" | Wrote handover v2; built regions, WHO targets, library, sessions, layout, onboarding | Idle (12:16 UTC on 2026-10-24) |
| `local_80dcbe51…` "Active Google Cloud resources" | Parent of the above: cloud audits, first VM and disk deletion, first Cloud Run deploy and public access, VM run and watchdog | Idle. Knows nothing after 11:16 UTC on 2026-10-24 |
| `local_c43d11a6…` "Active Google Cloud resources (fork)" | Fork that explained Fig. 5 | Idle. Its claim that the backend only runs on the laptop is **outdated** |
| `local_cec39fb2…` "Genohack secrets audit" | Ran gitleaks 8.30.1 | Git history: 0 findings. 12 working-tree hits, all inside the ignored build cache `web/.next/` (keys in compiled output, not source). Not re-run after today's changes |
| `local_bca5dc77…` "GenoHack business values" | Pitch and commercial slides, competitor table (Primer3, TOAST, PrimeGen, Xpert), mentor feedback | No code changes. Mentors said: highlight two benefits |
| `local_995b932e…` "NCBI project metadata retrieval" | The original builder session (1,400+ messages): pipeline, v1 design, first docs | Source of old decisions; ask it for history, not current state |
| Other sessions (meeting-transcriber, Tap-Twice, INA Digital Edu, Personal Website, Sahaba) | Unrelated projects | Ignore |

**Rules that avoid collisions**

1. **Never run `git add -A` or `git commit -a`.** Commit only the files you changed, by name. The user has a standing OK to push this
   repo (HTTPS via keychain) and wants no `Co-Authored-By` or "Generated with" lines in commits.
2. **No VM exists.** Do not create one unless you need held-out validation or BLAST for new primer pairs (section 15.4). If you do,
   the startup script shuts the VM down by itself once all isolates are done, which is not what you want for a BLAST job (section 16).
3. **Local ports:** the web dev server is on 3000 (`next-server`) and the API on 8000 (`uvicorn genohack.api:app`), both restarted
   at 00:47 WIB. Check with `lsof -nP -iTCP:3000 -iTCP:8000 -sTCP:LISTEN` before starting another; a second `pnpm dev` or `uvicorn`
   will clash. The API reads `results/` (456 folders) so it takes several seconds to start.
4. **`results/` is a shared cache** synced from the bucket by `scripts/sync_results.sh` (815 MB, 456 folders, plus a stray
   `.DS_Store`). A first sync dropped one file; always verify every folder has `DONE`, `<run>.results.json`, `metadata.json`,
   `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt` (only SRR37495300 lacks `metadata.json`; it never had one).
5. **`gcloud` default project on the laptop is `tap-twice-aurania`.** Always pass `--project haduh-512512`. The active account is
   `ahmadalfanihandoyo1@gmail.com`.
6. **Cloud actions needing approval:** enabling APIs, IAM changes, instance and service deletion were blocked by the permission
   classifier earlier and are now done only on the user's explicit say-so. Do not work around a block; give the command to the user.
7. **macOS Gatekeeper blocks `gcloud-crc32c`.** gcloud falls back to a slower checksum; one sync dropped a file while the prompt was
   open. Do not bypass it (the user's security setting).
8. Docs from other chats: `docs/pipeline_explained.{html,pdf}`, `docs/pipeline_overview.{html,pdf}`, `docs/progress_report.{html,pdf}`
   and `docs/status_report.{html,pdf}` were renamed to ResistTB and the PDFs regenerated with headless Chrome (same page counts).
   `status_report` and `progress_report` still describe the earlier partial state; use this file and `ResistTB_report.pdf` instead.
9. Files outside the repo, in the parent folder `/Users/afan/Documents/Repos/mtb-hackathon/`: `GenoHack Master Document.pdf`,
   `GenoHack Master Document - OCR.txt` (OCR of its 58 image-only pages; dense tables and figures are garbled), `business.txt`,
   `papers/`, `ncbi_metadata/`.

---

## 4. Pipeline overview

```
 public data                    Stage A: VM (Snakemake, per isolate)                       Stage B: design library (Python)                 Stage C
 ───────────                    ────────────────────────────────────                       ────────────────────────────────                ─────────
 SRA metadata (DuckDB)  ──▶  fasterq-dump ──▶ rasusa 100x ──▶ snippy (BWA-MEM+FreeBayes) ──▶ snapshot (±300 bp windows, 205 targets)  ──▶ Gemini agent
 BioProject accessions        reads             subsample       vs H37Rv NC_000962.3          + lineage + region per isolate                (Vertex AI,
 ENA run lists                (ENA fallback)                     │                           ──▶ consensus, variable-site mask             function calls)
                                                                └▶ TB-Profiler 6.6.5        ──▶ Primer3 primers, allele-specific probes    ──▶ FastAPI
                                                                   (lineage, resistance)    ──▶ tolerance ladder 2→5→10→20 %                 /api/chat (SSE)
                                                                ──▶ results/<run>/ in GCS   ──▶ BLAST specificity (VM, cached)               /api/design
                                                                    + DONE marker           ──▶ coverage: exact / 1 mismatch / likely fail   /api/report
                                                                                            ──▶ WHO evidence (PPV), score, multiplex tubes ──▶ Next.js UI
                                                                                            ──▶ design library (205 targets)                 (static export)
```

Full diagrams: `docs/pipeline_overview.pdf` and `docs/pipeline_explained.pdf`.

### 4.1 Stage A: per-isolate processing (cloud VM, finished)

Modelled on the Nextstrain TB build [22]. Orchestrated by Snakemake [14] (`workflow/Snakefile`; one rule per isolate; random
fixed-seed order so partial results are a fair sample). Per isolate, `scripts/process_isolate.sh <run> <threads> <coverage>`:

1. **Skip** if `gs://haduh-512512-genohack/results/<run>/DONE` exists.
2. **Download** with `fasterq-dump` (sra-tools 3.2.1 [13], `--split-files`) from NCBI SRA. ENA (curl, gzip-tested) is opt-in with
   `DOWNLOAD_SOURCE=ena`. **ENA was needed for 13 isolates** whose SRA downloads were truncated (rasusa error "First input has N reads,
   but the second has M reads").
3. **Subsample** to 100x with `rasusa` 5.1.0 [12] (`--genome-size 4.4mb --seed 100`). Average coverage is about 370x.
4. **Call variants** with `snippy` 4.6.0 [8] against H37Rv: BWA-MEM [10] then FreeBayes 1.3.6 [9]
   (`-p 2 -P 0 -C 2 -F 0.05 --min-coverage 10 --min-repeat-entropy 1.0 -q 13 -m 60`). Genotype 1/1 only, minimum depth 10. A base with
   depth under 10 is written as `-` (uncalled) in the aligned FASTA.
5. **Profile** with `tb-profiler profile` 6.6.5 [11]: lineage and drug-resistance calls (needs `snpeff=5.2`, section 16).
6. **Keep** `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, `<run>.results.json`, `metadata.json` (per-step seconds, bytes, versions);
   upload; write `DONE` last; delete reads and intermediates.

Run settings: 6 isolates at once × 3 threads, `--cores nproc+2 --keep-going --retries 2 --rerun-incomplete` on e2-standard-16. Median
seconds per isolate under 6-way parallelism: Bandung 851, Tamil Nadu about 515-519, Guangdong about 435-438. The new-region run took
about 5 h 40 min (started 08:33 UTC; 221 of 234 done at 14:01 UTC; the 13 retried isolates finished about 15:00 UTC). Selection of
isolates: `sql/indonesia_isolates.sql` (1,001 Indonesian runs) and `scripts/ena_isolates.py` (234 runs for two other BioProjects).

**VM automation (script files kept in the repo; the VM itself is deleted):**
- `scripts/vm_startup.sh` runs at every boot from instance metadata (`BUNDLE`, `BUCKET`, `DESIGN_BIOPROJECT`, `SHARD_INDEX`,
  `SHARD_COUNT`, `MAX_HOURS=14`): creates user `runner`, installs the environment, writes `/etc/genohack-run.env`, starts the run,
  installs the watchdog, copies logs to `gs://…/runlogs/<vm>/` every 10 minutes, schedules a hard stop, and **shuts the VM down when
  the share is complete**.
- `scripts/watchdog_vm.sh` + `install_watchdog_vm.sh`: kills an isolate running over 1 hour, restarts a dead run, stops the VM after 3
  restarts without progress. It does not pass `DOWNLOAD_SOURCE` to restarted runs; that is why the ENA retry was started by hand.

### 4.2 Stage B: design library (`src/genohack/`)

| Step | Module | What it does | Key settings |
|---|---|---|---|
| Targets | `targets.py` | `all_targets()`: 4 hand-built (rpoB S450L, katG S315T, inhA c.-15, gyrA D94G) + WHO targets generated from the catalogue: single-base changes with a genome position, name matching `_SPECIFIC` (p.Xxx123Yyy, p.Xxx123*, p.Xxx1?, c.-14C>T, n.1401A>G), at least 10 resistant isolates, deduplicated by (pos, alt) → **205 targets** | `*_LoF` entries are excluded |
| Snapshot | `snapshot.py` | `resources/snapshot_windows.npz` (733 KB): ±300 bp windows for 205 targets × 456 isolates, plus lineage and region per isolate. Lets the deployed service run without the 815 MB of per-isolate files | `GENOHACK_SNAPSHOT` (auto-used when `results/` is missing) |
| Variant table | `isolates.py`, `variants.py` | base code per isolate per position (ACGT, MISSING=4, N), indel flags from the VCF, consensus base, minor-allele frequency, masked flag | variable site = MAF > tolerance **and** ≥ 2 isolates |
| Primers | `primers.py` | Primer3 [16] on the consensus; excluded: variable, masked, indel or missing sites; amplicon must contain the SNP; excluded regions merged into runs because Primer3 allows at most 200 | length 18-25, Tm 58-64, GC 40-65, poly-X ≤ 4, product 70-160, 20 pairs per call |
| Probes | `probes.py` | wild-type from consensus, mutant = one base changed; Tm gap via Primer3 thermodynamic alignment | 20-30 nt, Tm 64-74, GC 30-75, no 5′ G, SNP ≥ 4 from ends |
| Assemble | `assay.py` | `build_assay` → `_build_assay` → `_best_of_pairs`. Walks the **tolerance ladder 2% → 5% → 10% → 20%**. **New rule (commit `9570925`):** keep trying looser rungs while the best design so far has H37Rv near-matches, and keep whichever rung scores higher; stop as soon as a design has none. **Probe-room fallback** (primers kept 26 bp from the SNP, 3× pairs) only when the normal attempt fails | rrs n.1401A>G is designed with the fallback (15 designs use it) |
| Checks | `checks.py`, `specificity.py`, `thermo.py` | hairpin / self-dimer / cross-dimer dG; H37Rv near-match scan; BLAST predicted off-target products | |
| Coverage | `assay.coverage_for` | per isolate: **exact**, **one mismatch**, **likely fail** (≥ 2 mismatches, or 1 in the last 3 bases of a primer); grouped `by_lineage` and `by_region`. **An uncalled base counts as a mismatch** (section 14) | SNP position must be called |
| Evidence | `who.py` | best WHO positive predictive value for the exact change | grade 1-2 slice |
| Score | `assay.score_assay` | section 11 | 30/30/20/20 |
| Multiplex | `multiplex.py` | all cross-assay oligo pairs, worst dimer dG, tube grouping | caution −7, conflict −9 kcal/mol; 4 channels, 2 per assay |
| Library | `library.py` | designs every target once, stores a summary (`resources/design_library.json`, copied to `web/data/library.json`) incl. `by_region` exact matches, drug names, `mutation_by_region`; run with `python -m genohack.cli library` | per-target error guard |
| Lookup | `lookup.py` | `find_targets(query)`, `region_mutations`, `DRUG_ALIASES`, suggested panel, `weak_panel_note`, `limit_note`, `names_a_target` | `PANEL_SIZE=4` |
| Regions | `regions.py` | `resources/regions.csv` (BioProject → label): PRJNA1433044 Bandung, PRJNA1256943 Tamil Nadu, PRJNA898845 Guangdong | |

**Specificity (BLAST).** A primer binding site is a BLAST (`blastn-short`, word size 7) alignment of ≥ 16 bases, ≤ 2 mismatches, no
gaps, last 5 bases exact. A **predicted product** is a plus-orientation site followed within 3,000 bases by a minus-orientation site
on the same sequence. Groups: human, ntm, flora. The off-target database (729 sequences, 3.37 Gb, index about 803 MiB: human
GRCh38, 7 NTM, 6 respiratory bacteria [7]) lives only in the bucket (`offtarget/`); it cannot be downloaded to the Mac (Gatekeeper).
`specificity.predict_products` reads the cache `resources/offtarget_cache.json` keyed by `"F|R"` (sorted primer sequences) and only
runs BLAST if the database is present. **A pair with no cache entry reports specificity as "not checked".** After today's work all 192
designs are cached; any change to a primer pair needs BLAST on a VM again (section 15.4).

### 4.3 Stage C: agent, API, interface

**Agent** (`agent.py`): Gemini `gemini-3.5-flash-lite` on Vertex AI [19], location `global`, `google-genai` function calling, up to 5
turns. Tools: `find_targets`, `design_assays` (≤ 6 ids), `region_mutations` (carriers of a mutation per region, region optional
since `5c6a3b3`) and a capabilities listing. The model sees a compact summary; **it never emits numbers**. Because the small model
ignores some instructions, critical wording is **enforced in code** (`limit_note`, `weak_panel_note`, an assumption prefix when no drug
is named). Out of scope and declined: prescribing advice, unrelated topics. WHO variants not designed are explained, not designed.
The system prompt starts "You are ResistTB".

**API** (`api.py`, FastAPI app title "ResistTB"): `GET /api/health`, `GET /api/report`, `POST /api/chat` (SSE events `step`, `report`,
`text`, `error`, `done`; body `{"message": ...}`), `POST /api/design` (no model call; body `{"targets": ["rpoB_S450L", ...]}`). Rate
limits (`RateLimit`, in memory per instance): chat 20/IP/hour and 300/day; design 60/IP/hour and 1,500/day; overrides
`GENOHACK_CHATS_PER_IP_HOUR/DAY`, `GENOHACK_DESIGNS_PER_IP_HOUR/DAY`. CORS: `GENOHACK_ORIGINS` if set, otherwise any localhost port. If
`web/site` exists the API also serves the static page, so one container is the whole site. Other env: `GENOHACK_RESULTS`,
`GENOHACK_SNAPSHOT`, `GENOHACK_PROJECT`, `GENOHACK_LOCATION`, `GENOHACK_MODEL`, `GENOHACK_BLAST_DB`.

**Web** (`web/`, Next.js 16.4.3, React 19.3, Tailwind 4): section 8.

---

## 5. Inputs and outputs

**Inputs**
1. Public reads: Bandung PRJNA1433044 (222 runs, 174 GB), Tamil Nadu PRJNA1256943 and Guangdong PRJNA898845 (234 runs together) [1].
2. H37Rv NC_000962.3 [3], gene annotation [4], low-confidence mask [6].
3. WHO 2023 mutation catalogue, grade 1-2 slice [5].
4. Off-target genomes for BLAST [7] (bucket only).
5. A chat message, or a library selection of up to 6 variants.

**Outputs**
1. Per isolate in `gs://haduh-512512-genohack/results/<run>/`: `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, `<run>.results.json`,
   `metadata.json`, `DONE`.
2. Derived artefacts committed to git: `resources/snapshot_windows.npz`, `resources/design_library.json`,
   `resources/offtarget_cache.json`, `web/data/library.json`, `web/data/report.json`.
3. Per request: a report JSON (schema `web/lib/types.ts`): ranked assays with primer pair, WT and mutant probes (sequence, coordinates,
   strand, Tm, hairpin and self-dimer dG, Tm gap), four scores, coverage overall / by lineage / by region, specificity, reasons, caveats,
   multiplex pairs and tubes, step timings, `dataset` (isolate count, regions).
4. A chat reply streamed to the interface.
5. FASTA export (local only): `fasta_export/per_isolate/<run>.fasta.gz` (456 files, aligned genome per isolate, header
   `>run lineage=… drtype=… ref=NC_000962.3`), `all_456_isolates.fasta.gz` (606 MB), `all_222_isolates.fasta.gz` (older, Bandung only) and
   `isolates.tsv` (456 rows: run, bioproject, lineage, sublineage, drtype, length, missing bases, missing %, variant count). Sequences
   are reference-length alignments, not assemblies; `-` and `N` mark uncalled bases.
6. Figures and tables: `figures/` (position validation, lineage presence) and the docs.

---

## 6. Datasets

| Dataset | Source | Size / count | Where | Note |
|---|---|---|---|---|
| SRA metadata [2] | AWS open data, DuckDB | 1,001 Indonesian Illumina MTB runs | regenerate with `scripts/select_isolates.sh` | public |
| Bandung reads [1] | PRJNA1433044 (Universitas Padjadjaran) | 222 runs, 174 GB | 222 result folders | original design set |
| Tamil Nadu reads [1] | PRJNA1256943 (prevalence survey) | 61 runs processed | result folders | lineage 1 heavy |
| Guangdong reads [1] | PRJNA898845 (clinical strains) | 173 runs processed | result folders | lineage 2 heavy, many MDR/pre-XDR |
| H37Rv [3] | NC_000962.3 | 4,411,532 bp | `ref/NC_000962.3.fasta` (git-ignored; copied into the container) | |
| Gene annotation [4] | Ensembl ASM19595v2 via TOAST | 4,018 genes | `resources/H37Rv_ASM19595v2.gff` | |
| Low-confidence mask [6] | `nextstrain/tb` BED | 1,324 regions, 276,750 bases | `ref/mask.bed` | |
| WHO catalogue 2023 [5] | GTB-tbsequencing | grade 1-2: 1,383 rows, 1,291 variants, 643 with SNV coordinates | `resources/who_catalogue_2023_assoc_with_R.csv` | MIT |
| Off-target BLAST db [7] | NCBI Datasets | 729 sequences, 3.37 Gb, index 803 MiB | bucket `offtarget/` only | not on the laptop |
| Snapshot | this project | 205 targets × ±300 bp × 456 isolates, 733 KB | `resources/snapshot_windows.npz` | |
| Per-isolate results | this project | 815 MB local, 456 folders | bucket + `results/` (ignored) | |
| Off-target cache | this project | 109 primer pairs | `resources/offtarget_cache.json` (also in bucket `vm-backup/`) | |

**Held-out candidates (not processed):** PRJNA595834 (387 runs, TANDEM), PRJNA430531 (314, Radboudumc), PRJNA1150781 (42, Papua),
PRJNA633244 (30, Java MDR), PRJNA950554 (6): 779 Indonesian runs. **Rejected or pending:** PRJEB84199 (London) accession could not be
resolved; a Philippines project is pending data. (The OCR of team notes p. 73 also lists PRJEB24463.)

### 6.2 Isolate QC (all 456, computed 2026-10-24; table in the scratchpad of this chat only, recompute with the script idea below)

| Metric | Bandung (221 + 1 without metadata) | Guangdong (173) | Tamil Nadu (61) |
|---|---|---|---|
| Median % reads mapped | 98.9 | 99.5 | 98.6 |
| Median target depth (after 100x subsample) | 83x | 91x | 56x |
| Median uncalled fraction of genome | 2.2% | 2.6% | 2.9% |
| Median variants vs H37Rv | 1,046 | 1,494 | 2,164 |

- **Four isolates look contaminated or mixed** (reads mapped under 50%, thousands of extra variants, oversized result files):
  SRR22256253 (19% mapped), SRR37495362 (27%), SRR22256210 (46%, no lineage call, 11.7 MB results JSON), SRR22256266 (49%).
- Depth under 30x: SRR22256253, SRR33381019, SRR37495362.
- Tamil Nadu isolates with many uncalled bases despite normal depth: SRR33381004 (30%), SRR33380963 (23%).
- They are **still included** in the design. Excluding them is an open decision (section 18).
- Recompute: read `<run>.results.json` → `qc.percent_reads_mapped`, `qc.target_median_depth`; count `-`, `N`, `n` in `snps.aligned.fa.gz`;
  `VariantTotal` in `snps.txt`. Join the sequence lines with `b"".join` (a `+=` loop is quadratic and took over 10 minutes).

**Data caveats:** BioProject-level region labels are coarse (one country-province per project). Lineage mix differs strongly by region
(Guangdong mostly lineage 2, Tamil Nadu mostly lineage 1, Bandung lineages 4 and 2), so the pooled consensus is dominated by the larger
sets. Pooled lineage counts: lineage 1 58 (+1 mixed), lineage 2 249 (+4 mixed with 4), lineage 3 5, lineage 4 138, unknown 1.

---

## 7. Results (current, pooled on 456 isolates)

### 7.1 The four headline assays

| Assay | Overall | Conservation / thermo / specificity / evidence | Exact matches (of 456) | Bandung | Guangdong | Tamil Nadu |
|---|---|---|---|---|---|---|
| inhA c.-15C>T (1,673,425) | 94 | 97 / 84 / 100 / 97 | 441 | 221/222 | 171/173 | 49/61 |
| gyrA p.Asp94Gly (7,582) | 86 | 90 / 68 / 100 / 94 | 412 | 205/222 | 154/173 | 53/61 |
| katG p.Ser315Thr (2,155,168) | 83 | 94 / 85 / 50 / 98 | 429 | 219/222 | 164/173 | 46/61 |
| rpoB p.Ser450Leu (761,155) | 80 | 84 / 50 / 100 / 98 | 382 | 212/222 | 147/173 | 23/61 |

Mutant carriers in the pooled set: katG S315T 105 (Guangdong 91, Bandung 8, Tamil Nadu 6), rpoB S450L 67 (Guangdong 59), inhA c.-15
19, gyrA D94G 6. Multiplex: tube 1 = inhA + gyrA, tube 2 = katG + rpoB (4 channels, 2 per assay, no conflict at −9 kcal/mol).

Sequences (5′→3′):

| Assay | Forward | Reverse | Probe WT | Probe mutant |
|---|---|---|---|---|
| inhA c.-15 | CTCGTGGACATACCGATTTC | CCAGGACTGAACGGGATAC | ACAACCTATCGTCTCGCCGCG | ACAACCTATCATCTCGCCGCG |
| gyrA D94G | ACCATGGGCAACTACCAC | GGCTTCGGTGTACCTCATC | TACGACACCCTGGTGCGCAT | TACGGCACCCTGGTGCGCAT |
| katG S315T | TCTCGAGGAAACTGTTGTCC | CTGGAAGAGCTCGTATGGC | ATCACCAGCGGCATCGAGGT | ATCACCACCGGCATCGAGGT |
| rpoB S450L | TTCATGGACCAGAACAACCC | GGTTTCGATCGGGCACAT | CGCCGACAGTCGGCGCTTGT | CGCCAACAGTCGGCGCTTGT |

(The rpoB pair is the same one designed on Bandung alone.) Probe Tm gaps: inhA 4.5 / 4.3 °C, gyrA 5.3 / 4.6, katG 3.4 / 9.5, rpoB 4.6 /
5.1 (wild-type / mutant).

**Weak points to quote honestly:** rpoB S450L exact matches by lineage: lineage 1 only 26 of 58, lineage 2 216 of 249, lineage 4 132 of
138. katG S315T specificity is 50 (2 near-matches in H37Rv). Coverage is in-sample.

### 7.2 What the rpoB S450L history teaches

- Bandung only: overall 83. First pooled rebuild: **61**, specificity 0, because at the strict 2% tolerance Primer3 returned only 20
  pairs with 2 distinct forward primers, both with 4-6 near-matches in H37Rv.
- At tolerance ≥ 5% the original pair returns (0 near-matches, conservation 84). The selection fix (section 4.2) picks it: **80**.
- The five rpoB designs sharing that pair improved by 18-22 points (H445D 74→93, H445Y 73→92, H445N 67→86, S450W 62→80).
- Tamil Nadu's low rpoB result (23 of 61) is mostly **one uncalled base at position 761152 inside the probe**: 39 isolates (30 of the 58
  lineage-1 isolates, 35 of the 39 are Tamil Nadu) have no base call there, with no variant in the VCF. It looks like a coverage dropout
  (Tamil Nadu has lower depth), not a polymorphism, but this was **not confirmed from raw reads**. The tool counts an uncalled base as a
  mismatch, so Tamil Nadu coverage is probably underestimated.

### 7.3 The library (205 targets)

- **192 designed**, 13 not: rpoB Asp435Val, Asp435Tyr, Asp435Gly, Asp435Glu, Asp435Ala, Leu452Pro, Gln432Pro, Gln432Leu, Met434Ile,
  Asn437Asp (dense RRDR, indels); pncA Leu27Pro, Thr135Pro; katG Ser315Arg.
- By drug (first listed drug): pyrazinamide 81, ethionamide 21, rifampicin 20, streptomycin 20, levofloxacin 17, ethambutol 13,
  isoniazid 5, amikacin 4, others fewer.
- Overall score: ≥ 80: 161 designs; 60-79: 30; under 60: 1. Exact-match share: ≥ 90%: 179; 80-90%: 12; under 80%: 1.
- Tolerance used: 2% for 138 designs, 5% for 47, 10% for 6, 20% for 1. 15 designs use the probe-room fallback.
- Specificity score distribution (192 designs, all BLAST-checked): 100 → 129, 75 → 32, 50 → 6, 25 → 5, **0 → 20**. The BLAST cache has 109
  pairs: 85 clean in all three groups, a few with NTM products, one with 43 predicted human products.
- Against the first BLAST-checked library, only 8 designs changed with the new selection rule: five rpoB designs up 18-22 points, rrl n.2814G>T +2 (63), rrs n.1484G>T −1 (74), ethA p.Ser399* −2 (85). rrs and rrl both have specificity 0.
- Oligo position checks (`figures/oligo_position_checks.csv`): all primers 0 mismatches against H37Rv.
- snippy and TB-Profiler disagree for gyrA and katG at a few isolates (documented in the figures work).

---

## 8. Interface

Static export of a Next.js app, served by `pnpm dev` on port 3000 or by the API container (`web/site`).

- **Layout:** report first; the assistant sits beside it and can be minimized to a rail (desktop) or bar (phone). A pulse and unread dot
  show activity while minimized; the choice is remembered in localStorage (`resisttb:assistant`).
- **Tabs:** *Results* and *Target library*. The library lists the 205 designable WHO variants, filterable by drug, with per-region exact
  matches and per-region resistance carriers; select up to 6 and design (`POST /api/design`, no model call).
- **Results:** ranked assay cards (scores, primers and probes, amplicon diagram, specificity, caveats), multiplex tubes, and a coverage panel
  with a **Region | Lineage** switch; an empty state in a new chat.
- **Assistant:** free-text chat (SSE with visible tool steps); transcript; *Chats* list with rename and delete; "New chat" keeps old ones.
- **Sessions:** IndexedDB database `resisttb` in the user's browser (max 50 chats, 20 reports per chat); report switcher per chat. The
  storage keys were renamed from `chatgp-tb` on 2026-10-25, so chats saved under the old name are no longer visible (the new domains also
  start with empty storage). Nothing is stored on a server.
- **Onboarding:** welcome card on first visit, reopened by "How it works"; numbers come from the loaded data; "Try an example"; a
  "Good to know" box (in silico, coverage is in-sample, chats are local); a guide to scores and terms.
- Files: `web/components/App.tsx`, `AgentPanel.tsx`, `ReportView.tsx`, `TargetLibrary.tsx`, `ReportSwitcher.tsx`, `Onboarding.tsx`;
  `web/lib/sessions.ts`, `useSessions.ts`, `library.ts`, `types.ts`, `report.ts`. `next.config.ts` switches to static export when
  `STATIC_EXPORT=1`. Build with `cd web && pnpm build:site` (output `web/site`).
- Next 16 differs from older versions; read `web/node_modules/next/dist/docs/` before changing routing or config (`web/AGENTS.md`).
- Not yet done: accessibility audit, real-phone test, CSV order-sheet export, share link (`?targets=`), compare view. `lib/mock.ts` demo
  data is still shipped as a fallback.

---

## 9. Cloud: what exists, specs, costs

Project **`haduh-512512`** (number 66604371416). Billing account `01D2B5-C86DC4-5860ED` (currency **IDR**). Owner user
`ahmadalfanihandoyo1@gmail.com`. Budgets "genohack-haduh" and "Rp500,000 Monthly budget alert" (IDR 500,000; email alerts at 50/90/100%
and 150%; **nothing stops spending automatically**). 36 APIs enabled (compute, storage, aiplatform, billingbudgets, cloudbilling, run,
artifactregistry, cloudbuild and others). Cloud Scheduler is not enabled.

### 9.1 What exists now (checked 2026-10-25)

| Resource | Details | Cost (my estimate from list prices, not the billing console) |
|---|---|---|
| Cloud Run service `resisttb` (asia-southeast1) | revision `resisttb-00001-nvs`, public (`allUsers` has `run.invoker`), min 0 / max 1 instance, 1 vCPU / 1 GiB, concurrency 4, timeout 120 s, service account `resisttb-run@haduh-512512.iam.gserviceaccount.com` (only `roles/aiplatform.user`), env `GENOHACK_PROJECT=haduh-512512`, `GENOHACK_LOCATION=global`. URL `https://resisttb-66604371416.asia-southeast1.run.app` | about $0 idle; Gemini usage per chat unmeasured |
| Bucket `gs://haduh-512512-genohack` (asia-southeast1) | `results/` (456 folders), `offtarget/` (803 MiB BLAST index), `vm-backup/` (isolates.tsv, logs, `offtarget_cache.json`), `deploy/` (run bundle, probably out of date), `runlogs/` | pennies per month |
| Bucket `run-sources-haduh-512512-asia-southeast1` | source zips from `gcloud run deploy --source` (about 6.7 MB) | pennies |
| Artifact Registry `cloud-run-source-deploy` | the `resisttb` image (older `chatgp-tb` images deleted) | about $0.02 per month |
| Domain mapping `resist-tb.afanhandoyo.com` → `resisttb` | Cloud Run domain mapping (preview feature; free); live | $0 |
| Service accounts | `resisttb-run` (Cloud Run), `genohack-vm` (storage.objectAdmin on the bucket; unused, kept for a future VM), default compute SA `66604371416-compute@` (roles/editor and `roles/cloudbuild.builds.builder`, needed for source deploys) | free |
| Firewall | `allow-iap-ssh` (35.235.240.0/20), `default-allow-icmp`, `default-allow-internal`, and **`default-allow-ssh` and `default-allow-rdp` still open to 0.0.0.0/0** (recommend deleting; not requested yet) | free |
| **Nothing else** | no VM, disks, snapshots, reserved IPs, Cloud Run jobs or scheduler jobs (checked) | |

Deleted on 2026-10-24 and 2026-10-25: first VM and 400 GB disk (earlier), VM `genohack-run-0` and its 100 GB disk (no snapshot), Cloud Run
`chatgp-tb`, service account `chatgp-tb-run` and its role, two `chatgp-tb` images.

Cost notes: the data VM ran about 6.5 hours for the main run plus two short boots for BLAST (about 8-9 hours on e2-standard-16 at about
$0.66/h including disk, so roughly $6-8 for this phase). The gcloud `beta` component was installed on the laptop on 2026-10-25.

### 9.2 Cloud Run architecture

One container per service: `python:3.13-slim`, FastAPI under uvicorn, the `genohack` package run from source (`PYTHONPATH=/app/src`), a
static Next.js export in `web/site` served by FastAPI, and Gemini on Vertex AI through `google-genai`. It copies `src`, `resources`,
`ref/NC_000962.3.fasta`, `ref/mask.bed`, `web/data/report.json`, `web/site`; it needs no results folder and no BLAST database. Deploys
from source: Cloud Build builds the image from the Dockerfile and pushes it to Artifact Registry. Rate limits are in memory per instance,
so they reset on a cold start and a public endpoint can still spend Gemini quota (bounded by the limits and the budget alert).

### 9.3 Custom domain `resist-tb.afanhandoyo.com` (Cloudflare DNS)

- Domain `afanhandoyo.com` is registered at Porkbun with **Cloudflare nameservers**; all DNS records are in Cloudflare.
- Done: Search Console domain verification (TXT at the apex, by `ahmadalfanihandoyo1@gmail.com`); mapping created with
  `gcloud beta run domain-mappings create --service resisttb --domain resist-tb.afanhandoyo.com --region asia-southeast1`; Cloudflare
  `CNAME resist-tb → ghs.googlehosted.com` set to **DNS only** (grey cloud). `dig` returns the CNAME and a Google address.
- Timeline: the mapping showed `Ready`, `CertificateProvisioned` and `DomainRoutable` all True at about 00:55 WIB, but for roughly an hour
  `curl` and `openssl s_client` got a connection reset after the client hello (the certificate had not reached all of Google's frontends).
  It then started answering by itself, with no change on our side: **HTTP 200, certificate issued by Google Trust Services (WR3), `/api/report`
  returns 456 isolates**. If a future mapping behaves the same, wait before debugging.
- If it ever fails again, check: the proxy is really off (grey cloud), no conflicting `A`/`AAAA`/`CAA` record on that name, Cloudflare DNSSEC
  settings, and `gcloud beta run domain-mappings describe --domain resist-tb.afanhandoyo.com --region asia-southeast1`. Fallbacks if the preview
  feature breaks: Cloudflare Worker reverse proxy (Host header must be the run.app host; rate limits would then see Cloudflare IPs unless the
  forwarded IP is read), Firebase Hosting rewrite, or a load balancer with a serverless NEG (about $18+ per month).
- Docs [30] say domain mapping is a preview feature, not production-ready, with latency issues.

---

## 10. Local environment

macOS laptop. Git-ignored: `results/`, `ref/`, `.venv/`, `web/node_modules`, `web/.next`, `web/.next-export`, `web/site`, `fasta_export/`.
Python 3.13 venv; Node 24 / pnpm 10; Next 16.4.3, React 19.3, Tailwind 4; gcloud 589.0.0 with `beta`; Chrome (headless, for PDFs);
BLAST+ 2.17 (unused locally). Preview configs: `/Users/afan/Documents/Repos/mtb-hackathon/.claude/launch.json` (`web` on 3000, `static-web` on 3100).

```bash
cd /Users/afan/Documents/Repos/mtb-hackathon/genohack
python -m venv .venv && .venv/bin/pip install -e . pytest
PYTHONPATH=src .venv/bin/python -m pytest -q                 # 35 passed, 1 warning
# run locally (two terminals)
GENOHACK_RESULTS=results PYTHONPATH=src .venv/bin/uvicorn genohack.api:app --port 8000
cd web && pnpm install && pnpm dev                            # http://localhost:3000
```

If `results/` is absent the API uses `resources/snapshot_windows.npz`. The agent needs a valid `gcloud` login (Application Default
Credentials). Dashboard URLs: local `http://localhost:3000`; live `https://resist-tb.afanhandoyo.com` (or `https://resisttb-66604371416.asia-southeast1.run.app`).

---

## 11. Scoring (as coded in `assay.score_assay`)

```
overall = 0.30*conservation + 0.30*thermodynamics + 0.20*specificity + 0.20*resistance_evidence
          (if evidence is missing: drop it and renormalise the other weights)
conservation   = 100 * exact_matches / isolates
thermodynamics = 100 * mean of five terms, each clipped to [0,1]:
   1 min(wt_gap, mut_gap) / 8          2 1 - |Tm_fwd - Tm_rev| / 3
   3 1 if 6 <= (min probe Tm - mean primer Tm) <= 12 else 1 - 0.15*(deg outside)
   4 (worst cross-dimer dG + 10) / 4   5 (worst hairpin dG + 4) / 2
specificity    = max(0, 100 - 25 * hits)    hits = H37Rv near-matches + BLAST predicted off-target products
evidence       = round(100 * highest WHO positive predictive value for the exact change)
```

Worked check, inhA: 97, 84, 100, 97 → 94. Interface coverage % is exact/isolates rounded **down** to one decimal. Panel "share of WHO
resistance" (lookup) matches on genome position **and** alt allele. Selection note: the ranking inside `_best_of_pairs` uses H37Rv
near-matches (so specificity affects the choice), but **BLAST products are added only after the choice**.

## 12. Threshold provenance (be honest about this)

Only a minority of thresholds have an external source; nothing was re-verified against a published guideline.

| Threshold | Value | Origin |
|---|---|---|
| Primer length / Tm / GC | 18-25 / 58-64 °C / 40-65% | common practice; TOAST (18-24, 58-80, 45-68) and PrimeGen (GC 40-62) read [20][21] |
| Amplicon | 70-160 bp | typical qPCR; a web result said 50-150 [27] |
| Salt / DNA | 50 mM Na⁺, 3 mM Mg²⁺, 0.8 mM dNTP, 250 nM | typical, from memory |
| Probe length / Tm / GC | 20-30 / 64-74 °C / 30-75% | typical TaqMan; patent example [27]; GC widened for inhA |
| Probe Tm above primers | 6-12 °C | patent example [27], lower bound loosened |
| No 5′ G; SNP ≥ 4 from ends | rules | TaqMan guidance (memory); mine |
| Tm gap target 8 °C; primer Tm match 3 °C | targets | mine; common guidance |
| Dimer: caution −7, conflict −9 kcal/mol | | widely quoted ≈ −9 limit, unverified |
| Hairpin band −2 to −4 | | team notes p. 47 (kJ/mol written, treated as kcal/mol) |
| Variable site MAF > 2% and ≥ 2 isolates | rule | mine |
| Last 3 bases of a primer = likely fail | rule | standard fact; "3" is mine; effect size depends on the master mix [31] |
| BLAST ≥ 16 bases, ≤ 2 mismatches, last 5 exact, ≤ 3 kb | rule | inspired by Primer-BLAST [18] |
| Specificity 25 per hit; weights 30/30/20/20 | rules | mine, not fitted |
| 4 channels, 2 per assay | assumption | typical instrument |
| Library inclusion: ≥ 10 resistant isolates | rule | mine (gives 205 from 212 candidates) |

There is no settings file; values are function defaults across modules.

## 13. Capabilities (summary)

- Process any set of public MTB Illumina runs into per-isolate calls: resumable, sharded, self-restarting, with timing metadata.
- Design on the **population consensus** of pooled regions; tolerance ladder instead of dropping hard targets; selection that backs off to
  looser tolerances when the strict pool is poor; probe-room fallback.
- Allele-specific probe pairs with Tm gap; per-isolate coverage with near-miss and 3′ failures; by lineage and by region.
- Off-target prediction (human, 7 NTM, 6 respiratory bacteria) with a pair-keyed cache; multiplex dimer screen and channel-limited tube
  grouping.
- 205-variant WHO library with drug names, evidence, per-region exact matches and resistance carriers; instant `/api/design`.
- Chat for drug, gene, variant, region and patient-scenario questions with code-enforced warnings; explains WHO variants it cannot design.
- Sessions, per-chat reports, onboarding, minimizable assistant, responsive layout.
- One-container hosting (API + static site) on Cloud Run with rate limits.

## 14. Limitations

**Science and data**
1. **In silico only.** Tm, dimer and probe gaps are model estimates; probe discrimination is modest (about 3-9 °C).
2. **Coverage is in-sample** (designed and measured on the same isolates). Held-out and leave-one-region-out tests are not done.
3. **Region labels are per BioProject**; Tamil Nadu is lineage-1 heavy (61 isolates, median depth 56x); per-region figures on small n are fragile.
4. **An uncalled base counts as a mismatch**, which probably underestimates Tamil Nadu and lineage-1 coverage (rpoB S450L: 23 of 61, lineage 1
   26 of 58). The cause (a coverage dropout at one probe base) is not confirmed from raw reads.
5. **Four isolates look contaminated or mixed** and are still in the design.
6. Mutant alleles are still rare for several targets (gyrA D94G 6 carriers); mutant probes are designed from the expected change.
7. Only near-fixed calls (1/1): no heteroresistance; 100x subsampling can lose minor variants; indels come from the VCF, not the FASTA.
8. **Not designed:** 12 variants in rpoB RRDR and pncA (dense or indel-rich; need multi-probe or melt design) and katG S315R; large-deletion
   and loss-of-function variants are excluded from the library.
9. The design assumes the consensus base at the SNP is the wild type; otherwise no probes.
10. **Specificity is a screen** (BLAST predicted products + H37Rv near-matches); in-silico specificity predicted wet-lab specificity poorly in
    other work [32]. 20 designs still score 0.
11. **Multiplex is a dimer screen only**; 4 channels is an assumption.
12. The score and weights are a transparent heuristic, not validated (section 12).
13. Not a diagnostic and no clinical advice; the agent declines prescribing questions.

**Engineering and operations**
14. Thresholds are scattered; no settings file. conda tools are not all pinned (snpeff is).
15. No CI. The container pins Python deps in `deploy/requirements.txt`.
16. The small Gemini model ignores some instructions; critical wording is in code. LLM cost per chat is not measured.
17. Public endpoint: rate limits are per instance in memory (reset on cold start; max 1 instance). Budget alerts are email-only.
18. Security hygiene: open SSH and RDP firewall rules, project-wide SSH key metadata (may still exist), no secrets in git (audit before
    today's changes).
19. Chats live in one browser only.
20. The custom domain uses Cloud Run domain mapping, a preview feature that Google does not recommend for production (section 9.3).
21. `deploy/genohack_run_bundle.tgz` in the bucket is probably out of date (it lacks `src/` and the new code).

---

## 15. Rebuild, redeploy and deploy runbook

### 15.1 Rebuild after any data or design change

```bash
cd /Users/afan/Documents/Repos/mtb-hackathon/genohack
bash scripts/sync_results.sh        # then verify every folder has its 6 files (see section 3, rule 4)
export PYTHONPATH=src
.venv/bin/python -m genohack.cli snapshot --results results
.venv/bin/python -m genohack.cli library --snapshot resources/snapshot_windows.npz
.venv/bin/python -m genohack.cli report --results results --snapshot resources/snapshot_windows.npz --out web/data/report.json
.venv/bin/python -m pytest -q
cd web && pnpm build:site           # -> web/site
```

**Run the steps one at a time and stop on the first error.** Piping into `tail` hides a failed `snapshot`, and the next steps then
rebuild from the old snapshot (this happened once). Check the new snapshot has 456 rows and `web/data/report.json` says 456 isolates.
New primer pairs that are not in `resources/offtarget_cache.json` show specificity "not checked" until BLAST is run (15.4).

### 15.2 Deploy to Cloud Run (the new service)

Prerequisites: `gcloud auth login` as the project owner; compute SA and Cloud Build SA hold `roles/cloudbuild.builds.builder`; `Dockerfile`
and `deploy/requirements.txt` exist. Check the upload set first: `gcloud meta list-files-for-upload .` should list about 75 files,
about 9 MB, with no `results/`, `fasta_export/` or `node_modules`.

```bash
gcloud run deploy resisttb --source . --project haduh-512512 --region asia-southeast1 \
  --service-account resisttb-run@haduh-512512.iam.gserviceaccount.com \
  --min-instances 0 --max-instances 1 --memory 1Gi --cpu 1 --concurrency 4 --timeout 120 \
  --set-env-vars GENOHACK_PROJECT=haduh-512512,GENOHACK_LOCATION=global
```

A redeploy keeps IAM. The first deploy of a new service used `--no-allow-unauthenticated`, was verified with an identity token
(`gcloud auth print-identity-token`), and was then made public with
`gcloud run services add-iam-policy-binding resisttb --member=allUsers --role=roles/run.invoker --region asia-southeast1 --project haduh-512512`.
Verify: `curl <url>/api/health`, `/api/report` (456 isolates, regions Bandung/Guangdong/Tamil Nadu), `POST /api/design` with
`{"targets":["rpoB_S450L"]}` (expect overall 80), and one `POST /api/chat`. The first call after idle can fail on a cold start; retry.
Service accounts: creating one and granting `roles/aiplatform.user` were IAM changes done with the user's approval.

### 15.3 Domain

See section 9.3. To add another domain: verify it in Search Console, `gcloud beta run domain-mappings create`, add the `CNAME` to
`ghs.googlehosted.com` with the proxy off.

### 15.4 When a VM is needed again (BLAST for new pairs, held-out validation)

The VM was deleted. Recreate it with the startup script and metadata (note the `^|^` delimiter because the project list contains commas):

```bash
gcloud compute instances create genohack-run-0 --project haduh-512512 --zone us-east4-a --machine-type e2-standard-16 \
  --boot-disk-size 100GB --boot-disk-type pd-balanced --image-family debian-12 --image-project debian-cloud \
  --service-account genohack-vm@haduh-512512.iam.gserviceaccount.com --scopes cloud-platform --labels project=genohack \
  --metadata-from-file startup-script=scripts/vm_startup.sh \
  --metadata "^|^BUNDLE=gs://haduh-512512-genohack/deploy/genohack_run_bundle.tgz|BUCKET=gs://haduh-512512-genohack|DESIGN_BIOPROJECT=<comma list>|SHARD_INDEX=0|SHARD_COUNT=1|MAX_HOURS=14"
```

**Rebuild the bundle first** (`scripts/ workflow/ envs/ resources/`, plus `src/` if you want the design code there). Setup installs miniforge,
snippy, tb-profiler, sra-tools, rasusa and snakemake at first boot (about 20-30 minutes).

**To run only BLAST** (what was done twice on 2026-10-24/25): the startup script shuts the VM down as soon as it sees the work complete, so
either leave `DESIGN_BIOPROJECT` pointing at isolates that are not yet done, or boot without the script (remove `startup-script` from the
metadata before booting, restore it afterwards). Then: arm a hard stop (`sudo shutdown -h +90`), upload a tarball of `src/`, `pyproject.toml`
and `resources/` (use `COPYFILE_DISABLE=1 tar` on the Mac to avoid noisy Apple attributes), unpack in `~/blast_run`, symlink
`ref/NC_000962.3.fasta` and `ref/mask.bed`, download `gs://haduh-512512-genohack/offtarget/*` into `ref/offtarget/`, activate the `design`
conda env (it has blastn, primer3-py, pandas, numpy), and run `PYTHONPATH=src python -m genohack.cli library --snapshot
resources/snapshot_windows.npz` detached (`nohup … &`). It adds each new pair to `resources/offtarget_cache.json`. Copy the cache back, copy it
to `gs://…/vm-backup/`, **stop the VM** and rebuild locally (15.1). The full library run took about 17 minutes with an empty cache, 13 with a
nearly full one. Detached SSH commands hang unless stdin and stdout are redirected.

### 15.5 Minimum to keep the prototype alive at lowest cost

Cloud Run (min 0) and the bucket (optional BLAST index). Idle cost about $0-1 per month plus Gemini calls.

---

## 16. Gotchas learned the hard way

- `gcloud` default project is not `haduh-512512`; always `--project`. SSH needs `--tunnel-through-iap`. `gcloud storage cp` to bucket paths with
  wildcards needs quoting.
- **zsh does not word-split unquoted variables**: `for p in $PAGES` and `P="--project x"` fail; use `${=VAR}` or write flags literally.
  macOS `sed -i` needs a suffix (`-i ''`); use `perl -pi -e` or the Edit tool. macOS has no `setsid`. `zcat` wants `.Z`; use `gzip -dc`.
- `pkill -f` and `pgrep -f` match their own command line over SSH; use the `[x]` trick (`pgrep -f "[g]enohack.cli"`).
- A chained `a | tail && b` hides a failure in `a`; run steps separately (see 15.1).
- **The VM startup script shuts the VM down when all isolates are done**, even if you only wanted a BLAST run. It also runs `rm -rf work/*` and
  `snakemake --unlock`. The watchdog timer (`genohack-watchdog.timer`) restarts a dead run; stop it before running a manual retry.
- **snpEff 5.3.0a needs Java 21** but the environment pins Java 17 → every isolate failed at TB-Profiler. Fixed with `snpeff=5.2`.
- **Truncated SRA downloads** show up as a rasusa read-count mismatch; the watchdog's restarts keep using SRA. Retry with `DOWNLOAD_SOURCE=ena`.
- `gcloud … --metadata` splits on commas; use `^|^`.
- Primer3 errors with more than 200 `SEQUENCE_EXCLUDED_REGION` items on diverse data; the code merges runs and returns no pairs above 200.
  At 2% tolerance the pooled rpoB pool is only 20 pairs; asking Primer3 for more (n=200) still returns 20.
- `*_LoF` names have positions but are not single changes → excluded (212 → 205).
- Small LLM: it misapplied number comparisons; warnings and assumption prefixes are generated in code.
- Next export mode: Cache Components and partial prefetch must be disabled; `STATIC_EXPORT=1` toggles them.
- Cloud Run: a new service cannot inherit the old name or URL; `*.run.app` URL form is
  `https://<service>-<project number>.<region>.run.app`. Cold start can make the first request fail.
- Cloud Run domain mapping: the certificate needs the CNAME unproxied; "provisioned" does not mean the frontends serve it yet.
- `results/` can contain `.DS_Store`; iterate directories only.
- A sync with the blocked `gcloud-crc32c` helper dropped a file once; verify counts and required files after every sync.
- Screenshots in the browser tool can be stale; verify with the DOM or logs.
- Background waits: `Monitor` with an `until` loop works; long SSH loops get moved to the background and can outlive their purpose (one ran
  for almost 2 hours until killed).

---

## 17. Validation: how to establish readiness and regional suitability

Research done on 2026-10-24 (web searches; the primary papers were not all read, so quote them carefully).

**Regional suitability (no lab needed)**
- Held-out coverage: design on the three regions, score the 779 other Indonesian runs (Wilson 95% intervals). Estimate: about 17 VM hours, $15-35.
- **Leave-one-region-out coverage:** design without one region, score on it. Needs no new data or VM time; the best next step.
- Per-lineage floor (minimum coverage across lineages 1, 2, 4), failure-mode split (3′ versus internal mismatches, uncalled versus variant).
- Marker prevalence by region, panel sensitivity against the WHO catalogue and TB-Profiler calls.
- Report coverage under more than one rule set: the 3′ mismatch rule changes the estimated detected fraction [31][33].

**Readiness (lab)**
- MIQE metrics [34]: PCR efficiency (typical acceptance 90-110%, R² ≥ 0.98), dynamic range, limit of detection (lowest concentration with
  ≥ 95% positives), inclusivity and exclusivity panels, mutant versus wild-type discrimination (ΔCq or allelic discrimination). The numeric
  targets are from memory, not from a cited source.
- Diagnostic accuracy against phenotypic DST with sequencing to resolve discordance, sensitivity and specificity with 95% intervals, compared with
  Xpert MTB/XDR (published: isoniazid about 96% and fluoroquinolones about 94% sensitivity in Anhui, 99.2% and 88.4% in Georgia) [35][36] and
  against the WHO target product profiles (August 2024) [37] (numeric thresholds not retrieved; read the document).
- Per-marker evidence: WHO catalogue predictive values [5][38].
- Stepwise path: held-out and leave-one-region-out coverage → panel sensitivity → BLAST on new pairs → synthetic-template (gBlock) wet-lab test at a
  partner lab → clinical DNA of known sequence versus phenotypic DST and Xpert.
- In silico predictions are not wet-lab results: Primer-BLAST-specific pairs often failed specificity in vitro in one study [32].

---

## 18. What's next (prioritised)

**Immediately**
1. **Custom domain:** live; keep an eye on it because domain mapping is a preview feature (section 9.3).
2. Decide on the open firewall rules `default-allow-ssh` / `default-allow-rdp` and the project-wide `ssh-keys` metadata (the user has not asked
   to delete them).
3. Re-run the secrets audit after today's changes (gitleaks); the earlier run found nothing in git.

**Validation and design quality**
4. **Leave-one-region-out** validation, then **held-out** validation (779 runs).
5. **Separate "uncalled" from "mismatch"** in `coverage_for` and report both; re-check Tamil Nadu rpoB (inspect the raw reads at 761152).
6. Decide whether to exclude the 4 contaminated isolates (SRR22256253, SRR37495362, SRR22256210, SRR22256266) and rebuild.
7. **BLAST-aware selection:** feed predicted off-target products into `_best_of_pairs` (needs BLAST at selection time, so on a VM) to lift the 20
   designs with specificity 0.
8. **Multi-probe or melt design** for the 12 undesigned rpoB/pncA variants and katG S315R.
9. Settings file with cited thresholds; pin conda tools; CI for tests; lock the container.
10. Heteroresistance-aware calling (TB-Profiler minor variants).
11. UI backlog: CSV order-sheet export, share link, compare view, accessibility audit, real-phone test, remove the mock fallback.
12. Measure Gemini cost per chat and consider a cap; add a persistent rate limit if the public endpoint is used widely.
13. Add the Philippines project when data is available; resolve the London accession.

**Business and research (see the "GenoHack business values" chat and `business.txt`)**
14. Mentors' feedback: position as a "Genomic Assay Intelligence Platform"; interview 5-8 customers; paid pilot → subscription → licensing; B2B
    sizing, pricing and ROI, financial projection and NPV, validation plan and IP, partnerships, 12-month plan, **two headline benefits**. The
    master document (p. 115, OCR) has an illustrative initial funding need of Rp1.45 billion across six buckets; the bucket values are not clean in the OCR.
15. Wet-lab validation with a partner lab; compare with Xpert MTB/RIF and Deeplex Myc-TB (tNGS; the team notes include a West Java
    implementation study and cost table).
16. Panel optimisation as in PrimeGen (SADDLE-style).
17. Update the master document and proposal wording to ResistTB if the name change is meant to apply there (the submitted draft says ChatGP-TB).

---

## 19. Decision log

| Decision | Why |
|---|---|
| Nextstrain-TB-style pipeline | proven structure; matches team notes |
| 100x subsample | average 370x; −70% compute |
| us-east4 for the VM | Singapore downloads stalled; no resume |
| SRA default, ENA opt-in | ~20% faster; ENA used only to rescue truncated SRA downloads |
| 6 isolates × 3 threads on 16 vCPU | CPU was half idle at 4 jobs; +17% throughput |
| On-demand VM, not Spot | avoids pre-emption restarts for a ~6-13 h run |
| Pooled design with region grouping | one panel that works across regions |
| Design on the population consensus | lineage polymorphisms would otherwise be penalised |
| Tolerance ladder, now with back-off when the best design has near-matches | a silently disappearing target is worse than a stated relaxation; the strict pool for rpoB was only 20 near-identical pairs |
| Specificity as predicted products | single-primer hits are meaningless in a 3 Gb genome |
| BLAST on a VM plus a pair-keyed cache | the index cannot be downloaded to the Mac |
| 205 targets (≥ 10 resistant isolates) | covers frequent variants; the rest are explained, not designed |
| Library as a tab plus `/api/design` | the dashboard should not depend on the chatbot |
| Snapshot instead of per-isolate files in the container | 733 KB versus 815 MB; same results |
| Code-enforced warnings | the small model ignores instructions |
| Sessions in IndexedDB, no accounts | no server cost or auth |
| Include the 4 low-quality isolates for now | effect believed small; left for a user decision |
| Delete the VM and disk with no snapshot (2026-10-25) | the user's call; everything is in git or the bucket, only conda envs are lost (20-30 min to rebuild) |
| Rename to ResistTB, new Cloud Run service and service account, delete the old ones | Cloud Run cannot rename; the user chose a clean rename including storage keys |
| Cloud Run domain mapping (not a load balancer) | free; load balancer about $18+ per month; mapping is a preview feature |
| Gemini 3.5 flash lite, location `global` | the user's choice; not offered in us-central1 |
| Cloud Run public with rate limits | the user asked for public access; budget alert as a backstop |

## 20. Repository map

```
README.md                  quick start (layout table partly outdated; this handover is current)
Dockerfile, deploy/        container (python:3.13-slim) and pinned requirements
pyproject.toml, envs/      package; conda envs (snippy, tbprofiler [snpeff=5.2], duckdb, design)
sql/indonesia_isolates.sql DuckDB query over SRA metadata
scripts/                   select_isolates, process_isolate, run_full, vm_startup, watchdog(+_vm), install_watchdog(+_vm),
                           progress, setup_vm, build_offtarget_db, build_who_subset, ena_isolates, summarize_partial,
                           sync_results, validation_figures, bench_download
workflow/                  Snakefile (DESIGN_BIOPROJECT list, shards), config.yaml
src/genohack/              genome, targets, isolates, variants, windows, primers, probes, thermo, checks, specificity, who,
                           multiplex, assay, snapshot, regions, library, lookup, agent, api, cli   (~2,230 lines)
resources/                 GFF, WHO subset, regions.csv, isolates_extra.tsv, snapshot_windows.npz, design_library.json,
                           offtarget_cache.json, sample_bioproject_fallback.csv
tests/                     test_genome, test_windows, test_multiplex, test_snapshot, test_targets, test_api, test_primers,
                           test_scenarios   (35 pass)
web/                       Next.js app: app/, components/, lib/, data/ (report.json, library.json)
figures/                   position validation, lineage presence/absence, CSVs
docs/                      HANDOVER.md, ResistTB_report.{html,pdf}, status_report, progress_report, pipeline_overview,
                           pipeline_explained (html + pdf each), refs.json, interface screenshots
fasta_export/              (git-ignored) per-isolate and combined FASTA for all 456 isolates, isolates.tsv
```

Recent commits (newest first, all on `main`): `a923266` handover URL; `ff7db7b` rename to ResistTB; `9570925` rebuild on 456, BLAST every design,
cleaner primers; `5c6a3b3` region_mutations lookup and optional region; `c7c2efa` country names as regions, list_capabilities tool;
`8646c0b` design on the named region only; `2568d29` empty results state; `ee57827` resistance carriers per region; `3aede94` handover v2;
`e6a0e7b` layout, minimize, onboarding; `8d87e9a` chat sessions.

## 21. Memory and context pointers

Memory notes (auto-loaded) are in `/Users/afan/.claude/projects/-Users-afan-Documents-Repos-mtb-hackathon/memory/`:
`feedback_push-genohack-freely.md` (standing permission to push this repo; HTTPS via keychain), `feedback_no-commit-attribution.md` (no
Co-Authored-By or Generated-with lines), `project_genohack-gcp.md` (cloud facts; refreshed 2026-10-25 for the ResistTB state). Reference
material in the parent folder: `GenoHack Master Document.pdf` (136 pages in the current file; Indonesian; proposal draft pp. 68-72; meeting
plan p. 81; business slides near p. 115) and `GenoHack Master Document - OCR.txt`. The transcript of this chat is
`/Users/afan/.claude/projects/-Users-afan-Documents-Repos-mtb-hackathon/cbe979e7-ae08-4171-b80f-63723135c7ab.jsonl` (id taken from the fork notice;
not verified on disk). Other transcripts are listed with `list_sessions` (section 3).

## 22. References and sources

R = read or fetched during this project. M = tool used; the citation was written from memory, check before submitting. S = found in a web
search, the source itself not read in full. N = from team notes, not read.

| # | Type | Reference | Status |
|---|---|---|---|
| [1] | Data | NCBI SRA / BioProject: PRJNA1433044 (Bandung), PRJNA1256943 (Tamil Nadu), PRJNA898845 (Guangdong); held-out PRJNA595834, PRJNA430531, PRJNA1150781, PRJNA633244, PRJNA950554. https://www.ncbi.nlm.nih.gov/bioproject/ | R |
| [2] | Data | SRA public metadata, AWS Open Data, s3://sra-pub-metadata-us-east-1/sra/metadata/ (DuckDB); ENA file reports, https://www.ebi.ac.uk/ena/portal/api/ | R |
| [3] | Data | H37Rv, NCBI RefSeq NC_000962.3. Cole ST et al. Nature 393:537-544 (1998). | M |
| [4] | Data | Ensembl Genomes ASM19595v2 (GCA_000195955.2), file from the TOAST repository (MIT). | R |
| [5] | Data | WHO. Catalogue of mutations in M. tuberculosis complex and their association with drug resistance, 2nd ed. (2023). https://github.com/GTB-tbsequencing/mutation-catalogue-2023 (MIT). | R |
| [6] | Data | Marin M et al. Benchmarking the empirical accuracy of short-read sequencing across the M. tuberculosis genome. Bioinformatics 38(7):1781-1787 (2022); BED from https://github.com/nextstrain/tb. | M |
| [7] | Data | Off-target genomes via NCBI Datasets, https://www.ncbi.nlm.nih.gov/datasets/ (human GRCh38 GCF_000001405.40; 7 NTM; 6 respiratory bacteria). | R |
| [8] | Software | Seemann T. snippy v4.6.0. https://github.com/tseemann/snippy | M |
| [9] | Software | Garrison E, Marth G. FreeBayes. arXiv:1207.3907 (2012) (1.3.6). | M |
| [10] | Software | Li H. BWA-MEM. arXiv:1303.3997 (2013). | M |
| [11] | Software | Phelan JE et al. TB-Profiler. Genome Medicine 11:41 (2019) (v6.6.5). | M |
| [12] | Software | Hall M. Rasusa. JOSS 7(69):3941 (2022) (v5.1.0). | M |
| [13] | Software | NCBI SRA Toolkit 3.2.1. https://github.com/ncbi/sra-tools | M |
| [14] | Software | Mölder F et al. Snakemake. F1000Research 10:33 (2021). | M |
| [15] | Software | Raasveldt M, Mühleisen H. DuckDB. SIGMOD 2019. | M |
| [16] | Software | Untergasser A et al. Primer3. Nucleic Acids Res 40(15):e115 (2012); primer3-py 2.4.0. | M |
| [17] | Software | Camacho C et al. BLAST+. BMC Bioinformatics 10:421 (2009) (2.17.0+). | M |
| [18] | Software | Ye J et al. Primer-BLAST. BMC Bioinformatics 13:134 (2012). Inspiration only. | M |
| [19] | Software | Google Cloud Vertex AI / Gemini (gemini-3.5-flash-lite, location global); google-genai; FastAPI https://fastapi.tiangolo.com; Next.js 16 https://nextjs.org/docs; Tailwind 4. | R |
| [20] | Prior work | Wang L et al. TOAST. BMC Genomics 26:1058 (2025). doi:10.1186/s12864-025-12247-9 ; https://github.com/linfeng-wang/TOAST | R |
| [21] | Prior work | Wang Y et al. PrimeGen. Nature Biomedical Engineering 10:338-353 (2026). doi:10.1038/s41551-025-01455-z | R |
| [22] | Prior work | Nextstrain TB build, https://github.com/nextstrain/tb (pipeline structure). | R |
| [23] | Prior work | Xie NG et al. SADDLE. Nature Communications 13:1881 (2022). Cited in PrimeGen; not used. | M |
| [24] | Prior work | Multiplex real-time PCR melting curve assay for drug-resistant TB mutations. J Clin Microbiol (2011). https://pubmed.ncbi.nlm.nih.gov/21752982 | S |
| [25] | Prior work | Comparative genomic analysis of established and emerging anti-tubercular drug targets in M. tuberculosis from Indonesia. Frontiers in Tropical Diseases (2026). doi:10.3389/fitd.2026.1953716 (team notes pp. 76-80; its supplementary tables S2-S4 are summarised there) | N |
| [26] | Prior work | GenoHack Master Document (team notes, Indonesian), meeting plan p. 81, draft proposal pp. 68-72; OCR in `GenoHack Master Document - OCR.txt` (also: Deeplex Myc-TB West Java tNGS evaluation pp. 11-17, CRyPTIC resources p. 26, tool table p. 39, business slide p. 115). | R |
| [27] | Thresholds | TOAST defaults and PrimeGen (read); a web result (patent text, not identified) for probe Tm and amplicon length; general qPCR practice from memory. | S |
| [28] | Cost | Google Cloud Billing Catalog API (E2 and balanced PD prices), https://cloud.google.com/billing/docs/how-to/get-pricing-information-api | R |
| [29] | Cloud | Cloud Run documentation (deploying from source, services, IAM); https://cloud.google.com/run/docs | S |
| [30] | Cloud | Cloud Run: Mapping custom domains (preview; supported regions include asia-southeast1; not recommended for production). https://docs.cloud.google.com/run/docs/mapping-custom-domains | S |
| [31] | Validation | Lefever S et al. Impact of basepair mismatch in primer annealing on qPCR assay performance (study of 3′ mismatches; effect depends on the master mix). https://www.econferences.de/impact-of-basepair-mismatch-in-primer-annealing-on-qpcr-assay-performance/ | S |
| [32] | Validation | Pitfalls during in silico prediction of primer specificity for eDNA surveillance (2020; Primer-BLAST-specific pairs rarely specific in vitro; BLAST predicted about 67% of outcomes). https://datadryad.org/dataset/doi:10.5061/dryad.41ns1rnb7 | S |
| [33] | Validation | In silico primer coverage with and without a 3′ mismatch rule (dengue case study). BMC Bioinformatics 19 (2018). https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-018-2313-0 | S |
| [34] | Validation | Bustin SA et al. The MIQE guidelines. Clinical Chemistry 55:611-622 (2009); summary https://www.aladdinsci.com/us_en/faqs/pcr-miqe-guidelines-en.html ; Bio-Rad bulletin 6262 | M/S |
| [35] | Validation | Evaluation of Xpert MTB/XDR, Anhui Province, China (2025). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12431546/ | S |
| [36] | Validation | Programmatic diagnostic accuracy of Xpert MTB/XDR in rifampicin-resistant TB, Georgia (medRxiv 2024). https://www.medrxiv.org/content/10.1101/2024.10.02.24314770.full.pdf | S |
| [37] | Validation | WHO. Updated target product profiles for TB diagnosis and detection of drug resistance (14 August 2024). https://www.who.int/news/item/14-08-2024-who-releases-updated-target-product-profiles-for-tuberculosis-diagnosis-and-detection-of-drug-resistance | S |
| [38] | Validation | The 2021 WHO catalogue of M. tuberculosis complex mutations associated with drug resistance: a genotypic analysis (38,215 isolates). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7612554/ | S |
