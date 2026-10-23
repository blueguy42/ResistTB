import type { Candidate, Report } from "./types";

// DEMO DATA. Gene, drug and mutation labels are real targets from the WHO catalogue, but every
// sequence, score, coordinate-derived number and coverage figure below is made up to exercise
// the interface. None of it is a result. The UI shows a banner while report.mock is true.

const candidates: Candidate[] = [
  {
    id: "rpoB-S450L",
    rank: 1,
    gene: "rpoB",
    drug: "Rifampicin",
    mutation: "p.Ser450Leu",
    genome_pos: 761155,
    who_tier: "Assoc w R",
    amplicon_start: 761060,
    amplicon_end: 761218,
    oligos: [
      { name: "rpoB-F (demo)", role: "forward", sequence: "GCTGTCGGGGTTGACCCAC", start: 761060, end: 761078, strand: "+", tm: 60.4, hairpin_dg: -0.8, self_dimer_dg: -3.1 },
      { name: "rpoB-R (demo)", role: "reverse", sequence: "CGATCACACCGCAGACGTT", start: 761200, end: 761218, strand: "-", tm: 60.1, hairpin_dg: -0.4, self_dimer_dg: -2.6 },
      { name: "rpoB-WT probe (demo)", role: "probe_wt", sequence: "CAGCCAGCTGAGCCAATTCATGGA", start: 761142, end: 761165, strand: "+", tm: 69.8, mismatch_dtm: 7.9 },
      { name: "rpoB-S450L probe (demo)", role: "probe_mut", sequence: "CAGCCAGCTGAGCCAATTCATGGA".replace("GAGCCAATT", "GAGCCAATC"), start: 761142, end: 761165, strand: "+", tm: 69.5, mismatch_dtm: 8.3 },
    ],
    scores: { conservation: 94, resistance_evidence: 98, specificity: 96, thermodynamics: 88, overall: 94 },
    coverage: { isolates_total: 222, perfect_match: 214, one_mismatch: 6, failing: 2 },
    specificity: { human_hits: 0, ntm_hits: 1, note: "One partial match in a related mycobacterial genome, outside the primer 3' ends." },
    reasons: [
      "Mutation hotspot in the rifampicin resistance region, the highest evidence tier.",
      "Flanking windows are among the most conserved in the isolate set.",
      "Probe separates wild-type from mutant by a large Tm gap.",
    ],
    caveats: [
      "Demo values: not computed from real data.",
      "Other rpoB mutations in the same region would need extra probes.",
    ],
    validation: "in_silico",
  },
  {
    id: "katG-S315T",
    rank: 2,
    gene: "katG",
    drug: "Isoniazid",
    mutation: "p.Ser315Thr",
    genome_pos: 2155168,
    who_tier: "Assoc w R",
    amplicon_start: 2155070,
    amplicon_end: 2155240,
    oligos: [
      { name: "katG-F (demo)", role: "forward", sequence: "AGGAAACTGTTGTCCCATTTCG", start: 2155070, end: 2155091, strand: "+", tm: 59.7, hairpin_dg: -0.5, self_dimer_dg: -2.2 },
      { name: "katG-R (demo)", role: "reverse", sequence: "GTCAACCAGCGGGTCAACAT", start: 2155221, end: 2155240, strand: "-", tm: 60.2, hairpin_dg: -1.1, self_dimer_dg: -3.4 },
      { name: "katG-WT probe (demo)", role: "probe_wt", sequence: "GATCACCAGCGGCATCGAGGGCC", start: 2155150, end: 2155172, strand: "+", tm: 70.1, mismatch_dtm: 6.8 },
      { name: "katG-S315T probe (demo)", role: "probe_mut", sequence: "GATCACCACCGGCATCGAGGGCC", start: 2155150, end: 2155172, strand: "+", tm: 69.4, mismatch_dtm: 7.1 },
    ],
    scores: { conservation: 90, resistance_evidence: 97, specificity: 93, thermodynamics: 85, overall: 91 },
    coverage: { isolates_total: 222, perfect_match: 209, one_mismatch: 9, failing: 4 },
    specificity: { human_hits: 0, ntm_hits: 2, note: "Two partial matches in non-tuberculous mycobacteria; none at the primer 3' ends." },
    reasons: [
      "The most frequent isoniazid resistance mutation.",
      "Single-nucleotide change gives a clean wild-type versus mutant probe pair.",
    ],
    caveats: [
      "Demo values: not computed from real data.",
      "A lineage-specific variant near the reverse primer lowers coverage in some isolates.",
    ],
    validation: "in_silico",
  },
  {
    id: "inhA-c-15",
    rank: 3,
    gene: "inhA promoter",
    drug: "Isoniazid, ethionamide",
    mutation: "c.-15C>T",
    genome_pos: 1673425,
    who_tier: "Assoc w R",
    amplicon_start: 1673330,
    amplicon_end: 1673489,
    oligos: [
      { name: "inhA-F (demo)", role: "forward", sequence: "CCTCGCTGCCCAGAAAGG", start: 1673330, end: 1673347, strand: "+", tm: 60.6, hairpin_dg: -0.2, self_dimer_dg: -1.9 },
      { name: "inhA-R (demo)", role: "reverse", sequence: "TGGTCGGCAGACCTACGT", start: 1673472, end: 1673489, strand: "-", tm: 60.3, hairpin_dg: -0.9, self_dimer_dg: -2.8 },
      { name: "inhA-WT probe (demo)", role: "probe_wt", sequence: "ATATCGCCGACCTCACATACCTG", start: 1673405, end: 1673427, strand: "+", tm: 68.9, mismatch_dtm: 5.6 },
      { name: "inhA-c-15 probe (demo)", role: "probe_mut", sequence: "ATATCGCCGACCTCATATACCTG", start: 1673405, end: 1673427, strand: "+", tm: 68.2, mismatch_dtm: 6.0 },
    ],
    scores: { conservation: 82, resistance_evidence: 95, specificity: 90, thermodynamics: 79, overall: 85 },
    coverage: { isolates_total: 222, perfect_match: 201, one_mismatch: 12, failing: 9 },
    specificity: { human_hits: 0, ntm_hits: 3, note: "Promoter region is GC-rich; three partial matches in other mycobacteria." },
    reasons: ["Common low-level isoniazid resistance marker outside the katG gene."],
    caveats: [
      "Demo values: not computed from real data.",
      "GC-rich context makes the probe Tm gap smaller, so discrimination is the weakest of the three.",
    ],
    validation: "in_silico",
  },
];

