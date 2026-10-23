# genohack: ChatGP-TB

Genomics-guided primer and probe design for drug-resistant *M. tuberculosis*.
GenoHack 2026 prototype. All results are in silico.

## Layout

| Path | Purpose |
|---|---|
| `sql/` | DuckDB query that lists Indonesian MTB isolates from the public SRA metadata |
| `scripts/` | Per-isolate processing and VM setup |
| `workflow/` | Snakemake workflow (resumable, one isolate at a time) |
| `envs/` | Conda environments, one per tool group |
| `infra/` | The `gcloud` commands used to build the GCP environment |
| `data/`, `work/`, `results/` | Local data, git-ignored |

## Pipeline

1. `scripts/select_isolates.sh` queries SRA metadata and writes `data/isolates.tsv`.
2. `workflow/Snakefile` runs `scripts/process_isolate.sh` per isolate:
   download (`fasterq-dump`), subsample to about 100x (`rasusa`), `tb-profiler`, `snippy`
   against H37Rv (NC_000962.3), upload small outputs to Cloud Storage, delete the reads.
3. Downstream (to build): masked variant table, conserved-window ranking, resistance-SNP
   ranking, Primer3 primers, probe design, specificity, multiplex and coverage checks.

The per-isolate approach follows the design of the Nextstrain TB build
(https://github.com/nextstrain/tb). Tool versions are pinned in `envs/`.

## GCP

Project `haduh-512512`, region `asia-southeast1`. See `infra/gcp_setup.sh`.

## Quick start on the VM

```bash
git clone git@github.com:blueguy42/genohack.git && cd genohack
bash scripts/setup_vm.sh
export BUCKET=gs://haduh-512512-genohack
bash scripts/select_isolates.sh
snakemake -s workflow/Snakefile --cores 8 --jobs 2
```

## Stopping early

Each isolate is uploaded to the bucket the moment it finishes, and isolates run in a fixed random
order, so whatever is done at any point is a fair sample. To show partial results:

```bash
bash scripts/sync_results.sh               # pull finished isolates from the bucket
python scripts/summarize_partial.py        # lineage, resistance, variant tables in results/summary/
```

Re-running `snakemake` later resumes where it stopped. If the design changes, nothing is lost:
the stored outputs (VCF, aligned FASTA, TB-Profiler JSON) do not depend on the downstream design.

Time one isolate first (`bash scripts/process_isolate.sh SRR37495311 8 100`) before running all.
