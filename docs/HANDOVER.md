# ChatGP-TB handover

Written 2026-10-24 (about 09:00 WIB) for continuing in a new chat. Everything below was checked against the repo,
the cloud project and the data on that date unless a line says "not verified". Read this first, then
`README.md`, then the memory notes listed in section 17.

Numbers in square brackets, like [8], refer to the reference list in section 19; its status column says which sources were read and which citations are from memory and need checking.

**Deadline:** GenoHack proposal due **15:00 WIB on 2026-10-24** (3 A4 pages: background and problem, proposed
technology, development plan, team, partners, current TRL, early prototype / lo-fi design).

---

## 1. One-paragraph summary

ChatGP-TB takes 222 *Mycobacterium tuberculosis* genomes from Bandung (public NCBI data), calls their variants,
and uses the result to design qPCR primers and allele-specific probes for four drug-resistance hotspots (rpoB
S450L, katG S315T, inhA promoter c.-15C>T, gyrA D94G). Each design is checked against all 222 isolates (overall and
by lineage), screened for off-target amplification in human, non-tuberculous mycobacteria and respiratory bacteria,
scored, and checked for whether assays can share a tube. A Gemini agent (Vertex AI) turns a chat request into a call
to this design tool and explains the result in a Next.js interface. **Everything is in silico: nothing has been tested
in a tube.**

## 2. Status snapshot

| Area | State |
|---|---|
| Data processing, 222 isolates | **Done.** All in the bucket; VM shut itself down at 2026-10-24 01:09 UTC (08:09 WIB) |
| Design library (Python) | **Done**, 11 tests pass |
| Final report on 222 isolates | **Done**, `web/data/report.json`, generated 2026-10-24 01:14 UTC |
| Gemini agent + API | **Done**, tested end to end on the final data |
| Web interface | **Done** (runs locally) |
| Resistance-SNP ranking | **Partial**: 4 hand-picked hotspots with real WHO evidence, not an automated ranking of all mutations |
| Held-out validation on other Indonesian projects | **Not started** |
| Hosted deployment | **Not started** (runs on a laptop only) |
| 3-page proposal | **Not started** in this chat (a draft exists in the master document, pages 68-71, but predates all results) |
| Wet-lab validation | Not started, out of scope for the hackathon |

Repo: `github.com/blueguy42/genohack` (private), branch `main`, 34 commits, HEAD `d124764` at time of writing.
Local path: `/Users/afan/Documents/Repos/mtb-hackathon/genohack`.

---

## 3. Final results (on 222 Bandung isolates)

Source: `web/data/report.json`. Scores are explained in section 8.

| Rank | Assay | Overall | Conservation | Thermodynamics | Specificity | WHO evidence | Exact match | One mismatch | Likely fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | inhA promoter c.-15C>T (pos 1,673,425) | 94 | 100 | 84 | 100 | 97 | 221/222 | 1 | 0 |
| 2 | gyrA p.Asp94Gly (pos 7,582) | 87 | 92 | 68 | 100 | 94 | 205/222 | 14 | 3 |
| 3 | katG p.Ser315Thr (pos 2,155,168) | 85 | 99 | 85 | 50 | 98 | 219/222 | 2 | 1 |
| 4 | rpoB p.Ser450Leu (pos 761,155) | 83 | 95 | 50 | 100 | 98 | 212/222 | 8 | 2 |

- BLAST screen: **0 predicted off-target products** in human, non-tuberculous mycobacteria and respiratory bacteria
  for all four primer pairs. katG has specificity 50 only because of 2 near-matches inside the H37Rv genome itself.
- Multiplex: no pair conflicts at the -9 kcal/mol limit; 4 pairs sit at "caution" (-7 to -7.6). With 4 channels and
  2 per assay, the grouping is **Tube 1 = inhA + gyrA, Tube 2 = katG + rpoB**.
- gyrA needed a relaxed design: a polymorphism 3 bases from the SNP in about 8% of isolates blocks every probe window
  at the strict 2% setting, so oligos were allowed over sites varying in up to 10% of isolates (stated in the assay's
  caveats).
- Probe discrimination (estimated Tm drop between alleles): inhA 4.5/4.3 C, gyrA 5.3/4.6, katG 3.4/9.5,
  rpoB 4.6/5.1 (wild-type probe / mutant probe).
- Sequences (5' to 3'; reverse primer written as it would be ordered; probe strand shown as designed):

| Assay | Forward | Reverse | Probe (wild-type) | Probe (mutant) |
|---|---|---|---|---|
| inhA c.-15 | CTCGTGGACATACCGATTTC | CCAGGACTGAACGGGATAC | ACAACCTATCGTCTCGCCGCG | ACAACCTATCATCTCGCCGCG |
| gyrA D94G | ACCATGGGCAACTACCAC | GGCTTCGGTGTACCTCATC | TACGACACCCTGGTGCGCAT | TACGGCACCCTGGTGCGCAT |
| katG S315T | TCTCGAGGAAACTGTTGTCC | CTGGAAGAGCTCGTATGGC | ATCACCAGCGGCATCGAGGT | ATCACCACCGGCATCGAGGT |
| rpoB S450L | TTCATGGACCAGAACAACCC | GGTTTCGATCGGGCACAT | CGCCGACAGTCGGCGCTTGT | CGCCAACAGTCGGCGCTTGT |

Dataset facts that shape the limits of these results (from TB-Profiler on the 222 isolates):
- Lineages: lineage 4 = 117, lineage 2 = 94, lineage 1 = 8, mixed lineage 2+4 = 3.
- Resistance class: Sensitive 180, HR-TB 9, MDR-TB 8, RR-TB 4, Other 21.
- Carriers of the target mutations: katG S315T 8 isolates, rpoB S450L 3 (plus S450F 2), gyrA D94G 3, inhA c.-777C>T
  (the WHO name for the promoter variant) 3. **The resistant alleles are barely represented**, so the mutant probes are
  designed from the expected sequence change, not validated on many observed mutants.

---

## 4. Inputs and outputs

**Inputs**
1. Public sequencing reads, Bandung: 222 paired-end Illumina runs, BioProject PRJNA1433044, 174 GB gzipped FASTQ.
2. H37Rv reference genome (NC_000962.3), gene annotation, low-confidence mask.
3. WHO 2023 mutation catalogue (resistance evidence and genome coordinates).
4. Off-target genomes for BLAST (human, 7 NTM, 6 respiratory bacteria).
5. A chat request (for example "design an assay for isoniazid resistance only").

