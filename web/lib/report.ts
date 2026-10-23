import type { Report } from "./types";
import { mockReport } from "./mock";
import generated from "../data/report.json";

// Use the report produced by `python -m genohack.cli report` when it exists, else the demo data.
export function loadReport(): Report {
  const r = generated as unknown as Report;
  return r && Array.isArray(r.candidates) && r.candidates.length > 0 ? r : mockReport;
}
