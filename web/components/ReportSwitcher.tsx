"use client";

import { ago, type Session } from "@/lib/sessions";

// Moves between the reports a chat has produced. A chat with no report shows an empty state instead.
export default function ReportSwitcher({ session, onShow }: { session: Session; onShow: (id: string | null) => void }) {
  if (session.reports.length === 0) return null;
  const ids = session.reports.map((r) => r.id);
  // Chats saved before the empty state could point at the old starting report (null); they show the latest report.
  const activeId = session.activeReportId ?? ids[ids.length - 1];
  const at = ids.indexOf(activeId);
  const go = (delta: number) => onShow(ids[Math.min(ids.length - 1, Math.max(0, at + delta))]);
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-surface px-4 py-2.5 text-xs">
      <span className="text-muted">Results from this chat</span>
      <button type="button" onClick={() => go(-1)} disabled={at <= 0} aria-label="Previous report" className="rounded-md border border-line px-2 py-0.5 disabled:opacity-40">
        ‹
      </button>
      <label className="min-w-0 flex-1">
        <span className="sr-only">Choose a report</span>
        <select
          value={activeId}
          onChange={(e) => onShow(e.target.value)}
          className="w-full min-w-0 truncate rounded-md border border-line bg-bg px-2 py-1 text-ink"
        >
          {session.reports.map((r, i) => (
            <option key={r.id} value={r.id}>
              {i + 1}. {r.label} · {ago(r.at)}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={() => go(1)} disabled={at >= ids.length - 1} aria-label="Next report" className="rounded-md border border-line px-2 py-0.5 disabled:opacity-40">
        ›
      </button>
      <span className="tabular-nums text-muted">
        {at + 1} of {ids.length}
      </span>
    </div>
  );
}