**Outputs**
1. Per isolate (x222): `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, `<run>.results.json` (TB-Profiler),
   `metadata.json` (durations, versions, source row), `DONE`. In `gs://haduh-512512-genohack/results/<run>/`.
2. Per request: a report (JSON, schema in `web/lib/types.ts`) with ranked assays: primer pair, wild-type and
   mutant probe (sequence, coordinates, strand, Tm, hairpin/self-dimer dG, Tm gap), four scores, coverage overall and
   by lineage, specificity, reasons, caveats, multiplex pairs and tube grouping, step timings.
3. A chat summary from the agent, and the interface rendering the report.

---

## 5. Datasets

| Dataset | Source | Size / count | Where it lives | Licence / note |
|---|---|---|---|---|
| SRA metadata [2] | AWS open data `s3://sra-pub-metadata-us-east-1/sra/metadata/*`, queried with DuckDB (`sql/indonesia_isolates.sql`) | 1,001 Indonesian MTB Illumina WGS runs | `data/isolates.tsv` on the VM disk only (regenerate with `scripts/select_isolates.sh`) | public |
| Bandung reads [1] | NCBI SRA PRJNA1433044 (Universitas Padjadjaran; submitted 2026-03-05) | 222 runs, 361 Gbases, 174 GB gz | downloaded per isolate, then deleted | public |
| H37Rv genome [3] | NCBI nuccore NC_000962.3 | 4,411,532 bp | `ref/NC_000962.3.fasta` (local and VM, git-ignored) | public |
| Gene annotation [4] | Ensembl ASM19595v2 GFF, copied from the TOAST repo | 4,018 genes | `resources/H37Rv_ASM19595v2.gff` (committed, 2.3 MB) | TOAST is MIT. Chromosome is named `Chromosome` here, `NC_000962.3` elsewhere (same coordinates) |
| Low-confidence mask [6] | `nextstrain/tb` `defaults/AF14_RLC_Regions.Plus.LowPmapK50E4.H37Rv.bed` (Marin et al. 2022) | 1,324 regions, 276,750 bases | `ref/mask.bed` (downloaded by `setup_vm.sh`; not committed) | the nextstrain/tb clone had no LICENSE file, so it is downloaded, not copied. BED chromosome is `NC_000962` (no version) |
| WHO catalogue 2023 [5] | `GTB-tbsequencing/mutation-catalogue-2023` | grade 1 and 2 only: 1,383 rows, 1,291 variants, 643 with SNV coordinates | `resources/who_catalogue_2023_assoc_with_R.csv` (built by `scripts/build_who_subset.py`) | MIT. WHO names the inhA promoter variant at 1,673,425 `inhA_c.-777C>T`; the literature calls it fabG1 c.-15C>T |
| Off-target BLAST db [7] | NCBI Datasets: human GRCh38 (GCF_000001405.40); reference genomes of M. avium, M. intracellulare, M. abscessus, M. kansasii, M. fortuitum, M. smegmatis, M. marinum; S. pneumoniae, S. aureus, P. aeruginosa, K. pneumoniae, H. influenzae, Nocardia farcinica | 729 sequences, 3.37 Gbases, index about 842 MB (803 MiB) | VM disk `ref/offtarget/` and bucket `offtarget/` (not on the laptop) | public |
| BLAST result cache | produced by the above | 4 entries | `resources/offtarget_cache.json` (committed) | keyed by the exact primer pair |
| Per-isolate results | this project | 329 MB in the bucket, 504 MB on the laptop | bucket + `results/` (git-ignored) | derived data |

**Other Indonesian projects** (selected by the metadata query, not processed; kept as the intended held-out test):
PRJNA595834 387 runs (Radboudumc "TANDEM WGS"), PRJNA430531 314 (Radboudumc, pulmonary TB and TB meningitis),
PRJNA1150781 42 (Papua, lineage 1, Padjadjaran), PRJNA633244 30 (Java MDR, Khon Kaen University), PRJNA950554 6
(Lab nasional Prof Sri Oemijati). Total 779. Raw sizes (whole projects) in ENA file reports: 231 GB, 158 GB, 17 GB,
25 GB, 1.5 GB. Earlier metadata is in `/Users/afan/Documents/Repos/mtb-hackathon/ncbi_metadata/`.

Other files in the parent folder `/Users/afan/Documents/Repos/mtb-hackathon/`: `GenoHack Master Document.pdf` (team
notes in Indonesian, 81 pages; the meeting plan "Kesimpulan Meet 23/10/26" is on page 81; a proposal draft is on pages
68-71), `papers/` (TOAST paper `s12864-025-12247-9-1.pdf`, PrimeGen paper `s41551-025-01455-z.pdf`).

---

## 6. Pipeline in detail

Two diagrams exist: `docs/pipeline_overview.pdf` (3 pages) and the earlier status diagrams in the chat history.

### 6.1 Stage A: from public data to per-isolate results (cloud VM)

Modelled on the Nextstrain TB build [22]. Orchestration (Snakemake [14]): `workflow/Snakefile` (one rule per isolate, random fixed-seed order so partial results are a fair
sample), launched by `scripts/run_full.sh`, kept alive by `scripts/watchdog.sh`. Per isolate,
`scripts/process_isolate.sh <run> <threads> <coverage>`:

1. **Skip** if `gs://.../results/<run>/DONE` already exists (recreates the local `DONE` so Snakemake agrees).
2. **Download** with `fasterq-dump` (sra-tools 3.2.1 [13], `--split-files`) from NCBI SRA. ENA (curl) exists as an opt-in
   (`DOWNLOAD_SOURCE=ena`); it stalled from Singapore and worked from us-east4 (2.6 MB/s) but SRA was about 20% faster.
3. **Subsample** to 100x with `rasusa` 5.1.0 [12] (`--genome-size 4.4mb --seed 100`). Reads are left uncompressed:
   compressing the full-size reads cost 5-10 minutes per isolate under load.
4. **Call variants** with `snippy` 4.6.0 [8] against H37Rv: `bwa mem` [10] alignment, then FreeBayes 1.3.6 [9]. The VCF header shows
   `-p 2 -P 0 -C 2 -F 0.05 --min-coverage 10 --min-repeat-entropy 1.0 -q 13 -m 60`. In every file checked, all calls are
   genotype 1/1 and minimum depth is 10.
