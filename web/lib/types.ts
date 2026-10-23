// Contract between the Python backend and this UI. The backend returns a Report; the UI renders it.
// Length and GC are derived from the sequence in the UI, so they can never disagree with it.

export type StepStatus = "done" | "running" | "pending";

export interface ToolStep {
  id: string;
  tool: string; // function name the agent called
  label: string; // human-readable summary
  detail?: string;
  status: StepStatus;
  seconds?: number;
}

export type OligoRole = "forward" | "reverse" | "probe_wt" | "probe_mut";

export interface Oligo {
  name: string;
  role: OligoRole;
  sequence: string; // 5'->3'
  start: number; // 1-based genome coordinate on NC_000962.3
  end: number;
  strand: "+" | "-";
  tm: number; // degrees C
  hairpin_dg?: number; // kcal/mol
  self_dimer_dg?: number; // kcal/mol
  mismatch_dtm?: number; // probes only: Tm drop against the other allele, degrees C
}

export interface Coverage {
  isolates_total: number;
  perfect_match: number; // isolates with zero mismatches at every oligo
  one_mismatch: number; // isolates with one mismatch outside the 3' end
  failing: number; // isolates with a mismatch that is likely to break the assay
}

export interface Specificity {
  human_hits: number | null; // null: not checked yet
  ntm_hits: number | null;
  note: string;
}

export interface Scores {
  conservation: number; // 0-100
  resistance_evidence: number | null; // null when the mutation is not in the WHO catalogue
  specificity: number;
  thermodynamics: number;
  overall: number;
}

export interface Candidate {
  id: string;
  rank: number;
  gene: string;
  drug: string;
  mutation: string; // protein-level change, e.g. p.Ser450Leu
  genome_pos: number;
  who_tier: string; // WHO catalogue confidence group
  amplicon_start: number;
  amplicon_end: number;
  oligos: Oligo[];
  scores: Scores;
  coverage: Coverage;
  specificity: Specificity;
  reasons: string[];
  caveats: string[];
  validation: "in_silico";
}

export interface Report {
  mock: boolean; // true while the UI runs on demo data
  request: string;
  summary: string;
  generated_at: string;
  dataset: {
    name: string;
    bioproject: string;
    isolates: number;
    reference: string;
  };
  steps: ToolStep[];
  candidates: Candidate[];
}
