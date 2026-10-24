# ResistTB handover (version 2)

Written 2026-10-24 about 19:15 WIB (12:15 UTC), replacing the morning version. It is meant for a new chat that
continues the work. Facts were checked against the repo, the cloud project and the running VM on that date, unless a
line says "not verified". Read this file first, then `README.md`, then the memory notes (section 20).

Numbers in square brackets, like [8], refer to the reference list in section 21.

**The one thing to know first:** the data run on the VM (two new regions) is **still going** and will end around
21:00-21:15 WIB. Until it ends, the data in `results/` and in the live site are partial. Section 3 says what changes
at that moment, and section 15 is the exact runbook.

---

## 1. Summary

ResistTB turns public *Mycobacterium tuberculosis* (TB) genomes into qPCR primer and allele-specific probe designs for
drug-resistance variants. A cloud VM processes sequencing reads into per-isolate variant calls. A Python library then
designs primers and probes on the **population consensus** of those isolates, checks them against every isolate (overall,
by lineage, by region), screens for off-target amplification, scores them and checks multiplexing. A Gemini agent on
Vertex AI turns a free-text question into a design call; a Next.js interface shows the ranked assays, a browsable library
of designs for **205 WHO-catalogue resistance variants**, saved chats and one report per chat.
**Everything is in silico. Nothing has been tested in a tube.**

What changed since the morning handover (v1):

| Then (v1, 08:00-09:00 WIB) | Now (v2) |
|---|---|
| 4 hand-picked targets | 205 targets (4 hand-built + 201 generated from the WHO catalogue); 193 of 205 designed on Bandung data |
| Bandung only (222 isolates) | Pooled design over Bandung + Tamil Nadu (PRJNA1256943) + Guangdong (PRJNA898845), 456 isolates when the run ends; results are grouped by region |
| Runs on a laptop only | Cloud Run service is live and public (old build, see 9.2) |
| Chat picks one of 4 targets | Chat finds any WHO variant by drug/gene/name, explains out-of-scope ones, handles patient-scenario questions |
| One report | Chats are saved in the browser, each with its own reports; target library tab; minimizable assistant; onboarding |
| VM `genohack-analysis-us` (400 GB) | VM `genohack-run-0` (100 GB), a new startup script and a stall watchdog; the old VM and disk were deleted |

Team (from the master document): Hanifa Syifa Kamila, Yudisto P Nadapdap, Hefina Aissa Gunawan, Ahmad Alfani Handoyo.
**Deadline for the proposal was 15:00 WIB on 2026-10-24** (3 A4 pages). Whether it was submitted is not known to this
chat; the draft is in the master document, pages 68-72.

---

## 2. Status snapshot (2026-10-24 ~19:15 WIB)

| Area | State |
|---|---|
| Stage A, Bandung 222 isolates | **Done.** 222 result folders in the bucket |
| Stage A, new regions (234 runs) | **Running** on `genohack-run-0`: about 150 of 234 done at 12:12 UTC; 6 isolates at once; rate 45-47 isolates/hour; ETA 14:00-14:15 UTC (21:00-21:15 WIB). 27 retries so far, 0 gave up |
| Design library (Python) | **Done**, 34 tests pass, 1 skipped |
| WHO target library | **Done**: 205 targets, 193 designed on Bandung-only data |
| Agent (Gemini) + API | **Done** (tested on partial pooled data) |
| Web interface | **Done** (sessions, library, minimize, onboarding) |
| Tracked data in git (`web/data/*.json`, `resources/design_library.json`, `resources/snapshot_windows.npz`) | **Bandung-only.** Not yet rebuilt on pooled data |
| Cloud Run `resisttb` | **Live, public, but an old build** (4 targets, Bandung-only, no sessions) |
| Rebuild on pooled data + redeploy | **Waiting for the VM run** |
| Delete VM and disk | **Waiting for the user's explicit OK** |
| Held-out validation (other Indonesian projects, 779 runs) | Not started |
| Wet-lab validation | Not started (out of scope) |
| Business case | Separate chat, see section 18 |

Repo: `github.com/blueguy42/genohack` (private), branch `main`, 51 commits, HEAD `e6a0e7b`
("Report-first layout, a minimizable assistant and onboarding"). Local path
`/Users/afan/Documents/Repos/mtb-hackathon/genohack`.

---

## 3. Parallel chats and shared state (read before touching anything)

Several Claude sessions work in the same folder. They share **one git working tree, one branch (`main`), one cloud
project, one VM and the same local ports**. That is the main source of confusion.

| Session | What it is | State / what to know |
|---|---|---|
| `local_80dcbe51…` "Active Google Cloud resources" | Parent of this chat. Cloud audits, deletion of the first VM/disk, Cloud Run deploy and public access, region support, VM run and watchdog, chatbot/library/sessions/layout work (through forks) | Last reported 104/234 at 11:16 UTC. Knows Cloud Run is live and public |
| `local_6e8a81cd…` (this chat) | Fork of the parent. Built regions, WHO targets, library, scenarios, sessions, layout, onboarding, and this handover | Ends here |
| `local_c43d11a6…` "Active Google Cloud resources (fork)" | Fork; explained Fig. 5 | Idle. **Its statement that the backend runs only on the laptop is outdated** (Cloud Run is live) |
| `local_cec39fb2…` "Genohack secrets audit" | Ran gitleaks 8.30.1 | Git history: 0 findings. 12 working-tree hits, all inside the ignored build cache `web/.next/` (keys in compiled output, not source). No secret in git |
| `local_bca5dc77…` "GenoHack business values" | Pitch and commercial slides, competitor table (Primer3, TOAST, PrimeGen, Xpert), positioning from mentor feedback | No code changes. Mentors said: highlight two benefits |
| `local_995b932e…` "NCBI project metadata retrieval" | The original builder session (1,400+ messages). Built the pipeline, v1 design, first deploy of docs. Committed `b5c7bf0` (docs, `.gitignore`) | Source of the old decisions; ask it for history, not for current state |
| Other sessions (meeting-transcriber, Tap-Twice, INA Digital Edu, Personal Website, Sahaba) | Unrelated projects | Ignore |

**Rules that avoid collisions**

1. **Never run `git add -A` or `git commit -a`.** The working tree has two uncommitted files that must not be committed:
   `web/data/library.json` and `web/data/report.json` are currently *partial pooled copies* (277 isolates) used for local
   testing. The tracked versions are Bandung-only. Commit only the files you changed, by name. Restore with
   `git checkout web/data/library.json web/data/report.json` if you need the tracked versions, and regenerate when the run ends.
2. **One VM only.** `genohack-run-0` is the only compute resource. Do not start a second VM for the same task. Do not stop,
   resize or delete it while the run is going. Do not run heavy jobs on it (they slow the run).