5. **Profile** with `tb-profiler profile` 6.6.5 [11] (own mapping and calling): lineage, drug-resistance calls.
6. **Keep** `snps.vcf.gz`, `snps.aligned.fa.gz`, `snps.txt`, the TB-Profiler JSON; write `metadata.json` (per-step
   seconds, bytes, tool versions, machine type, the isolates.tsv row); upload to the bucket; write `DONE` last;
   delete the reads and intermediates.

Settings used for the full run: 6 isolates at once, 3 threads each, Snakemake `--cores nproc+2 --keep-going
--retries 2 --rerun-incomplete`. Measured: median 851 s per isolate (mean 855, max 1,300), 2.4 minutes of VM time per
isolate at 6 in parallel, wall clock from the first test isolate to the last result: 2026-10-23 15:37 to 2026-10-24 01:08 UTC (about 9.5 hours, including test batches and the two watchdog restart tests).

**Watchdog** (`scripts/watchdog.sh`, installed as systemd timer `genohack-watchdog.timer`, every 15 minutes, first
run 3 minutes after boot): restarts the run if Snakemake is not running; restarts if no new isolate for 50 minutes;
gives up and shuts the VM down after 8 restarts without progress; when all isolates are done it writes
`logs/COMPLETE` and shuts the VM down once. `run_full.sh` itself only shuts down when everything is done. Tested by
forcing a stall restart and a simulated crash. **The timer is still enabled on the VM**; on a restart it sees
`COMPLETE` and does nothing.

### 6.2 Stage B: design library (`src/genohack/`, runs on the laptop in about 20 seconds)

Entry: `python -m genohack.cli report` or the agent's `design_assays` tool, both call `assay.build_report()`.

| Step | Module | What it does | Key settings (see section 9 for sources) |
|---|---|---|---|
| Locate targets | `genome.py`, `targets.py` | Positions from the GFF, strand aware (`Gene.codon_pos`, `upstream_pos`); asserts the reference base | 4 targets, hand-picked; verified against the genome and WHO coordinates |
| Variant table | `isolates.py`, `variants.py` | For each target, +/-300 bp: base code per isolate per position (ACGT, MISSING for `-`, `N`, `n`), indel flags from the VCF, per-position counts, **consensus base**, minor-allele frequency, masked flag | `finished_samples` requires the data files, not just `DONE` |
| Primers | `primers.py` | Primer3 [16] (primer3-py 2.4.0) on the consensus; sites excluded if variable (MAF > tolerance AND >= 2 isolates), masked, indel or missing in > tolerance and >= 2 isolates; amplicon must contain the SNP | size 18-25, Tm 58-64, GC 40-65, poly-X <= 4, product 70-160, 20 pairs |
| Probes | `probes.py` | Windows over the SNP; wild-type from consensus, mutant = one base changed; Tm gap from Primer3 thermodynamic alignment of each probe against the other allele | 20-30 nt, Tm 64-74, GC 30-75, no 5' G, no other variable site, SNP >= 4 bases from either end |
| Assemble | `assay.py` | Per primer pair, picks the probe inside the amplicon with a Tm 6-12 C above the primers and the best gap | tolerance ladder 2% -> 5% -> 10% -> 20% if no design exists |
| Checks | `checks.py`, `specificity.py`, `thermo.py` | hairpin/self-dimer/cross-dimer dG; H37Rv near-match scan (cached); BLAST predicted off-target products | see below |
| Coverage | `assay.coverage_for` | per isolate: exact / one mismatch / likely fail; by lineage from TB-Profiler `main_lineage` | SNP position excluded from the mismatch count but must be called |
| Evidence | `who.py` | best WHO positive predictive value for the exact nucleotide change | grade 1 and 2 catalogue slice |
| Score and rank | `assay.score_assay` | section 8 | weights 30/30/20/20 |
| Multiplex | `multiplex.py` | all cross-assay oligo pairs, worst dimer dG, status, greedy tube grouping | caution -7, conflict -9 kcal/mol; 4 channels, 2 per assay |
| Report | `assay.build_report` | JSON for the interface | schema = `web/lib/types.ts` |

Specificity details (BLAST+ [17]; the product idea follows Primer-BLAST [18]): primer binding site = BLAST alignment (`blastn-short`, word size 7) of >= 16 bases, <= 2 mismatches,
no gaps, reaching the primer's 3' end with the last 5 bases exact; **a predicted product** = a plus-orientation site
followed within 3,000 bases, on the same sequence, by a minus-orientation site. Counted per group (human, ntm, flora).
Single-primer hits are deliberately not counted: a 16-mer with 2 mismatches matches the human genome about a thousand
times by chance. The BLAST database exists only on the VM; the laptop reads `resources/offtarget_cache.json`, keyed by
the exact primer pair. **A new primer pair with no cache entry reports specificity as "not checked".**

### 6.3 Stage C: agent, API, interface

- `agent.py`: Gemini `gemini-3.5-flash-lite` through Vertex AI [19] (location `global`; the model is not offered in
  us-central1), via the `google-genai` SDK with function calling. One tool, `design_assays(targets)`, with an enum of
  the four target ids and the drug each covers. The system prompt tells it to pick targets from the named drugs, never
  invent numbers, quote the supplied coverage sentence, write plain text, state in silico only. Tool arguments are
  validated server side; the model only sees a compact summary (scores, a ready-made coverage sentence, specificity
  note, multiplex tubes). Up to 5 turns. Credentials: Application Default Credentials if present, else a short-lived
  `gcloud auth print-access-token` (laptop only).
- `api.py` (FastAPI): `GET /api/health`, `GET /api/report`, `POST /api/chat` (server-sent events: `step`, `report`,
  `text`, `error`, `done`). CORS allows `http://localhost:3000` and `127.0.0.1:3000` (env `GENOHACK_ORIGINS`).
- `web/` (Next.js 16.4.3, React 19.3, Tailwind 4, TypeScript): static page that loads `web/data/report.json`
  (falls back to `lib/mock.ts`, labelled demo data, if the file is empty). Chat calls the API directly at
  `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000`); if the API is down and the data is mock it replays the steps,
  otherwise it shows an error. Next 16 has breaking changes: read `web/node_modules/next/dist/docs/` before changing
  routing or config (`web/AGENTS.md` says so).

