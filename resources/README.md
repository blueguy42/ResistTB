# Resources

- `H37Rv_ASM19595v2.gff`: Ensembl Genomes annotation of M. tuberculosis H37Rv (ASM19595v2). The chromosome
  is named `Chromosome` here and `NC_000962.3` in the variant files; the sequence and coordinates are the
  same (length 4,411,532). Copied from the TOAST repository (MIT licence),
  https://github.com/linfeng-wang/TOAST, file `toast_amplicon/db/MTB-h37rv_asm19595v2-eg18.gff`.
- `who_catalogue_2023_assoc_with_R.csv`: variants graded "Assoc w R" (grade 1) or "Assoc w R - Interim" (grade 2) in
  the WHO catalogue of mutations in M. tuberculosis complex, 2nd edition (2023), with evidence counts and genome
  coordinates of the single-nucleotide form. Built by `scripts/build_who_subset.py` from
  https://github.com/GTB-tbsequencing/mutation-catalogue-2023 (MIT licence). The catalogue names the inhA promoter
  variant at position 1,673,425 `inhA_c.-777C>T`; the literature calls it fabG1 c.-15C>T.