3. **Local ports:** the web dev server is on 3000 and a local API on 8000 (started from this chat with a partial snapshot and
   rate limits off). Another chat starting `pnpm dev` or `uvicorn` will clash; check with `lsof -i :3000 -i :8000`.
4. **`results/` is a shared cache**, synced from the bucket by `scripts/sync_results.sh`. It currently has 290 finished isolates
   (Bandung 222, Guangdong 52, Tamil Nadu 16). Another chat synced it earlier. A test (`tests/test_snapshot.py`) skips its
   snapshot-versus-results comparison when the committed snapshot differs from `results/`; that skip is expected until the rebuild.
5. **`gcloud` default project on the laptop is `tap-twice-aurania`.** Always pass `--project haduh-512512`.
6. **Cloud actions needing approval:** enabling APIs, IAM changes, instance/snapshot deletion were blocked by the permission
   classifier earlier; the user allowed or ran them. Do not work around a block; give the command to the user.
7. `fasta_export/` (564 MB, git-ignored), `ncbi_metadata/`, `papers/`, `GenoHack Master Document.pdf` and `business.txt` live in
   the parent folder or are ignored; another chat created `fasta_export/`.
8. Docs from other chats: `docs/pipeline_explained.{html,pdf}` (my explainer, committed by `b5c7bf0`). Do not overwrite it.

---

## 4. Pipeline overview

```
 public data                    Stage A: VM (Snakemake, per isolate)                       Stage B: design library (Python)                 Stage C
 ───────────                    ────────────────────────────────────                       ────────────────────────────────                ─────────
 SRA metadata (DuckDB)  ──▶  fasterq-dump ──▶ rasusa 100x ──▶ snippy (BWA-MEM+FreeBayes) ──▶ snapshot (±300 bp windows, 205 targets)  ──▶ Gemini agent
 BioProject accessions        reads             subsample       vs H37Rv NC_000962.3          + lineage + region per isolate                (Vertex AI,
 ENA run lists                                                   │                           ──▶ consensus, variable-site mask             function calls)
                                                                 └▶ TB-Profiler 6.6.5        ──▶ Primer3 primers, allele-specific probes    ──▶ FastAPI
                                                                    (lineage, resistance)    ──▶ tolerance ladder 2→5→10→20 %                 /api/chat (SSE)
                                                                 ──▶ results/<run>/ in GCS   ──▶ BLAST specificity (cached)                   /api/design
                                                                     + DONE marker           ──▶ coverage: exact / 1 mismatch / likely fail   /api/report
                                                                                             ──▶ WHO evidence (PPV), score, multiplex tubes ──▶ Next.js UI
                                                                                             ──▶ design library (205 targets)                 (static export)
```

A full diagram with every tool is in `docs/pipeline_overview.pdf` (3 pages) and `docs/pipeline_explained.pdf`.

### 4.1 Stage A: per-isolate processing (cloud VM)

Modelled on the Nextstrain TB build [22]. Orchestrated by Snakemake [14] (`workflow/Snakefile`; one rule per isolate; random
fixed-seed order so partial results are a fair sample). Per isolate, `scripts/process_isolate.sh <run> <threads> <coverage>`:

1. **Skip** if `gs://haduh-512512-genohack/results/<run>/DONE` exists.
2. **Download** with `fasterq-dump` (sra-tools 3.2.1 [13], `--split-files`) from NCBI SRA. ENA (curl) is opt-in (`DOWNLOAD_SOURCE=ena`).
3. **Subsample** to 100x with `rasusa` 5.1.0 [12] (`--genome-size 4.4mb --seed 100`). Average coverage is about 370x, so this cuts compute by about 70%.
4. **Call variants** with `snippy` 4.6.0 [8] against H37Rv: BWA-MEM [10] then FreeBayes 1.3.6 [9]
   (`-p 2 -P 0 -C 2 -F 0.05 --min-coverage 10 --min-repeat-entropy 1.0 -q 13 -m 60`). All calls are genotype 1/1, minimum depth 10.
5. **Profile** with `tb-profiler profile` 6.6.5 [11]: lineage and drug-resistance calls. (Needs `snpeff=5.2`, see section 16.)
6. **Keep** `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, `<run>.results.json`, `metadata.json` (per-step seconds, bytes, versions);
   upload to the bucket; write `DONE` last; delete reads and intermediates.

Run settings: 6 isolates at once × 3 threads, Snakemake `--cores nproc+2 --keep-going --retries 2 --rerun-incomplete` on e2-standard-16.
Measured median seconds per isolate (under 6-way parallelism): Bandung 851, Tamil Nadu ~515-519, Guangdong ~435-438.
Selection of isolates: `sql/indonesia_isolates.sql` (DuckDB over SRA metadata, 1,001 Indonesian runs) and
`scripts/ena_isolates.py` (run lists for given BioProjects, wrote `resources/isolates_extra.tsv`, 234 runs).
Sharding is supported (`SHARD_INDEX`/`SHARD_COUNT`, `DESIGN_BIOPROJECT` comma list) but the run uses one shard.

**VM automation (new):**
- `scripts/vm_startup.sh` runs at every boot from instance metadata (`BUNDLE`, `BUCKET`, `DESIGN_BIOPROJECT`, `SHARD_INDEX`, `SHARD_COUNT`, `MAX_HOURS=14`). It creates the user `runner`, installs the environment (miniforge, snippy, tb-profiler, sra-tools, rasusa, snakemake), writes `/etc/genohack-run.env`, starts the run, installs the watchdog, copies logs to `gs://…/runlogs/genohack-run-0/` every 10 minutes, and schedules a hard stop `MAX_HOURS` after boot.
- `scripts/watchdog_vm.sh` + `install_watchdog_vm.sh`: kills an isolate running longer than 1 hour, restarts a dead run, and shuts the VM down after 3 restarts without progress. It reads `/etc/genohack-run.env` so the project list and shard settings are kept.
- The VM shuts down by itself when the run completes. Disk continues to bill until deleted (about $0.37/day for 100 GB).

### 4.2 Stage B: design library (`src/genohack/`)