---

## 7. Capabilities

- Reproducible processing of any set of public MTB Illumina runs into per-isolate variant calls and lineage/resistance
  calls, resumable, with per-step timing metadata.
- Population-aware design: oligos are designed on the **population consensus**, not H37Rv (a base that differs from
  H37Rv in every isolate is still conserved), avoiding variable, masked, indel and poorly covered sites.
- Allele-specific probe pairs with an estimated Tm gap, and per-isolate coverage that counts near misses and 3' end
  failures separately, split by lineage.
- Off-target amplicon prediction against 14 organisms, plus H37Rv near-matches.
- Multiplex compatibility and a channel-limited tube grouping.
- WHO-catalogue evidence attached to each target.
- Chat front end that selects targets from drug names, runs the design, streams its steps and explains the result
  without generating numbers itself.
- Partial-result friendliness: results upload per isolate in random order; `scripts/summarize_partial.py` summarises
  whatever is finished.

---

## 8. Scoring formulas (exactly as coded in `assay.score_assay`)

```
overall = 0.30*conservation + 0.30*thermodynamics + 0.20*specificity + 0.20*resistance_evidence
          (if evidence is missing: drop it and renormalise the other weights)

conservation   = 100 * exact_matches / isolates
thermodynamics = 100 * mean of five terms, each clipped to [0,1]:
   1  min(wt_gap, mut_gap) / 8                           (probe Tm gap between alleles, C)
   2  1 - |Tm_forward - Tm_reverse| / 3
   3  1 if 6 <= (min probe Tm - mean primer Tm) <= 12, else 1 - 0.15 * (C outside that band)
   4  (worst cross-dimer dG + 10) / 4                    (kcal/mol: >= -6 full, <= -10 zero)
   5  (worst hairpin dG + 4) / 2                         (kcal/mol: >= -2 full, <= -4 zero)
specificity    = max(0, 100 - 25 * hits)
   hits = H37Rv near-matches (primers: <= 3 mismatches with exact last 6 bases; probe: <= 2 mismatches)
          + BLAST predicted off-target products (human + ntm + flora)
evidence       = round(100 * highest WHO positive predictive value among drugs matching the exact change)
```

Worked check, inhA: conservation 99.55, thermodynamics 83.70 (terms 0.543, 0.642, 1, 1, 1), specificity 100, evidence 97
-> 94.38, shown as 94. The interface's coverage percentage is exact matches / isolates, rounded **down** to one
decimal (221/222 shows 99.5%).

---

## 9. Threshold provenance (be honest about this in the proposal)

Sources: TOAST [20] and PrimeGen [21] (read), a web search result [27], the team notes [26], and general practice.

Only a minority have an external source. Everything not marked "source" was applied from general qPCR practice or is a
choice of mine. **Nothing here was re-verified against a published guideline in the session.**

| Threshold | Value | Origin |
|---|---|---|
| Primer length | 18-25 | common practice; TOAST default file uses 18-24 (read) |
| Primer Tm | 58-64 C | common practice; TOAST allows 58-80 (read). Tighter by choice |
| Primer GC | 40-65% | common practice; PrimeGen paper 40-62% (read); TOAST 45-68 (read) |
| Amplicon | 70-160 bp | typical qPCR; a web search result gave 50-150 bp; stretched |
| Salt / DNA | 50 mM Na+, 3 mM Mg2+, 0.8 mM dNTP, 250 nM | typical qPCR values from memory |
| Probe length | 20-30 nt | typical TaqMan-style, from memory |
| Probe Tm | 64-74 C | a patent example in a web search had probes about 8-12 C above primers (58-60 / 68-70) |
| Probe Tm above primers | 6-12 C | same patent example (8-12); lower bound loosened by me |
| Probe GC | 30-75% | upper bound widened by me because the inhA region is 65-73% GC |
| No 5' G | rule | common TaqMan guidance (quenches the dye), from memory |
| SNP >= 4 bases from probe ends | rule | mine |
| Probe Tm gap 8 C | target | mine, no source |
| Primer Tm match 3 C | target | common guidance 2-3 C |
| Dimer band -6 to -10; conflict -9; caution -7 | kcal/mol | the widely quoted limit of about -9 kcal/mol, from memory, unverified |
| Hairpin band -2 to -4 | kcal/mol | team notes (master doc p. 47, written as kJ/mol, treated here as kcal/mol) say hairpin dG should be better than about -3 |
| Variable site: MAF > 2% and >= 2 isolates | rule | mine (aims at about 98% coverage). The count floor stops one isolate blocking everything on small sets |
| 3' end: mismatch in the last 3 bases of a primer = likely fail | rule | standard fact that 3' mismatches matter most; "3" is mine |
| BLAST: >= 16 bases, <= 2 mismatches, last 5 exact, product <= 3 kb | rule | inspired by Primer-BLAST, not identical to its defaults |
| Specificity penalty 25 per hit | rule | mine |
| Score weights 30/30/20/20 | rule | mine, not fitted |
| 4 channels, 2 per assay | assumption | typical instrument, not the target lab's |

The values live as function defaults scattered across the modules; there is no single settings file yet (see section 16).

---

## 10. Cloud

Project **`haduh-512512`** ("HaDuH", number 66604371416). Billing account `01D2B5-C86DC4-5860ED` ("My Billing Account"),
**currency IDR**. The user's account `ahmadalfanihandoyo1@gmail.com` is project owner. **The gcloud default project on the
laptop is a different one (`tap-twice-aurania`); always pass `--project haduh-512512`.**

