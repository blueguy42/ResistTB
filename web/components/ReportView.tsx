"use client";

import type { Candidate, Oligo, Report } from "@/lib/types";
import { formatPos, gcPercent } from "@/lib/seq";
import AmpliconDiagram from "./AmpliconDiagram";
import ScoreBar from "./ScoreBar";

const ROLE_LABEL: Record<Oligo["role"], string> = {
  forward: "Forward primer",
  reverse: "Reverse primer",
  probe_wt: "Probe, wild-type",
  probe_mut: "Probe, mutant",
};

function pct(n: number, total: number) {
  return total ? Math.round((n / total) * 100) : 0;
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface px-4 py-3">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  );
}

function CoverageBar({ c }: { c: Candidate["coverage"] }) {
  const parts = [
    { key: "perfect", n: c.perfect_match, color: "var(--accent)", label: "Perfect match" },
    { key: "one", n: c.one_mismatch, color: "var(--warn)", label: "One mismatch" },
    { key: "fail", n: c.failing, color: "var(--bad)", label: "Likely to fail" },
  ];
  return (
    <div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-line">
        {parts.map((p) => (
          <div key={p.key} style={{ width: `${(p.n / c.isolates_total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {parts.map((p) => (
          <span key={p.key} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: p.color }} />
            {p.label}: <span className="font-mono tabular-nums text-ink">{p.n}</span>
          </span>
        ))}
        <span>of {c.isolates_total} isolates</span>
      </div>
    </div>
  );
}

function OligoTable({ oligos }: { oligos: Oligo[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="text-xs text-muted">
          <tr className="border-b border-line">
            <th className="py-2 pr-3 font-normal">Oligo</th>
            <th className="py-2 pr-3 font-normal">Sequence (5′→3′)</th>
            <th className="py-2 pr-3 text-right font-normal">Length</th>
            <th className="py-2 pr-3 text-right font-normal">GC %</th>
            <th className="py-2 pr-3 text-right font-normal">Tm °C</th>
            <th className="py-2 text-right font-normal">Tm gap °C</th>
          </tr>
        </thead>
        <tbody>
          {oligos.map((o) => (
            <tr key={o.name} className="border-b border-line last:border-0">
              <td className="py-2.5 pr-3">
                <div className="font-medium">{ROLE_LABEL[o.role]}</div>
                <div className="text-xs text-muted">
                  {formatPos(o.start)}–{formatPos(o.end)} ({o.strand})
                </div>
              </td>
              <td className="py-2.5 pr-3 font-mono text-[13px] tracking-wide">{o.sequence}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{o.sequence.length}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{gcPercent(o.sequence).toFixed(0)}</td>
              <td className="py-2.5 pr-3 text-right tabular-nums">{o.tm.toFixed(1)}</td>
              <td className="py-2.5 text-right tabular-nums">{o.mismatch_dtm ? o.mismatch_dtm.toFixed(1) : "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Detail({ c }: { c: Candidate }) {
  return (
    <div className="rounded-2xl border border-line bg-surface">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              {c.gene} <span className="font-mono text-base font-normal text-muted">{c.mutation}</span>
            </h2>
            <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">Rank {c.rank}</span>
          </div>
          <div className="mt-0.5 text-sm text-muted">
            {c.drug} · WHO: {c.who_tier} · position {formatPos(c.genome_pos)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-semibold tabular-nums leading-none">{c.scores.overall}</div>
          <div className="mt-1 text-xs text-muted">Overall score</div>
        </div>
      </div>

      <div className="grid gap-6 px-5 py-5 lg:grid-cols-[1fr_220px]">
        <div className="min-w-0 space-y-6">
          <AmpliconDiagram c={c} />
          <OligoTable oligos={c.oligos} />
        </div>
        <div className="space-y-3">
          <ScoreBar label="Conservation" value={c.scores.conservation} />
          {c.scores.resistance_evidence !== null && <ScoreBar label="Resistance evidence" value={c.scores.resistance_evidence} />}
          <ScoreBar label="Specificity" value={c.scores.specificity} />
          <ScoreBar label="Thermodynamics" value={c.scores.thermodynamics} />
        </div>
      </div>

      <div className="grid gap-6 border-t border-line px-5 py-5 md:grid-cols-2">
        <section>
          <h3 className="mb-2 text-sm font-medium">Coverage in the isolate set</h3>
          <CoverageBar c={c.coverage} />
        </section>
        <section>
          <h3 className="mb-2 text-sm font-medium">Specificity</h3>
          <p className="text-sm text-muted">
            Human: <span className="font-mono text-ink">{c.specificity.human_hits ?? "not checked"}</span>
            {" · "}Non-tuberculous: <span className="font-mono text-ink">{c.specificity.ntm_hits ?? "not checked"}</span>. {c.specificity.note}
          </p>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-medium">Why it ranks here</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
            {c.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
        <section>
          <h3 className="mb-2 text-sm font-medium">Risks and limits</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
            {c.caveats.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      </div>
      <div className="border-t border-line px-5 py-3 text-xs text-muted">Validation status: in silico only, not tested in the lab.</div>
    </div>
  );
}

export default function ReportView({
  report,
  selectedId,
  onSelect,
}: {
  report: Report;
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  const selected = report.candidates.find((c) => c.id === selectedId) ?? report.candidates[0];
  const best = report.candidates[0];
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Isolates" value={String(report.dataset.isolates)} sub={report.dataset.bioproject} />
        <Stat label="Candidates" value={String(report.candidates.length)} sub="ranked assays" />
        <Stat label="Top score" value={String(best.scores.overall)} sub={`${best.gene} ${best.mutation}`} />
        <Stat label="Reference" value="H37Rv" sub={report.dataset.reference} />
      </div>

      <div className="overflow-hidden rounded-2xl border border-line bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="bg-bg text-xs text-muted">
            <tr>
              <th className="px-4 py-2.5 font-normal">Rank</th>
              <th className="px-4 py-2.5 font-normal">Target</th>
              <th className="hidden px-4 py-2.5 font-normal sm:table-cell">Drug</th>
              <th className="px-4 py-2.5 font-normal">Coverage</th>
              <th className="px-4 py-2.5 text-right font-normal">Score</th>
            </tr>
          </thead>
          <tbody>
            {report.candidates.map((c) => {
              const active = c.id === selected.id;
              const cov = pct(c.coverage.perfect_match, c.coverage.isolates_total);
              return (
                <tr
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  className={`cursor-pointer border-t border-line transition-colors ${active ? "bg-accent-soft" : "hover:bg-bg"}`}
                >
                  <td className="px-4 py-3 tabular-nums">{c.rank}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onSelect(c.id)}
                      className="text-left font-medium focus-visible:outline-2 focus-visible:outline-accent"
                      aria-pressed={active}
                    >
                      {c.gene} <span className="font-mono font-normal text-muted">{c.mutation}</span>
                    </button>
                  </td>
                  <td className="hidden px-4 py-3 text-muted sm:table-cell">{c.drug}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-line">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${cov}%` }} />
                      </div>
                      <span className="text-xs tabular-nums text-muted">{cov}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold tabular-nums">{c.scores.overall}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Detail c={selected} />
    </div>
  );
}
