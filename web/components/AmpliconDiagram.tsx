import type { Candidate } from "@/lib/types";
import { formatPos } from "@/lib/seq";

// Schematic of one assay: amplicon baseline, forward primer above, reverse primer below,
// probe on the line, and a tick at the resistance mutation.
export default function AmpliconDiagram({ c }: { c: Candidate }) {
  const W = 640;
  const pad = 28;
  const span = c.amplicon_end - c.amplicon_start;
  const x = (p: number) => pad + ((p - c.amplicon_start) / span) * (W - 2 * pad);
  const fwd = c.oligos.find((o) => o.role === "forward");
  const rev = c.oligos.find((o) => o.role === "reverse");
  const probe = c.oligos.find((o) => o.role === "probe_wt");
  const bar = (start: number, end: number) => ({ x: x(start), w: Math.max(6, x(end) - x(start)) });

  return (
    <svg viewBox={`0 0 ${W} 118`} className="w-full" role="img" aria-label={`Amplicon layout for ${c.gene} ${c.mutation}`}>
      <line x1={pad} x2={W - pad} y1={58} y2={58} stroke="var(--line)" strokeWidth={2} />
      {fwd && (
        <g>
          <rect x={bar(fwd.start, fwd.end).x} y={34} width={bar(fwd.start, fwd.end).w} height={12} rx={3} fill="var(--accent)" />
          <text x={bar(fwd.start, fwd.end).x} y={26} fontSize={11} fill="var(--muted)">Forward primer</text>
        </g>
      )}
      {rev && (
        <g>
          <rect x={bar(rev.start, rev.end).x} y={70} width={bar(rev.start, rev.end).w} height={12} rx={3} fill="var(--accent)" />
          <text x={bar(rev.start, rev.end).x + bar(rev.start, rev.end).w} y={98} fontSize={11} textAnchor="end" fill="var(--muted)">Reverse primer</text>
        </g>
      )}
      {probe && (
        <g>
          <rect x={bar(probe.start, probe.end).x} y={52} width={bar(probe.start, probe.end).w} height={12} rx={3} fill="var(--probe)" />
          <text x={bar(probe.start, probe.end).x + bar(probe.start, probe.end).w / 2} y={26} fontSize={11} textAnchor="middle" fill="var(--muted)">
            Probes (wild-type, mutant)
          </text>
        </g>
      )}
      <g>
        <line x1={x(c.genome_pos)} x2={x(c.genome_pos)} y1={44} y2={72} stroke="var(--bad)" strokeWidth={1.5} strokeDasharray="3 3" />
        <text x={x(c.genome_pos)} y={110} fontSize={11} textAnchor="middle" fill="var(--bad)">{c.mutation}</text>
      </g>
      <text x={pad} y={14} fontSize={10} fill="var(--muted)">{formatPos(c.amplicon_start)}</text>
      <text x={W - pad} y={14} fontSize={10} textAnchor="end" fill="var(--muted)">{formatPos(c.amplicon_end)}</text>
    </svg>
  );
}