| Step | Module | What it does | Key settings |
|---|---|---|---|
| Targets | `targets.py` | `all_targets()`: 4 hand-built (rpoB S450L, katG S315T, inhA c.-15, gyrA D94G) + WHO targets generated from the catalogue: single-base changes with a genome position, name matching `_SPECIFIC` (p.Xxx123Yyy, p.Xxx123*, p.Xxx1?, c.-14C>T, n.1401A>G), at least 10 resistant isolates (`MIN_RESISTANT`), deduplicated by (pos, alt) → **205 targets** | `*_LoF` entries are excluded (not single changes) |
| Snapshot | `snapshot.py` | `resources/snapshot_windows.npz`: ±300 bp windows for all 205 targets for every isolate + lineage + region. A few MB; lets the deployed service run without the 500 MB of per-isolate files | `GENOHACK_SNAPSHOT` (auto-used when `results/` is missing) |
| Variant table | `isolates.py`, `variants.py` | base code per isolate per position (ACGT, MISSING, N), indel flags from VCF, consensus base, minor-allele frequency, masked flag | variable site = MAF > tolerance **and** ≥ 2 isolates |
| Primers | `primers.py` | Primer3 [16] on the consensus; excluded: variable, masked, indel or missing sites; amplicon must contain the SNP; excluded regions merged into runs because Primer3 allows at most 200 (more → no pairs) | length 18-25, Tm 58-64, GC 40-65, poly-X ≤ 4, product 70-160, 20 pairs |
| Probes | `probes.py` | wild-type from consensus, mutant = one base changed; Tm gap via Primer3 thermodynamic alignment against the other allele | 20-30 nt, Tm 64-74, GC 30-75, no 5′ G, SNP ≥ 4 from ends |
| Assemble | `assay.py` | picks the probe inside the amplicon 6-12 °C above primers with the best gap; **tolerance ladder 2% → 5% → 10% → 20%**; **probe-room fallback** (primers kept 26 bp from the SNP, 3× pairs) only when the normal attempt fails (rrs n.1401A>G is designed this way, score 96) | |
| Checks | `checks.py`, `specificity.py`, `thermo.py` | hairpin / self-dimer / cross-dimer dG; H37Rv near-match scan; BLAST predicted off-target products | |
| Coverage | `assay.coverage_for` | per isolate: **exact**, **one mismatch**, **likely fail** (≥ 2 mismatches, or 1 in the last 3 bases of a primer); grouped `by_lineage` and `by_region` | SNP position must be called |
| Evidence | `who.py` | best WHO positive predictive value for the exact change | grade 1-2 slice |
| Score | `assay.score_assay` | section 11 | 30/30/20/20 |
| Multiplex | `multiplex.py` | all cross-assay oligo pairs, worst dimer dG, tube grouping | caution −7, conflict −9 kcal/mol; 4 channels, 2 per assay |
| Library | `library.py` | designs every target once, stores a summary (`resources/design_library.json`, copied to `web/data/library.json`) incl. `by_region` exact matches and drug names | per-target error guard |
| Lookup | `lookup.py` | `find_targets(query)`, `DRUG_ALIASES`, suggested panel (top 4 designed targets, with share of WHO resistance covered, matched on pos+alt), `weak_panel_note`, `limit_note`, `names_a_target` | `PANEL_SIZE=4` |
| Regions | `regions.py` | `resources/regions.csv` (BioProject → label): PRJNA1433044 Bandung, PRJNA1256943 Tamil Nadu, PRJNA898845 Guangdong; fallback `resources/sample_bioproject_fallback.csv` | |

**Specificity:** primer binding site = BLAST (`blastn-short`, word size 7) alignment of ≥ 16 bases, ≤ 2 mismatches, no gaps, last 5
bases exact; a **predicted product** = plus-orientation site followed within 3,000 bases by a minus-orientation site, same
sequence. Groups: human, ntm, flora. Single-primer hits are not counted. The 803 MiB BLAST index exists only on a VM and in the
bucket; the app reads `resources/offtarget_cache.json` keyed by primer pair. **A pair with no cache entry reports
specificity as "not checked".** Most of the 205 library designs are in that state.

### 4.3 Stage C: agent, API, interface

**Agent** (`agent.py`): Gemini `gemini-3.5-flash-lite` on Vertex AI [19], location `global`, `google-genai` function calling,
up to 5 turns. Tools: `find_targets(query)` (resolve a drug, gene, variant or free text to target ids) and
`design_assays(targets)` (≤ 6 ids, `MAX_TARGETS`). The model sees a compact summary (`_compact`): scores, sequences, a ready-made
region sentence ("In Bandung, N of M isolates match every oligo exactly; k is/are likely to fail"). **The model never emits numbers.**
Because the small model ignores some instructions, critical wording is **enforced in code**: `limit_note`, `weak_panel_note`, and an
assumption prefix ("You did not name a drug, so this looks at …") when no drug, gene or regimen is named. Prompt rules cover
patient-scenario questions (a group not improving on a drug → suggested panel; "[drug]" placeholders → ask which drug).
Out of scope and declined: prescribing advice, unrelated topics. WHO variants not designed are explained, not designed.

**API** (`api.py`, FastAPI): `GET /api/health`, `GET /api/report`, `POST /api/chat` (SSE events `step`, `report`, `text`, `error`, `done`),
`POST /api/design` (no model call; used by the library tab). Rate limits (`RateLimit` class): chat 20/IP/hour and 300/day; design
60/IP/hour and 1,500/day. Overrides: `GENOHACK_CHATS_PER_IP_HOUR/DAY`, `GENOHACK_DESIGNS_PER_IP_HOUR/DAY`. CORS: `GENOHACK_ORIGINS`
list if set, otherwise any localhost/127.0.0.1/[::1] port. If `web/site` exists the API also serves the static page, so one
container is the whole site. Other env: `GENOHACK_RESULTS`, `GENOHACK_SNAPSHOT`, `GENOHACK_PROJECT`, `GENOHACK_LOCATION`,
`GENOHACK_MODEL`, `GENOHACK_BLAST_DB`.

**Web** (`web/`, Next.js 16.4.3, React 19.3, Tailwind 4): see section 8.

---

## 5. Inputs and outputs

**Inputs**
1. Public reads: Bandung PRJNA1433044 (222 runs, 174 GB), Tamil Nadu PRJNA1256943 and Guangdong PRJNA898845 (234 runs together).
2. H37Rv NC_000962.3, gene annotation, low-confidence mask.
3. WHO 2023 mutation catalogue (grade 1-2 slice).
4. Off-target genomes for BLAST (on the VM / bucket).
5. A chat message or a library selection (up to 6 variants).

