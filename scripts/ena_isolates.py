"""Write an isolate list (same columns as data/isolates.tsv) for BioProjects that are not in the Indonesia query.

Run: python scripts/ena_isolates.py PRJNA1256943 PRJNA898845 > resources/isolates_extra.tsv
Reads ENA's public run metadata only; nothing is downloaded. Keeps Illumina paired-end M. tuberculosis WGS runs.
"""
import csv
import io
import sys
import urllib.request

FIELDS = (
    "run_accession,sample_accession,sample_alias,center_name,instrument_platform,instrument_model,library_layout,"
    "library_selection,library_strategy,library_source,scientific_name,read_count,base_count,fastq_bytes,country,"
    "collection_date,first_public"
)
HEADER = [
    "acc", "bioproject", "biosample", "sample_name", "center_name", "platform", "instrument", "librarylayout",
    "libraryselection", "mbytes", "mbases", "avgspotlen", "country", "geo_loc_name_sam", "collection_date_sam", "releasedate",
]


def main(projects: list[str]) -> None:
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    out.writerow(HEADER)
    for p in projects:
        url = f"https://www.ebi.ac.uk/ena/portal/api/filereport?accession={p}&result=read_run&fields={FIELDS}&format=tsv"
        text = urllib.request.urlopen(url, timeout=120).read().decode()
        kept = skipped = 0
        for r in csv.DictReader(io.StringIO(text), delimiter="\t"):
            if not (r["instrument_platform"] == "ILLUMINA" and r["library_layout"] == "PAIRED"
                    and r["library_strategy"] == "WGS" and r["library_source"] == "GENOMIC"
                    and r["scientific_name"].startswith("Mycobacterium tuberculosis")):
                skipped += 1
                continue
            mbytes = sum(int(x) for x in r["fastq_bytes"].split(";") if x) / 1e6
            reads = int(r["read_count"] or 0)
            out.writerow([
                r["run_accession"], p, r["sample_accession"], r["sample_alias"], r["center_name"], "ILLUMINA",
                r["instrument_model"], "PAIRED", r["library_selection"], round(mbytes), round(int(r["base_count"] or 0) / 1e6),
                round(int(r["base_count"] or 0) / reads) if reads else "", r["country"].split(":")[0], r["country"],
                r["collection_date"], r["first_public"],
            ])
            kept += 1
        print(f"{p}: kept {kept}, skipped {skipped}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
