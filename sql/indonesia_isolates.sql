-- Lists Illumina WGS runs of M. tuberculosis from Indonesia in the public SRA metadata
-- (AWS open data mirror, anonymous access). Run with: duckdb -f sql/indonesia_isolates.sql
INSTALL httpfs;
LOAD httpfs;
INSTALL parquet;
LOAD parquet;

SET s3_region = 'us-east-1';
SET s3_endpoint = 's3.amazonaws.com';

COPY (
    SELECT
        acc,
        bioproject,
        biosample,
        sample_name,
        center_name,
        platform,
        instrument,
        librarylayout,
        libraryselection,
        mbytes,
        mbases,
        avgspotlen,
        geo_loc_name_country_calc AS country,
        geo_loc_name_sam,
        collection_date_sam,
        releasedate
    FROM read_parquet('s3://sra-pub-metadata-us-east-1/sra/metadata/*')
    WHERE lower(organism) LIKE '%mycobacterium tuberculosis%'
      AND platform = 'ILLUMINA'
      AND assay_type IN ('WGS', 'WGA')
      AND librarysource = 'GENOMIC'
      AND mbases > 180
      AND geo_loc_name_country_calc = 'Indonesia'
    ORDER BY bioproject, acc
) TO 'data/isolates.tsv' (FORMAT CSV, DELIMITER '\t', HEADER);