| Resource | Details |
|---|---|
| VM `genohack-analysis-us` | zone us-east4-a; **e2-standard-16** (16 vCPU, 62-64 GB RAM); Debian 12; boot disk 400 GB `pd-balanced`; automatic restart on, migrate on maintenance, standard (not Spot); label `project=genohack`; service account `genohack-vm`, scope cloud-platform; ephemeral external IP (none while stopped). Created 2026-10-23 15:06 UTC as e2-standard-8, resized to 16 vCPU at 16:03 UTC, stopped itself 2026-10-24 01:09 UTC. **Status now: TERMINATED. The disk still exists and bills.** |
| On the VM disk | `~/genohack` (the repo, pulled over SSH with a read-only deploy key `genohack-vm-us`), `results/` (222 isolates), `ref/` (genome, mask, `offtarget/` BLAST db 7.2 GB incl. downloads), `data/isolates.tsv` (1,001 runs), `logs/` (including `COMPLETE`, `watchdog.log`), miniforge3 with conda envs `snippy`, `tb-profiler`, `duckdb`, `design`, `offtarget` |
| Systemd | `genohack-watchdog.timer` and `.service` (root), transient `genohack-run-*` units |
| Bucket `gs://haduh-512512-genohack` | asia-southeast1, uniform access; `results/` 329 MB (222 folders), `offtarget/` 842 MB (BLAST index files `offtarget.n*`) |
| Service account `genohack-vm@haduh-512512.iam.gserviceaccount.com` | `roles/storage.objectAdmin` on that bucket only. (The Compute default service account also exists, unused.) |
| Network | default network. Firewall: `allow-iap-ssh` (35.235.240.0/20, tcp:22, created by me) plus the stock `default-allow-ssh` and `default-allow-rdp` (**0.0.0.0/0, still open; recommend deleting both**), `default-allow-icmp`, `default-allow-internal` |
| SSH | `gcloud compute ssh ... --tunnel-through-iap`. Direct port 22 is blocked from the user's home network. `gcloud compute ssh` added an `ssh-keys` entry to **project** metadata, which applies to every VM in the project |
| APIs enabled by me | compute, storage, aiplatform (Vertex AI), billingbudgets, cloudbilling |
| Budgets | two on the billing account: "genohack-haduh" IDR 500,000 (alerts at 50/90/100%) and a pre-existing "Rp500,000 Monthly budget alert" (50/90/100/150%). **Alerts only email; nothing stops spending automatically** |
| Vertex AI | Gemini `gemini-3.5-flash-lite`, location `global`, billed to this project |
| Deleted | the first VM `genohack-analysis` (asia-southeast1-b), after downloads from Singapore stalled |

Cost so far, with prices from [28] (**my estimate from list prices, not from the billing console**): the VM at $0.36/h (e2-standard-8, us-east4) for
about 0.9 h and about $0.66/h (e2-standard-16, disk included) for about 9.1 h is roughly $6.4; the deleted Singapore VM
(about $0.40/h for a few hours) about $1; disk, bucket and Vertex calls a few dollars at most. **Likely total around
$8-10. Check the billing console for the real number.** Ongoing: the stopped VM's 400 GB disk costs about $0.06/h
(about $1.50/day, $44/month); the bucket about $0.03/month. Rates used: e2 core $0.02457/h and RAM $0.00329/GiB-h in
us-east4, balanced PD $0.11/GB-month (from the Cloud Billing catalogue API).

Restart the VM (the watchdog will see `COMPLETE` and idle):

```
gcloud compute instances start genohack-analysis-us --project haduh-512512 --zone us-east4-a
```

Clean-up when finished (irreversible):

```
gcloud compute instances delete genohack-analysis-us --project haduh-512512 --zone us-east4-a
```

(boot disk is set to delete with the VM). Delete the two default firewall rules `default-allow-ssh` and
`default-allow-rdp` and the stale project `ssh-keys` entry if the project will be kept.

---

## 11. Local environment

macOS laptop (Apple silicon). Not committed (git-ignored): `results/` (504 MB), `ref/` (genome, mask), `.venv/`,
`web/node_modules`, `web/.next`.

| Tool | Version |
|---|---|
| Python venv `.venv` | Python 3.13.11; primer3-py 2.4.0, pandas 3.1.0, numpy 2.5.4, FastAPI 0.161.1, google-genai, google-auth, openpyxl, pytest, uvicorn |
| Node / pnpm | 24.14.0 / 10.31.0; Next 16.4.3, React 19.3.0, Tailwind ^4 |
| BLAST+ | 2.17.0 (Homebrew), unused locally because the database is not here |
| gcloud SDK | 589.0.0 |
| Chrome | used headless to print the PDFs |

Rebuild the local setup:

```
cd /Users/afan/Documents/Repos/mtb-hackathon/genohack
python -m venv .venv && .venv/bin/pip install -e . pytest
gcloud storage rsync -r gs://haduh-512512-genohack/results results --project haduh-512512
gcloud compute scp --project haduh-512512 --zone us-east4-a --tunnel-through-iap genohack-analysis-us:~/genohack/ref/NC_000962.3.fasta ref/   # needs the VM running; or fetch with efetch
curl -L -o ref/mask.bed https://raw.githubusercontent.com/nextstrain/tb/master/defaults/AF14_RLC_Regions.Plus.LowPmapK50E4.H37Rv.bed
cd web && pnpm install
```

Run the demo (two terminals):

```
GENOHACK_RESULTS=results PYTHONPATH=src .venv/bin/uvicorn genohack.api:app --port 8000
cd web && pnpm dev          # http://localhost:3000
```

Other commands:

```
.venv/bin/python -m pytest                                               # 11 tests
PYTHONPATH=src .venv/bin/python -m genohack.cli report --results results --out web/data/report.json
PYTHONPATH=src .venv/bin/python -m genohack.cli windows --results results --out out   # conserved-window tables
python scripts/summarize_partial.py results 222                           # lineage, resistance, timing summary
```

**macOS Gatekeeper:** downloading the 800 MB BLAST index with `gcloud storage cp` triggered "Apple could not verify
gcloud-crc32c". It was deliberately not bypassed. Small result files sync without it. BLAST therefore runs on the VM.
The Vertex AI calls need a valid `gcloud` login on the laptop.

---

## 12. Repository map

```
README.md                  quick start, layout
pyproject.toml             package and dependencies (editable install)
envs/                      conda envs: snippy.yml, tbprofiler.yml, duckdb.yml, design.yml
sql/indonesia_isolates.sql DuckDB query over public SRA metadata
scripts/                   select_isolates.sh, process_isolate.sh (per isolate), run_full.sh (launcher),
                           watchdog.sh + install_watchdog.sh, progress.sh, setup_vm.sh, build_offtarget_db.sh,
                           build_who_subset.py, summarize_partial.py, sync_results.sh, bench_download.sh
workflow/                  Snakefile, config.yaml (design_bioproject, threads_per_isolate: 3, coverage: 100)
infra/gcp_setup.sh         the gcloud commands used to build the project (record, not idempotent)
src/genohack/              genome, targets, isolates, variants, windows, primers, probes, thermo, checks,
                           specificity, who, multiplex, assay, agent, api, cli
resources/                 GFF, WHO subset, BLAST cache, README on provenance
tests/                     test_genome.py, test_windows.py, test_multiplex.py
web/                       Next.js app: app/, components/ (App, AgentPanel, ReportView, AmpliconDiagram, ScoreBar),
                           lib/ (types.ts, mock.ts, report.ts, seq.ts), data/report.json
docs/                      HANDOVER.md, pipeline_overview.pdf/.html, progress_report.pdf/.html
```