**Outputs**
1. Per isolate in `gs://haduh-512512-genohack/results/<run>/`: `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, `<run>.results.json`, `metadata.json`, `DONE`.
2. Derived artefacts committed to git: `resources/snapshot_windows.npz`, `resources/design_library.json`, `web/data/library.json`, `web/data/report.json`.
3. Per request: a report JSON (schema `web/lib/types.ts`): ranked assays with primer pair, WT and mutant probes (sequence, coordinates, strand, Tm, hairpin/self-dimer dG, Tm gap), four scores, coverage overall / by lineage / by region, specificity, reasons, caveats, multiplex pairs and tubes, step timings, `dataset` (isolate count, regions).
4. A chat reply; the interface rendering the report.
5. Figures and tables: `figures/` (position validation, lineage deletions) and the docs.

---

## 6. Datasets

| Dataset | Source | Size / count | Where | Note |
|---|---|---|---|---|
| SRA metadata [2] | AWS open data, queried with DuckDB | 1,001 Indonesian Illumina MTB runs | VM only, regenerate with `scripts/select_isolates.sh` | public |
| Bandung reads [1] | PRJNA1433044 (Universitas Padjadjaran) | 222 runs, 174 GB | processed, 222 result folders | design set (original) |
| Tamil Nadu reads | PRJNA1256943 | in `resources/isolates_extra.tsv` | processing | region "Tamil Nadu" |
| Guangdong reads | PRJNA898845 | in `resources/isolates_extra.tsv` (234 new runs for both) | processing | region "Guangdong" |
| H37Rv [3] | NCBI NC_000962.3 | 4,411,532 bp | `ref/NC_000962.3.fasta` (git-ignored; copied into the container) | |
| Gene annotation [4] | Ensembl ASM19595v2 via TOAST repo | 4,018 genes | `resources/H37Rv_ASM19595v2.gff` | chromosome named `Chromosome` there |
| Low-confidence mask [6] | `nextstrain/tb` BED | 1,324 regions, 276,750 bases | `ref/mask.bed` (downloaded; copied into the container) | |
| WHO catalogue 2023 [5] | GTB-tbsequencing | grade 1-2: 1,383 rows, 1,291 variants, 643 with SNV coordinates | `resources/who_catalogue_2023_assoc_with_R.csv` | MIT |
| Off-target BLAST db [7] | NCBI Datasets: human GRCh38, 7 NTM, 6 respiratory bacteria | 729 sequences, 3.37 Gb, index 803 MiB | bucket `offtarget/`, VM only | not on the laptop (Gatekeeper) |
| Snapshot | this project | 205 targets × ±300 bp × isolates | `resources/snapshot_windows.npz` (Bandung-only, 222 isolates today) | few MB |
| Per-isolate results | this project | 531 MiB for 364 folders at 12:08 UTC | bucket + `results/` (ignored) | |

**Held-out candidates (not processed):** PRJNA595834 (387 runs), PRJNA430531 (314), PRJNA1150781 (42, Papua), PRJNA633244 (30, Java MDR),
PRJNA950554 (6): 779 Indonesian runs. **Rejected or pending:** PRJEB84199 (London) accession could not be resolved; PRJNA725239 was
discussed and dropped; a Philippines project is pending data; PRJNA1480927 was considered.

**Data caveats:** BioProject-level region labels are coarse (one country-province per project). Lineage mix differs strongly by
region (Guangdong is mostly lineage 2, Tamil Nadu mostly lineage 1, Bandung mostly 4 and 2), so a pooled design is dominated by
the larger sets and per-region exact matches can be lower than overall.

---

## 7. Results so far

**Bandung only (222 isolates), tracked in git**

| Assay | Overall | Exact match | Notes |
|---|---|---|---|
| inhA promoter c.-15C>T (1,673,425) | 94 | 221/222 | tube 1 with gyrA |
| gyrA p.Asp94Gly (7,582) | 87 | 205/222 | needed relaxed tolerance; WT probe has 1 base differing at 7585 (consensus) |
| katG p.Ser315Thr (2,155,168) | 85 | 219/222 | specificity 50: 2 near-matches in H37Rv; tube 2 with rpoB |
| rpoB p.Ser450Leu (761,155) | 83 | 212/222 | weakest thermodynamics (50) |

- 0 BLAST off-target products for all four pairs. No multiplex conflicts at −9 kcal/mol; 4 pairs at "caution".
- Oligo position checks (`figures/oligo_position_checks.csv`): all primers 0 mismatches against H37Rv; reproduces the TOAST/eLife-style check.
- snippy / TB-Profiler disagree for gyrA and katG at a few isolates (documented in the figures work).
- Library on Bandung: **193 of 205 designed**. Undesigned: 10 rpoB (dense, indels; e.g. Asp435Val seen in 1,154 isolates across the catalogue) and 2 pncA.

**Partial pooled (277 isolates, laptop only, not committed)**: rpoB S450L overall 82; S450L per region exact matches Bandung 212/222,
Guangdong 36/43, Tamil Nadu 6/12; inhA c.-15 Tamil Nadu 9/12; library 189/205 designed. **These will change when the run completes; do not quote them.**

**Dataset mix (290 finished isolates synced on 2026-10-24):** Bandung 222 (lineage 4 117, lineage 2 94, lineage 1 8, mixed 3; Sensitive 180, Other 21,
HR 9, MDR 8, RR 4); Guangdong 52 (lineage 2 48, 4 3, 1 1; MDR 21, pre-XDR 13, Sensitive 13, Other 3, XDR 1, HR 1); Tamil Nadu 16
(lineage 1 12; Sensitive 10, HR 3, Other 2, MDR 1). The new regions add many more resistant isolates, which is the main gain.

**Sequences (Bandung design, 5′→3′)**

| Assay | Forward | Reverse | Probe WT | Probe mutant |
|---|---|---|---|---|
| inhA c.-15 | CTCGTGGACATACCGATTTC | CCAGGACTGAACGGGATAC | ACAACCTATCGTCTCGCCGCG | ACAACCTATCATCTCGCCGCG |
| gyrA D94G | ACCATGGGCAACTACCAC | GGCTTCGGTGTACCTCATC | TACGACACCCTGGTGCGCAT | TACGGCACCCTGGTGCGCAT |
| katG S315T | TCTCGAGGAAACTGTTGTCC | CTGGAAGAGCTCGTATGGC | ATCACCAGCGGCATCGAGGT | ATCACCACCGGCATCGAGGT |
| rpoB S450L | TTCATGGACCAGAACAACCC | GGTTTCGATCGGGCACAT | CGCCGACAGTCGGCGCTTGT | CGCCAACAGTCGGCGCTTGT |

These will be re-derived on pooled data; they may change.

---

## 8. Interface (what the user sees)

Static export of a Next.js app, served either by `pnpm dev` (port 3000) or by the API container (`web/site`).

- **Layout:** report first; the assistant sits beside it and can be **minimized** to a rail (desktop) or bar (phone). A "working" pulse and an unread dot show activity while minimized; the choice is remembered in localStorage.
- **Tabs:** *Results* and *Target library*. The library lists the designable WHO variants (205), filterable by drug, with per-region exact-match columns; select up to 6 and design (`POST /api/design`, no model call).
- **Results:** ranked assay cards (scores, primers and probes, amplicon diagram, specificity, caveats), multiplex tubes, and a coverage panel with a **Region | Lineage** switch (shown whenever region data exists).
- **Assistant:** free-text chat (SSE streaming with visible tool steps); transcript; *Chats* list with rename and delete; "New chat" keeps old ones.
- **Sessions:** stored in IndexedDB in the user's browser (max 50 chats, 20 reports per chat); the report switcher moves between a chat's reports; the page's own default is "Starting report: the 4 main targets". Nothing is stored on a server.
- **Onboarding:** a welcome card on the first visit, reopened by "How it works"; numbers come from the loaded data; "Try an example" button; a "Good to know" box (in silico, coverage is in-sample, chats are local); a collapsible guide to scores and terms.
- Files: `web/components/App.tsx`, `AgentPanel.tsx`, `ReportView.tsx`, `TargetLibrary.tsx`, `ReportSwitcher.tsx`, `Onboarding.tsx`; `web/lib/sessions.ts`, `useSessions.ts`, `library.ts`, `types.ts`, `report.ts`. `next.config.ts` switches to static export when `STATIC_EXPORT=1` (Cache Components / partial prefetching are disabled in that mode).
- Next 16 differs from older versions; read `web/node_modules/next/dist/docs/` before changing routing or config (`web/AGENTS.md`).
- Not yet done: accessibility audit, real-phone test, CSV order-sheet export, share-link (`?targets=`), compare view. `lib/mock.ts` demo data is still shipped as a fallback.

---

## 9. Cloud: what exists, what it costs

Project **`haduh-512512`** (number 66604371416). Billing account `01D2B5-C86DC4-5860ED` (currency **IDR**). Owner user:
`ahmadalfanihandoyo1@gmail.com`. Budgets: "genohack-haduh" and "Rp500,000 Monthly budget alert" (IDR 500,000, 50/90/100% (and 150%) email
alerts; **nothing stops spending automatically**). Quotas: E2_CPUS 24 per region, CPUS_ALL_REGIONS 32.

### 9.1 Compute and storage

| Resource | Details |
|---|---|
| VM `genohack-run-0` | us-east4-a, **e2-standard-16** (16 vCPU, 64 GB), Debian 12, boot disk 100 GB `pd-balanced`, on-demand (not Spot), SA `genohack-vm`, label `project=genohack`, created 08:33 UTC. **RUNNING**. Hard stop scheduled about 22:33 UTC (`MAX_HOURS=14`). Reach: `gcloud compute ssh genohack-run-0 --project haduh-512512 --zone us-east4-a --tunnel-through-iap` |
| Bucket `gs://haduh-512512-genohack` (asia-southeast1) | `results/` (531 MiB, 364 folders at 12:08 UTC), `offtarget/` (803 MiB BLAST index), `vm-backup/` (10 MiB; isolates.tsv, logs, offtarget_cache.json), `deploy/` (27 KiB run bundle), `runlogs/` (239 KiB) |
| Bucket `run-sources-haduh-512512-asia-southeast1` | Cloud Run source uploads (created by `gcloud run deploy --source`) |
| Artifact Registry `cloud-run-source-deploy` | container images, about 110 MB |
| Nothing else | no other disks, snapshots or reserved IPs (checked) |