export const mockReport: Report = {
  mock: true,
  request: "Design a qPCR assay for rifampicin and isoniazid resistance in Indonesian TB.",
  summary:
    "I found three candidate assays covering the main rifampicin and isoniazid resistance hotspots. The rpoB S450L assay ranks first: its flanking regions are the most conserved across the isolate set and its probes separate wild-type from mutant clearly. All results are in silico only.",
  generated_at: "demo",
  dataset: {
    name: "Bandung active case finding",
    bioproject: "PRJNA1433044",
    isolates: 222,
    reference: "NC_000962.3 (H37Rv)",
  },
  steps: [
    { id: "s1", tool: "get_variants", label: "Load variant table for rpoB, katG, inhA", detail: "222 isolates", status: "done", seconds: 1.2 },
    { id: "s2", tool: "rank_conserved_windows", label: "Rank conserved windows around each target", detail: "3 targets", status: "done", seconds: 0.8 },
    { id: "s3", tool: "rank_resistance_snps", label: "Rank resistance mutations", detail: "WHO catalogue tier, then frequency", status: "done", seconds: 0.6 },
    { id: "s4", tool: "design_primers", label: "Design primer pairs", detail: "Primer3", status: "done", seconds: 2.4 },
    { id: "s5", tool: "design_probes", label: "Design wild-type and mutant probes", status: "done", seconds: 3.1 },
    { id: "s6", tool: "check_specificity", label: "Check against human and non-tuberculous genomes", detail: "BLAST", status: "done", seconds: 5.7 },
    { id: "s7", tool: "check_coverage", label: "Match oligos against each isolate", status: "done", seconds: 1.9 },
  ],
  candidates,
};