~2,200 lines of source, 12 shell/Python scripts. No Dockerfile, no CI, no settings file yet.

---

## 13. What is needed to deploy (hosted, not yet started)

The demo runs on a laptop. To host it:

1. **Backend container** (FastAPI + design library). Needs Python deps from `pyproject.toml`, the repo's `resources/`, and the
   data the design reads: `ref/NC_000962.3.fasta`, `ref/mask.bed`, and the per-isolate `snps.aligned.fa.gz`/`snps.vcf.gz`
   (329 MB). Reading all 222 genomes per request takes about 6 s and decompresses about 1 GB; better to **precompute the
   +/-300 bp region matrices once** and ship only those (a few MB), or mount the bucket. No BLAST database needed
   (cache only; new primer pairs would report "not checked").
2. **Vertex AI access:** use a service account with `roles/aiplatform.user`; the code uses Application Default
   Credentials automatically. Env vars: `GENOHACK_PROJECT`, `GENOHACK_LOCATION` (must be `global` for this model),
   `GENOHACK_MODEL`, `GENOHACK_RESULTS`, `GENOHACK_ORIGINS` (the frontend's origin). No secret/API key is used.
3. **Frontend:** `pnpm build` then host the Next app (Cloud Run or any Node host); set `NEXT_PUBLIC_API_URL` at build time
   to the backend URL; `web/data/report.json` is baked into the build.
4. **GCP pieces to enable:** Cloud Run, Artifact Registry, Cloud Build (not enabled yet). Region near users, for example
   asia-southeast2 (Jakarta); the Gemini location stays `global`.
5. **Guards:** no authentication and no rate limit exist. For a public link set Cloud Run max-instances, put a budget
   alert on the project, and consider a simple request cap per IP. The LLM only has one validated tool, but add input
   length limits (2,000 characters already enforced) and logging.
6. **Alternative for a quick public link:** Streamlit/Hugging Face were considered earlier and dropped; a static export of the
   report page plus a recorded demo is the cheapest fallback.

Estimated effort: about half a day for containers plus deploy, longer if the live design must run on a small instance.

---

## 14. Limitations

**Science and data**
1. **In silico only.** No assay was run in a tube; Tm, dimer and probe-gap values are model estimates (Primer3
   thermodynamic alignment), not measurements. Probe discrimination (3.4-9.5 C) is modest.
2. **Coverage is in-sample.** Oligos were designed from the same 222 isolates they are measured on, so coverage is
   optimistic. The planned held-out test on the other 779 Indonesian runs has not been done.
3. **One city, one study design.** Bandung active case finding; not representative of Indonesia (the master doc
   itself says so, page 78). Lineage 1 has only 8 isolates and 3 are mixed calls, so lineage splits there mean little.
4. **Very few resistant isolates** (see section 3): the mutant alleles are seen in 2-8 isolates, so mutant-probe behaviour
   is not validated on real mutants, and the gyrA/rpoB failure counts rest on a handful of isolates.
5. **Variant calling keeps only near-fixed calls** (all 1/1). Heteroresistance and minority variants are dropped, and
   the 100x subsampling can lose low-frequency signals. The aligned FASTA holds SNPs/MNPs but not indels (the VCF
   supplies indels). Exact snippy filter cutoffs were not verified (only the depth floor of 10 is visible in the files).
6. **Target selection is manual and narrow:** 4 hotspots. Not covered: other rpoB RRDR mutations (a real rifampicin assay
   needs several probes or a melt approach), pncA (scattered mutations), embB, rrs/eis, bedaquiline/linezolid genes.
   The automated frequency-based ranking of all resistance SNPs from the meeting plan (page 81) is not built.
7. **Design on the consensus** assumes the consensus base is the wild type at the SNP; the code returns no probes if it is not.
8. **gyrA** needed a relaxed tolerance; **rpoB** has the weakest thermodynamics (50); **katG** has 2 near-matches in H37Rv.
9. **Specificity is a screen:** 14 organisms, BLAST word-size sensitivity limits, probes are not screened on their own, and
   the cache only covers the current four pairs.
10. **Multiplex is a dimer screen only:** no amplicon competition, no reaction chemistry, thresholds are assumptions,
    4 channels assumed.
11. The score and its weights are a transparent heuristic, not validated; many thresholds are my choices (section 9).

**Engineering and operations**
12. Design thresholds are scattered defaults (no settings file, no citations in code).
13. Reproducibility gaps: `results/`, `ref/` and `data/isolates.tsv` are not in git; `rasusa`, `duckdb-cli`, `snakemake`
    and `snippy`'s dependencies are not all pinned in `envs/`; only snippy, sra-tools and tb-profiler are.
14. No auth, no rate limit, no CI, no Dockerfile. The agent depends on a human `gcloud` login on the laptop.
15. The small Gemini model sometimes phrases awkwardly ("its coverage statement is...") and can echo ids like `inhA_c-15`;
    numbers are quoted from the tool, but wording is not guaranteed.
16. The interface has not had an accessibility audit; `lib/mock.ts` demo data is still shipped as a fallback.
17. Security hygiene: default SSH/RDP firewall rules open to the world, project-wide SSH key metadata, budget alerts that only email.
18. The VM disk (400 GB) still bills until deleted.

---

## 15. Gotchas learned the hard way

- `gcloud` default project is not `haduh-512512`. Always `--project`.
- Direct SSH from the user's network times out; use `--tunnel-through-iap`. A freshly created VM needs about a minute before IAP sees it.
- `pkill -f <text>` inside an SSH command can kill the shell running it (pattern matches its own command line). Use the
  `[x]` bracket trick (`pkill -f 'snakemak[e]'`) or a script file.
- Killing Snakemake **before** the launcher script shuts down the VM in older versions; current `run_full.sh` only shuts down when complete.
- `fasterq-dump --version` has no word "version"; with `set -o pipefail` a `grep` on it aborted every isolate. Version capture is now guarded.
- Detached shells have no `conda` on PATH; scripts source `${CONDA_BASE:-$HOME/miniforge3}/etc/profile.d/conda.sh`.
- ENA downloads do not resume; SRA path is the default.
- BLAST wraps ids as `gnl|<group>|<id>`; the code reads the group from any part of the id.
- Heavy jobs on the VM during the run (BLAST, report) slow it noticeably.
- `zsh` does not word-split unquoted variables; macOS `zcat` wants `.Z` (use `gzip -dc`).
- The browser preview tool needs `.claude/launch.json` at the session root (`/Users/afan/Documents/Repos/mtb-hackathon/.claude/`), not inside the project.
- Next 16 differs from older versions; read the bundled docs first.

---

## 16. What's next (prioritised)

**Before 15:00 WIB today (about 6 hours)**
1. **Update the proposal** (master doc pp. 68-71 already has a draft titled "ChatGP-TB"). Change: TRL from "concept formulated"
   to a computational prototype validated in silico (suggest TRL 3, argue it explicitly); replace the Olivar/Biopython
   claims with what was built (Primer3, snippy, TB-Profiler, BLAST, Gemini on Vertex AI); add the real results table and the
   two diagrams (`docs/pipeline_overview.pdf`) and a screenshot of the interface for "lo-fi design"; state limitations
   (section 14) plainly; fix the claim that CRyPTIC and GenoMycAnalyzer are integrated (they are not).
2. Rehearse a demo: start API and web, run "design assays for isoniazid resistance", open the multiplex card and the lineage table.
3. Decide on the VM disk (delete or keep) and clean up the firewall rules.

**Short term (days)**
4. Held-out validation: process the other 779 Indonesian runs (about 3 days of VM time at the measured rate, roughly $20-35,
   estimate) and report coverage on isolates not used in design.
5. Automated resistance-SNP ranking across the whole WHO catalogue, by evidence tier then frequency, as in the meeting plan.
6. Single settings file with cited thresholds; pin all tool versions; Dockerfiles; CI running the 11 tests.
7. More targets and multi-probe design for the rpoB RRDR; embB, pncA strategy, rrs/eis.

**Medium term**
8. Heteroresistance-aware calling (TB-Profiler minor variants / lower allele fraction).
9. Panel optimisation as in PrimeGen (SADDLE-style dimer loss, LLM or search over pair choices), PrimerAST-style scoring.
10. Compare against Xpert MTB/RIF and Deeplex Myc-TB (cost, coverage; open questions on master doc p. 10); use Indonesian tNGS data if a partnership allows.
11. Wet-lab validation with a partner lab (the proposal names TB referral hospitals, e.g. RSUP Persahabatan).
12. Hosted deployment (section 13).

---

## 17. Decision log

| Decision | Why |
|---|---|
| Pipeline modelled on Nextstrain TB (SRA metadata via DuckDB, fasterq-dump, TB-Profiler, snippy, Snakemake) | proven structure; matches team notes |
| Subsample to 100x | the average isolate is about 370x; cut compute by about 70% |
| Moved VM from Singapore to us-east4 | repeated download stalls and no resume; us-east4 is near NCBI |
| SRA default, ENA opt-in | SRA about 20% faster in a clean test, never failed |
| Skip compressing full reads | the largest single step (5-10 min/isolate) and unnecessary |
| 6 isolates x 3 threads on 16 vCPU | CPU was 45-50% idle at 4 jobs; gave about 17% more throughput |
| Watchdog on the VM, not a scheduled check from the chat | works when the laptop sleeps |
| Design on the population consensus | fixed lineage polymorphisms would otherwise be penalised against H37Rv |
| Tolerance ladder instead of dropping a target | a target silently disappearing as data grew was worse than a stated relaxation |
| Specificity as predicted products, not single-primer hits | single hits are meaningless in a 3 Gb genome |
| BLAST on the VM plus a cache on the laptop | the 842 MB index could not be downloaded (Gatekeeper); cache is keyed by primer pair |
| Gemini 3.5 flash lite on Vertex AI | user's choice; verified it exists in `global` and calls tools correctly |
| Model never emits numbers; sees a compact tool summary | grounding; earlier paraphrase errors (14/14 vs 13 + 1) |
| Next.js frontend, API called directly with CORS | cleaner interface; proxying risks buffering streamed events |

## 18. Memory and context pointers

Memory notes (auto-loaded in future sessions) are in `/Users/afan/.claude/projects/-Users-afan-Documents-Repos-mtb-hackathon/memory/`:
`feedback_push-genohack-freely.md` (standing permission to `git push` this repo; HTTPS via keychain),
`feedback_no-commit-attribution.md` (no Co-Authored-By or "Generated with" lines),
`project_genohack-gcp.md` (cloud facts and gotchas).
The earlier sections of the master document, `papers/`, TOAST (`github.com/linfeng-wang/TOAST`) and PrimeGen
(`github.com/melobio/PrimeGen`) are the reference material behind the design.
Team (from the master doc): Hanifa Syifa Kamila, Yudisto P Nadapdap, Hefina Aissa Gunawan, Ahmad Alfani Handoyo.

## 19. References and sources

R = read or fetched during this project. M = tool used here; the citation details were written from memory and should be checked before the proposal is submitted. S = found in a web search, source document not identified. N = taken from the team's notes, not read.

| # | Type | Reference | Status |
|---|---|---|---|
| [1] | Data | NCBI Sequence Read Archive / BioProject: PRJNA1433044 (Universitas Padjadjaran, Bandung active case finding; the design set), also PRJNA595834, PRJNA430531, PRJNA1150781, PRJNA633244, PRJNA950554. https://www.ncbi.nlm.nih.gov/bioproject/ | R |
| [2] | Data | SRA public metadata, AWS Open Data, s3://sra-pub-metadata-us-east-1/sra/metadata/ (queried with DuckDB); ENA file reports for read sizes, https://www.ebi.ac.uk/ena/portal/api/ | R |
| [3] | Data | H37Rv reference genome, NCBI RefSeq NC_000962.3. Cole ST et al. Deciphering the biology of Mycobacterium tuberculosis from the complete genome sequence. Nature 393:537-544 (1998). | M |
| [4] | Data | Gene annotation: Ensembl Genomes, assembly ASM19595v2 (GCA_000195955.2), file taken from the TOAST repository (MIT licence). | R |
| [5] | Data | World Health Organization. Catalogue of mutations in Mycobacterium tuberculosis complex and their association with drug resistance, 2nd edition (2023). Data files: https://github.com/GTB-tbsequencing/mutation-catalogue-2023 (MIT licence). | R |
| [6] | Data | Low-confidence region mask: Marin M et al. Benchmarking the empirical accuracy of short-read sequencing across the M. tuberculosis genome. Bioinformatics 38(7):1781-1787 (2022); file from https://github.com/nextstrain/tb (defaults/AF14_RLC_Regions.Plus.LowPmapK50E4.H37Rv.bed). | M |
| [7] | Data | Off-target genomes via NCBI Datasets, https://www.ncbi.nlm.nih.gov/datasets/ : human GRCh38 (GCF_000001405.40) and reference genomes of seven non-tuberculous mycobacteria and six respiratory bacteria (list in the handover). | R |
| [8] | Software | Seemann T. snippy: rapid haploid variant calling and core genome alignment, v4.6.0. https://github.com/tseemann/snippy | M |
| [9] | Software | Garrison E, Marth G. Haplotype-based variant detection from short-read sequencing. arXiv:1207.3907 (2012) (FreeBayes 1.3.6, run inside snippy). | M |
| [10] | Software | Li H. Aligning sequence reads, clone sequences and assembly contigs with BWA-MEM. arXiv:1303.3997 (2013). | M |
| [11] | Software | Phelan JE et al. Integrating informatics tools and portable sequencing technology for rapid detection of resistance to anti-tuberculous drugs. Genome Medicine 11:41 (2019) (TB-Profiler 6.6.5). | M |
| [12] | Software | Hall M. Rasusa: randomly subsample sequencing reads to a specified coverage. Journal of Open Source Software 7(69):3941 (2022) (v5.1.0). | M |
| [13] | Software | NCBI SRA Toolkit (fasterq-dump 3.2.1). https://github.com/ncbi/sra-tools | M |
| [14] | Software | Mölder F et al. Sustainable data analysis with Snakemake. F1000Research 10:33 (2021). | M |
| [15] | Software | Raasveldt M, Mühleisen H. DuckDB: an embeddable analytical database. SIGMOD 2019. | M |
| [16] | Software | Untergasser A et al. Primer3: new capabilities and interfaces. Nucleic Acids Research 40(15):e115 (2012); Python bindings primer3-py 2.4.0, https://github.com/libnano/primer3-py | M |
| [17] | Software | Camacho C et al. BLAST+: architecture and applications. BMC Bioinformatics 10:421 (2009) (blastn 2.17.0+). | M |
| [18] | Software | Ye J et al. Primer-BLAST: a tool to design target-specific primers for polymerase chain reaction. BMC Bioinformatics 13:134 (2012). The off-target product screen is inspired by it but is not identical to its defaults. | M |
| [19] | Software | Google Cloud Vertex AI and Gemini (model gemini-3.5-flash-lite, location global), https://cloud.google.com/vertex-ai ; google-genai SDK; FastAPI, https://fastapi.tiangolo.com ; Next.js 16, https://nextjs.org/docs (bundled docs read) ; Tailwind CSS 4. | R |
| [20] | Prior work | Wang L et al. TOAST: a novel tool for designing targeted gene amplicons and an optimised set of primers for high-throughput sequencing in tuberculosis genomic studies. BMC Genomics 26:1058 (2025). doi:10.1186/s12864-025-12247-9 ; https://github.com/linfeng-wang/TOAST | R |
| [21] | Prior work | Wang Y et al. Accelerating primer design for amplicon sequencing using large language model-powered agents (PrimeGen). Nature Biomedical Engineering 10:338-353 (2026). doi:10.1038/s41551-025-01455-z ; https://github.com/melobio/PrimeGen | R |
| [22] | Prior work | Nextstrain TB build, https://nextstrain.org/tb/global and https://github.com/nextstrain/tb : the per-isolate processing (SRA metadata query, fasterq-dump, TB-Profiler, snippy, Snakemake) is modelled on it. | R |
| [23] | Prior work | Xie NG et al. Designing highly multiplex PCR primer sets with Simulated Annealing Design using Dimer Likelihood Estimation (SADDLE). Nature Communications 13:1881 (2022). Cited in the PrimeGen paper; not used in the code. | M |
| [24] | Prior work | Multiplex real-time PCR melting curve assay to detect drug-resistant mutations of Mycobacterium tuberculosis. Journal of Clinical Microbiology (2011). https://pubmed.ncbi.nlm.nih.gov/21752982 : found in a web search; the basis for the melt-probe idea for dense regions such as the rpoB RRDR. | S |
| [25] | Prior work | Comparative genomic analysis of established and emerging anti-tubercular drug targets ... in Mycobacterium tuberculosis isolates from Indonesia. Frontiers in Tropical Diseases (2026). doi:10.3389/fitd.2026.1953716 : listed in the team notes (master document p. 76); not read. | N |
| [26] | Prior work | GenoHack Master Document (team notes, Indonesian), including the meeting plan 'Kesimpulan Meet 23/10/26' (p. 81) and the draft proposal with its own reference list (pp. 68-72). | R |
| [27] | Thresholds | Design thresholds: the TOAST default settings file and the PrimeGen paper (both read); a web search result (patent text, specific patent not identified) for probe Tm 8-12 C above the primers and amplicons of 50-150 bp; general qPCR practice from memory. The dimer limit of about -9 kcal/mol is the commonly quoted manufacturer guidance, not verified here. See handover section 9. | S |
| [28] | Cost | Google Cloud Billing Catalog API (E2 core and RAM and balanced persistent disk prices, us-east4 and asia-southeast1), https://cloud.google.com/billing/docs/how-to/get-pricing-information-api ; cross-check for e2-standard-8 in Singapore: https://pcr.cloud-mercato.com/providers/google/flavors/e2-standard-8.skylake and https://calculator.holori.com/gcp/vm/e2-standard-2/asia-southeast1 (third-party listings). | R |

Citation numbers in the progress report refer to this list.