### 9.2 Cloud Run `resisttb` (asia-southeast1)

URL `https://resisttb-zqrp2hdbia-as.a.run.app`, **public** (`allUsers` has `run.invoker`), revision `resisttb-00001-tjp`, min 0 / max 1 instance, 1 vCPU / 1 GiB,
concurrency 4, timeout 120 s, service account `resisttb-run@haduh-512512.iam.gserviceaccount.com` (only `roles/aiplatform.user`),
env `GENOHACK_PROJECT=haduh-512512`, `GENOHACK_LOCATION=global`. It runs the **old build** (4 targets, Bandung only, 9 KB snapshot,
no regions, library or sessions). A redeploy is part of the runbook (section 15). Public means anyone can spend Gemini quota, bounded by the rate limits (20 chats/IP/h, 300/day) and the budget alert.

### 9.3 Identity, network, APIs

- Service accounts: `resisttb-run` (Cloud Run), `genohack-vm` (storage.objectAdmin on the bucket), default compute SA 66604371416-compute@ (roles/editor and, granted this session, `roles/cloudbuild.builds.builder`; the Cloud Build SA also has it). The grant was needed because the first source deploy failed with PERMISSION_DENIED.
- Firewall: `allow-iap-ssh` (35.235.240.0/20), `default-allow-icmp`, `default-allow-internal`, and **`default-allow-ssh` and `default-allow-rdp` still open to 0.0.0.0/0** (recommend deleting). A project-wide `ssh-keys` metadata entry exists.
- APIs enabled: compute, storage, aiplatform, billingbudgets, cloudbilling, run, artifactregistry, cloudbuild.
- Vertex AI: `gemini-3.5-flash-lite`, location `global`, billed to this project. Cost per chat is unknown (not measured).

### 9.4 Cost (my estimate from list prices, **not from the billing console**)

| Item | Estimate |
|---|---|
| VM `genohack-run-0` | about $0.66/h including disk; this run about $6-8 in total (≈ 13 h) |
| After the VM stops | 100 GB disk ≈ $0.37/day until deleted; VM itself $0 while stopped |
| Cloud Run | about $0 idle (min 0); Artifact Registry ≈ $0.01/month |
| Buckets | pennies |
| Gemini | unknown; small model, short prompts |
| Earlier costs | first VM(s) and 400 GB disk (deleted) ≈ $8-10 |

Check the billing console for real numbers. Currency is IDR, so alerts fire at IDR 250k / 450k / 500k.

### 9.5 Cleanup list (needs the user's explicit OK)

1. After results are synced: delete VM and its disk: `gcloud compute instances delete genohack-run-0 --project haduh-512512 --zone us-east4-a` (disk auto-deletes with the VM; confirm with `gcloud compute disks list`).
2. Delete firewall rules `default-allow-ssh`, `default-allow-rdp`; remove project `ssh-keys` metadata.
3. Optionally delete bucket `run-sources-haduh-512512-asia-southeast1` and old Artifact Registry images after the redeploy.
4. Keep the main bucket (results + BLAST index) so the VM can be recreated.

---

## 10. Local environment

macOS laptop. Git-ignored: `results/`, `ref/`, `.venv/`, `web/node_modules`, `web/.next`, `web/.next-export`, `web/site`, `fasta_export/`.
Python 3.13 venv; Node 24 / pnpm 10; Next 16.4.3, React 19.3, Tailwind 4; BLAST+ 2.17 (unused locally); gcloud SDK; Chrome (headless for PDFs).
Preview configs are in `/Users/afan/Documents/Repos/mtb-hackathon/.claude/launch.json` (`web` on 3000, `static-web` on 3100).

```bash
cd /Users/afan/Documents/Repos/mtb-hackathon/genohack
python -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/python -m pytest                                  # 34 passed, 1 skipped
# run locally (two terminals)
GENOHACK_RESULTS=results PYTHONPATH=src .venv/bin/uvicorn genohack.api:app --port 8000
cd web && pnpm install && pnpm dev                          # http://localhost:3000
```

If `results/` is absent the API uses `resources/snapshot_windows.npz`. The agent needs a valid `gcloud` login (Application Default
Credentials or a short-lived access token). macOS Gatekeeper blocked the 800 MB BLAST index download (`gcloud-crc32c`); this was
deliberately not bypassed.

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

Worked check, inhA (Bandung): 99.55, 83.70, 100, 97 → 94.38 → 94. Interface coverage % is exact/isolates rounded **down** to one decimal.
Panel "share of WHO resistance" (lookup) = fraction of WHO resistance variants for that drug that the suggested panel's variants account for, matched on genome position **and** alt allele (an earlier version double-counted).

## 12. Threshold provenance (be honest about this in the proposal)

Only a minority of thresholds have an external source; nothing was re-verified against a published guideline.

| Threshold | Value | Origin |
|---|---|---|
| Primer length / Tm / GC | 18-25 / 58-64 °C / 40-65% | common practice; TOAST (18-24, 58-80, 45-68) and PrimeGen (GC 40-62) read |
| Amplicon | 70-160 bp | typical qPCR; a web result said 50-150 |
| Salt / DNA | 50 mM Na⁺, 3 mM Mg²⁺, 0.8 mM dNTP, 250 nM | typical, from memory |
| Probe length / Tm / GC | 20-30 / 64-74 °C / 30-75% | typical TaqMan, patent example (8-12 °C above primers); GC widened for inhA |
| Probe Tm above primers | 6-12 °C | patent example, lower bound loosened |
| No 5′ G; SNP ≥ 4 from ends | rules | TaqMan guidance (memory); mine |
| Tm gap target 8 °C; primer Tm match 3 °C | targets | mine; common guidance |
| Dimer: band −6 to −10, caution −7, conflict −9 kcal/mol | | the widely quoted ≈ −9 limit, unverified |
| Hairpin band −2 to −4 | | team notes p. 47 (written as kJ/mol, treated as kcal/mol) |
| Variable site MAF > 2% and ≥ 2 isolates | rule | mine |
| Last 3 bases of a primer = likely fail | rule | standard fact, "3" is mine |
| BLAST ≥ 16 bases, ≤ 2 mismatches, last 5 exact, ≤ 3 kb | rule | inspired by Primer-BLAST [18] |
| Specificity 25 per hit; weights 30/30/20/20 | rules | mine, not fitted |
| 4 channels, 2 per assay | assumption | typical instrument |
| Library inclusion: ≥ 10 resistant isolates | rule | mine (gives 205 from 212 candidates) |

There is no single settings file; values are function defaults across modules (next steps, section 17).

---

## 13. Capabilities (summary)

- Process any set of public MTB Illumina runs into per-isolate calls, resumable, sharded, self-restarting, with timing metadata.
- Design on the **population consensus** of pooled regions; tolerance ladder instead of dropping hard targets; probe-room fallback.
- Allele-specific probe pairs with Tm gap; per-isolate coverage with near-miss and 3′ failures; by lineage **and by region**.
- Off-target prediction (14 organisms) with caching; multiplex dimer screen and channel-limited tube grouping.
- 205-variant WHO library with drug names, evidence, per-region exact matches; instant `/api/design`.
- Chat for drug / gene / variant / patient-scenario questions with code-enforced warnings; explains WHO variants it cannot design.
- Sessions, per-chat reports, onboarding, minimizable assistant, responsive layout.
- One-container hosting (API + static site) on Cloud Run with rate limits and CORS control.

## 14. Limitations

**Science and data**
1. **In silico only.** Tm, dimer and probe gaps are model estimates; probe discrimination is modest (about 3-9 °C).
2. **Coverage is in-sample** (designed and measured on the same isolates). The held-out test on 779 other Indonesian runs is not done. The interface says so.
3. **Region labels are per BioProject.** Few isolates per region for rare variants; Tamil Nadu is lineage-1 heavy; per-region figures on small n are fragile.
4. **Mutant alleles are rare in Bandung** (2-8 isolates); mutant probes are designed from the expected change. The new regions improve this but are skewed to MDR/pre-XDR in Guangdong.
5. **Only near-fixed calls** (1/1). No heteroresistance; 100x subsampling can lose minor variants; indels come from the VCF, not the aligned FASTA.
6. **Not designed:** 10 rpoB variants (dense RRDR, indels, need multi-probe or melt design) and 2 pncA; large-deletion / LoF variants are excluded from the library.
7. Design assumes the consensus base at the SNP is wild type; otherwise no probes.
8. **Specificity is a screen**, and new pairs are "not checked" until BLAST is run on a VM (cache keyed by primer pair).
9. **Multiplex is a dimer screen only**; assumed 4 channels.
10. The score and its weights are a transparent heuristic, not validated (section 12).
11. Not a diagnostic and no clinical advice; the agent declines prescribing questions.

**Engineering and operations**
12. Thresholds scattered; no settings file or citations in code. Not all tool versions pinned in `envs/` (snpeff is now pinned).
13. No CI. The container pins Python deps in `deploy/requirements.txt`, but conda environments are not locked.
14. The small Gemini model ignores some instructions; critical wording is in code; phrasing may still be awkward. LLM cost per chat not measured.
15. Public Cloud Run endpoint: IP-based limits are in memory per instance (reset on cold start; max 1 instance).
16. Cloud Run still serves the old build until redeployed.
17. Security hygiene: open SSH/RDP firewall rules, project-wide SSH key, email-only budget alerts. Secrets audit found nothing in git.
18. Chats live in one browser only; clearing site data deletes them.
19. The VM disk bills until deleted.

---

## 15. Rebuild, redeploy and deploy runbook

### 15.1 When the VM run finishes (ETA 21:00-21:15 WIB)

Check progress (do not stop the run):

```bash
gcloud compute ssh genohack-run-0 --project haduh-512512 --zone us-east4-a --tunnel-through-iap --command 'tail -5 /home/runner/genohack/logs/watchdog.log; uptime'
gcloud storage ls gs://haduh-512512-genohack/results/ --project haduh-512512 | wc -l      # expect 222 + 234 + 1 = 457 lines
```

Then, from the repo (commit only named files):

```bash
bash scripts/sync_results.sh                                           # pull all finished isolates to results/
PYTHONPATH=src .venv/bin/python -m genohack.cli snapshot --results results
PYTHONPATH=src .venv/bin/python -m genohack.cli library --snapshot resources/snapshot_windows.npz   # writes resources/design_library.json and a copy in web/data/library.json
PYTHONPATH=src .venv/bin/python -m genohack.cli report --results results --snapshot resources/snapshot_windows.npz --out web/data/report.json
.venv/bin/python -m pytest
cd web && pnpm build:site                                              # -> web/site with relative API URL
```

Review the numbers in `web/data/report.json` and `library.json` (isolates should be 456; regions Bandung / Tamil Nadu / Guangdong) before
committing `resources/snapshot_windows.npz`, `resources/design_library.json`, `web/data/library.json`, `web/data/report.json`.

### 15.2 Deploy to Cloud Run

Prerequisites: `gcloud auth login`; Cloud Build SA and compute SA hold `roles/cloudbuild.builds.builder` (done); `Dockerfile` and `deploy/requirements.txt` exist.
Check the upload set first (should be about 75 files, under 10 MB): `gcloud meta list-files-for-upload .`

```bash
gcloud run deploy resisttb --source . --project haduh-512512 --region asia-southeast1 \
  --service-account resisttb-run@haduh-512512.iam.gserviceaccount.com \
  --min-instances 0 --max-instances 1 --memory 1Gi --cpu 1 --concurrency 4 --timeout 120 \
  --set-env-vars GENOHACK_PROJECT=haduh-512512,GENOHACK_LOCATION=global
```

The service is currently public (`allUsers` invoker). A redeploy keeps IAM; if it is ever recreated, re-grant with
`gcloud run services add-iam-policy-binding resisttb --member=allUsers --role=roles/run.invoker --region asia-southeast1 --project haduh-512512`.
Verify: `curl https://resisttb-zqrp2hdbia-as.a.run.app/api/health`, then run a design and a chat from the page. Check the page shows 456 isolates and three regions.

The container (python:3.13-slim) runs from source (`PYTHONPATH=/app/src`) and copies `src`, `resources`, `ref/NC_000962.3.fasta`, `ref/mask.bed`,
`web/data/report.json`, `web/site`. It needs no results folder and no BLAST database (snapshot + cache).

### 15.3 Starting a new data run (if needed)

Create a VM with the startup script and metadata (note the `^|^` delimiter because the project list contains commas):

```bash
gcloud compute instances create genohack-run-0 --project haduh-512512 --zone us-east4-a --machine-type e2-standard-16 \
  --boot-disk-size 100GB --boot-disk-type pd-balanced --image-family debian-12 --image-project debian-cloud \
  --service-account genohack-vm@haduh-512512.iam.gserviceaccount.com --scopes cloud-platform --labels project=genohack \
  --metadata-from-file startup-script=scripts/vm_startup.sh \
  --metadata "^|^BUNDLE=gs://haduh-512512-genohack/deploy/genohack_run_bundle.tgz|BUCKET=gs://haduh-512512-genohack|DESIGN_BIOPROJECT=PRJNA1256943,PRJNA898845|SHARD_INDEX=0|SHARD_COUNT=1|MAX_HOURS=14"
```

The bundle is rebuilt from the repo before a new run (check its contents are current). Run `gcloud compute instances describe genohack-run-0 --project haduh-512512 --zone us-east4-a --format='value(metadata.items)'` to copy the metadata from the live VM.

### 15.4 Minimum to keep the prototype alive at lowest cost

Cloud Run (min 0), the bucket (results + BLAST index, optional), and nothing else. Stop or delete the VM. Idle cost ≈ $0-1 per month plus Gemini calls.

---

## 16. Gotchas learned the hard way

- `gcloud` default project is not `haduh-512512`. Always `--project`. SSH needs `--tunnel-through-iap`.
- `pkill -f <text>` over SSH can kill your own session; use the `[x]` trick or a script.
- **snpEff 5.3.0a needs Java 21** but the environment pins Java 17 (GATK) → every isolate failed at TB-Profiler for ~20 minutes. `conda install snpeff<5.3` did nothing (5.3.0a < 5.3 prerelease). Fixed with `snpeff=5.2`, pinned in `envs/tbprofiler.yml`.
- `gcloud … --metadata` splits on commas; use `^|^` for the project list.
- Primer3 errors with more than 200 `SEQUENCE_EXCLUDED_REGION` items on diverse pooled data; the code merges runs and returns no pairs above 200.
- `*_LoF` names have positions but are not single changes → excluded (212 → 205).
- Small LLM: it misapplied number comparisons and ignored "ask which drug". Warnings and assumption prefixes are now generated in code.
- Region switch hidden with one region / stale state → now shown whenever region data exists, and keyed to reset.
- Next export mode: Cache Components / partial prefetch must be disabled; `STATIC_EXPORT=1` toggles them.
- ESLint ref-during-render in `useSessions` → ref updated in an effect.
- Detached shells lack `conda` on PATH; scripts source `$HOME/miniforge3/etc/profile.d/conda.sh`.
- ENA downloads do not resume; SRA is the default.
- Heavy jobs on the VM during a run slow it noticeably.
- `zsh` does not word-split unquoted variables; macOS `zcat` wants `.Z` (use `gzip -dc`).
- Screenshots in the browser tool can be stale; verify with the DOM or logs.
- Classifier-blocked cloud commands (enable APIs, IAM, deletes): stop, explain, give commands; the user runs or allows them.

---

## 17. What's next (prioritised)

**Immediately (today)**
1. Wait for the run (ETA ~21:00-21:15 WIB), then follow 15.1 and 15.2. Report the real numbers (isolates, per-region exact matches, designed targets) and re-check the headline assays.
2. Ask the user for approval to delete the VM and disk (9.5). Delete the open default firewall rules.
3. Decide whether to commit `docs/status_report.*` and this handover (done in this chat) and push.

**Short term**
4. **Held-out validation:** process some of the 779 other Indonesian runs (PRJNA595834 387, PRJNA430531 314, …) and report coverage on isolates not used in design. About 17 h of VM time per 780 runs at ~45/h plus Bandung-like depth; estimate $15-35.
5. **BLAST on a VM** for the library's new primer pairs (fill `offtarget_cache.json`).
6. **Multi-probe / melt design** for the rpoB RRDR (10 undesigned) and a strategy for pncA.
7. Settings file with cited thresholds; pin all conda tools; CI running tests; lock the container.
8. Heteroresistance-aware calling (TB-Profiler minor variants).
9. UI backlog: CSV order-sheet export, share link `?targets=`, compare, accessibility audit, real-phone test, remove mock fallback.
10. Measure Gemini cost per chat; consider a cap.
11. Add the Philippines project when data is available; resolve the London accession.

**Business and research (see the "GenoHack business values" chat and `business.txt` in the parent folder)**
12. Mentors' feedback: position as a "Genomic Assay Intelligence Platform"; interview 5-8 customers; paid pilot → subscription → licensing; B2B sizing, pricing / ROI, financial projection / NPV, validation plan and IP, partnerships, 12-month plan, **two headline benefits**.
13. Wet-lab validation with a partner lab; compare with Xpert MTB/RIF and Deeplex Myc-TB.
14. Panel optimisation as in PrimeGen (SADDLE-style).

---

## 18. Decision log

| Decision | Why |
|---|---|
| Nextstrain-TB-style pipeline | proven structure; matches team notes |
| 100x subsample | average 370x; −70% compute |
| us-east4 for the VM | Singapore downloads stalled; no resume |
| SRA default, ENA opt-in | ~20% faster, never failed |
| 6 isolates × 3 threads on 16 vCPU | CPU was half idle at 4 jobs; +17% throughput |
| Watchdog on the VM, not a laptop check | works when the laptop sleeps |
| Single e2-standard-16 for the new run (not two) | the user asked to keep it simple; sharding exists if needed |
| On-demand, not Spot | avoids pre-emption restarts; cost difference small for a ~13 h run |
| Pooled design with region grouping | one panel that works across regions; regions shown in coverage |
| Design on the population consensus | lineage polymorphisms would otherwise be penalised |
| Tolerance ladder, not dropping a target | a silently disappearing target is worse than a stated relaxation |
| Specificity as predicted products | single-primer hits are meaningless in a 3 Gb genome |
| BLAST on VM + cache | index cannot be downloaded to the Mac |
| 205 targets (≥ 10 resistant isolates) | covers frequent variants; the rest are explained, not designed |
| Library as a tab + `/api/design` | the dashboard should not depend on the chatbot |
| Snapshot instead of per-isolate files in the container | few MB vs 500 MB; same results |
| Code-enforced warnings | the small model ignores instructions |
| Sessions in IndexedDB, no accounts | no server cost or auth needed |
| Cloud Run public with rate limits | the user asked for public access; budget alert as a backstop |
| Gemini 3.5 flash lite, location `global` | user's choice; not offered in us-central1 |

## 19. Repository map

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
                           multiplex, assay, snapshot, regions, library, lookup, agent, api, cli   (~2,060 lines)
resources/                 GFF, WHO subset, regions.csv, isolates_extra.tsv, snapshot_windows.npz, design_library.json,
                           offtarget_cache.json, sample_bioproject_fallback.csv
tests/                     test_genome, test_windows, test_multiplex, test_snapshot, test_targets, test_api, test_primers,
                           test_scenarios   (34 pass, 1 skip)
web/                       Next.js app: app/, components/, lib/, data/ (report.json, library.json)   (~1,900 lines TS/TSX)
figures/                   position validation, lineage presence/absence, CSVs
docs/                      HANDOVER.md, status_report.{html,pdf}, pipeline_overview, pipeline_explained, progress_report, refs.json
```

Recent commits (newest first): e6a0e7b layout/minimize/onboarding; 8d87e9a sessions; 2cfe3d2 scenario handling; fa80626 region switch;
b7d35b9 Primer3 fix + limit note; c41f1ab library panel + /api/design; d8d26f3 WHO targets + library + lookup; 56c6c95 snpEff pin;
61e1ba9 VM watchdog; 9a4cf0a regions/pooled/sharding/vm_startup; 354ccb6 static mount + rate limit; 3ac641a container + static export;
fc7a068 snapshot; b5c7bf0 docs/.gitignore (other chat); 8885a20 validation figures.

## 20. Memory and context pointers

Memory notes (auto-loaded) are in `/Users/afan/.claude/projects/-Users-afan-Documents-Repos-mtb-hackathon/memory/`: `feedback_push-genohack-freely.md`
(standing permission to push this repo; HTTPS via keychain), `feedback_no-commit-attribution.md` (no Co-Authored-By / Generated-with lines),
`project_genohack-gcp.md` (cloud facts; refreshed on 2026-10-24 evening). Reference material in the parent folder: `GenoHack Master Document.pdf`
(81 pp., Indonesian; proposal draft pp. 68-72; meeting plan p. 81), `papers/` (TOAST, PrimeGen), `business.txt`, `ncbi_metadata/`.
Full transcript of this chat: `/Users/afan/.claude/projects/-Users-afan-Documents-Repos-mtb-hackathon/6e8a81cd-0a49-46ba-82cf-deefe1186ef7.jsonl`.

## 21. References and sources

R = read or fetched during this project. M = tool used; citation written from memory, check before submitting. S = web search result. N = from team notes, not read.

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
| [9] | Software | Garrison E, Marth G. FreeBayes. arXiv:1207.3907 (2012). | M |
| [10] | Software | Li H. BWA-MEM. arXiv:1303.3997 (2013). | M |
| [11] | Software | Phelan JE et al. TB-Profiler. Genome Medicine 11:41 (2019) (v6.6.5). | M |
| [12] | Software | Hall M. Rasusa. JOSS 7(69):3941 (2022) (v5.1.0). | M |
| [13] | Software | NCBI SRA Toolkit 3.2.1. https://github.com/ncbi/sra-tools | M |
| [14] | Software | Mölder F et al. Snakemake. F1000Research 10:33 (2021). | M |
| [15] | Software | Raasveldt M, Mühleisen H. DuckDB. SIGMOD 2019. | M |
| [16] | Software | Untergasser A et al. Primer3. Nucleic Acids Res 40(15):e115 (2012); primer3-py 2.4.0. | M |
| [17] | Software | Camacho C et al. BLAST+. BMC Bioinformatics 10:421 (2009) (2.17.0+). | M |
| [18] | Software | Ye J et al. Primer-BLAST. BMC Bioinformatics 13:134 (2012). Inspiration only. | M |
| [19] | Software | Google Cloud Vertex AI / Gemini (gemini-3.5-flash-lite, location global); google-genai; FastAPI; Next.js 16; Tailwind 4. | R |
| [20] | Prior work | Wang L et al. TOAST. BMC Genomics 26:1058 (2025). doi:10.1186/s12864-025-12247-9 ; https://github.com/linfeng-wang/TOAST | R |
| [21] | Prior work | Wang Y et al. PrimeGen. Nature Biomedical Engineering 10:338-353 (2026). doi:10.1038/s41551-025-01455-z | R |
| [22] | Prior work | Nextstrain TB build, https://github.com/nextstrain/tb (pipeline structure). | R |
| [23] | Prior work | Xie NG et al. SADDLE. Nature Communications 13:1881 (2022). Cited in PrimeGen; not used. | M |
| [24] | Prior work | Multiplex real-time PCR melting curve assay for drug-resistant TB mutations. J Clin Microbiol (2011). https://pubmed.ncbi.nlm.nih.gov/21752982 | S |
| [25] | Prior work | Frontiers in Tropical Diseases (2026). doi:10.3389/fitd.2026.1953716 (team notes p. 76; not read). | N |
| [26] | Prior work | GenoHack Master Document (team notes), meeting plan p. 81, draft proposal pp. 68-72. | R |
| [27] | Thresholds | TOAST defaults file and PrimeGen (read); web result (patent text) for probe Tm and amplicon length; general practice from memory. See section 12. | S |
| [28] | Cost | Google Cloud Billing Catalog API (E2, balanced PD), https://cloud.google.com/billing/docs/how-to/get-pricing-information-api | R |
