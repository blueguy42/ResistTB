"use client";

import { useMemo, useState } from "react";
import type { Library, LibraryTarget } from "@/lib/types";

const MAX_PICK = 6; // the backend designs at most this many per request

function drugsOf(t: LibraryTarget) {
  return t.drug.split(", ");
}

export default function TargetLibrary({
  library,
  current,
  busy,
  onDesign,
}: {
  library: Library;
  current: string[]; // ids shown in the report now
  busy: boolean;
  onDesign: (ids: string[]) => void;
}) {
  const [open, setOpen] = useState(true);
  const [drug, setDrug] = useState("All drugs");
  const [query, setQuery] = useState("");
  const [showNoDesign, setShowNoDesign] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);

  const drugs = useMemo(() => {
    const count = new Map<string, number>();
    for (const t of library.targets) for (const d of drugsOf(t)) count.set(d, (count.get(d) ?? 0) + 1);
    return [...count.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [library]);

  const designed = library.targets.filter((t) => t.status === "designed").length;
  const regionNames = Object.keys(library.regions);
  const multiRegion = regionNames.length > 1;

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return library.targets
      .filter((t) => (showNoDesign || t.status === "designed") && (drug === "All drugs" || drugsOf(t).includes(drug)))
      .filter((t) => !q || `${t.gene} ${t.mutation} ${t.id}`.toLowerCase().includes(q))
      .sort((a, b) => b.resistant_isolates - a.resistant_isolates);
  }, [library, drug, query, showNoDesign]);

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < MAX_PICK ? [...p, id] : p));

  return (
    <section className="rounded-2xl border border-line bg-surface px-5 py-4" aria-label="Target library">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-medium">Target library</h3>
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="text-xs text-muted hover:text-ink">
          {open ? "Hide" : "Show"}
        </button>
      </div>
      <p className="mt-1 text-xs text-muted">
        {designed} of {library.targets.length} WHO resistance variants have a design on {library.isolates} isolates
        {multiRegion ? ` from ${regionNames.length} regions` : ""}. Pick up to {MAX_PICK} to design them together.
      </p>

      {open && (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <label className="flex items-center gap-1.5">
              <span className="text-muted">Drug</span>
              <select
                value={drug}
                onChange={(e) => setDrug(e.target.value)}
                className="rounded-md border border-line bg-bg px-2 py-1 text-ink"
              >
                <option>All drugs</option>
                {drugs.map(([d, n]) => (
                  <option key={d} value={d}>
                    {d} ({n})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">Search</span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="gene or variant, e.g. embB"
                className="w-44 rounded-md border border-line bg-bg px-2 py-1 text-ink placeholder:text-muted"
              />
            </label>
            <label className="flex items-center gap-1.5 text-muted">
              <input type="checkbox" checked={showNoDesign} onChange={(e) => setShowNoDesign(e.target.checked)} />
              Include targets with no design
            </label>
            <span className="ml-auto tabular-nums text-muted">{rows.length} shown</span>
          </div>

          <div className="mt-3 max-h-80 overflow-auto rounded-xl border border-line">
            <table className="w-full min-w-[560px] text-left text-xs">
              <thead className="sticky top-0 bg-surface text-muted">
                <tr className="border-b border-line">
                  <th className="w-8 py-1.5 pl-3 font-normal"><span className="sr-only">Pick</span></th>
                  <th className="py-1.5 pr-3 font-normal">Variant</th>
                  <th className="py-1.5 pr-3 font-normal">Drug</th>
                  <th className="py-1.5 pr-3 text-right font-normal" title="Resistant isolates the WHO catalogue lists with this variant">WHO isolates</th>
                  <th className="py-1.5 pr-3 text-right font-normal">Score</th>
                  <th className="py-1.5 pr-3 text-right font-normal">Exact match</th>
                  {multiRegion && <th className="py-1.5 pr-3 font-normal">By region</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((t) => {
                  const ok = t.status === "designed";
                  const checked = picked.includes(t.id);
                  const inReport = current.includes(t.id);
                  return (
                    <tr key={t.id} className={`border-b border-line last:border-0 ${ok ? "" : "text-muted"} ${checked ? "bg-accent-soft" : ""}`}>
                      <td className="py-1.5 pl-3">
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={!ok || (!checked && picked.length >= MAX_PICK)}
                          onChange={() => toggle(t.id)}
                          aria-label={`Pick ${t.gene} ${t.mutation}`}
                        />
                      </td>
                      <td className="py-1.5 pr-3">
                        <span className={ok ? "text-ink" : ""}>
                          {t.gene} {t.mutation}
                        </span>
                        {inReport && <span className="ml-1.5 rounded-full bg-accent-soft px-1.5 py-0.5 text-[10px] text-accent">in report</span>}
                        {!ok && (
                          <span className="ml-1.5 text-warn" title={t.reason}>
                            no design
                          </span>
                        )}
                      </td>
                      <td className="max-w-[10rem] truncate py-1.5 pr-3" title={t.drug}>{t.drug}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{t.resistant_isolates.toLocaleString()}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{ok ? t.overall : "–"}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{ok ? `${t.exact_matches}/${t.isolates}` : "–"}</td>
                      {multiRegion && (
                        <td className="py-1.5 pr-3 tabular-nums">
                          {ok && t.by_region
                            ? Object.entries(t.by_region)
                                .map(([r, [n, total]]) => `${r} ${n}/${total}`)
                                .join(" · ")
                            : "–"}
                        </td>
                      )}
                    </tr>
                  );
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={multiRegion ? 7 : 6} className="py-4 text-center text-muted">
                      No targets match.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <button
              type="button"
              disabled={busy || picked.length === 0}
              onClick={() => onDesign(picked)}
              className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-surface transition-opacity disabled:opacity-40"
            >
              {busy ? "Designing…" : `Design selected (${picked.length})`}
            </button>
            {picked.length > 0 && (
              <button type="button" onClick={() => setPicked([])} className="text-xs text-muted hover:text-ink">
                Clear
              </button>
            )}
            <span className="text-xs text-muted">Designing runs the full design again on the current isolates.</span>
          </div>
        </>
      )}
    </section>
  );
}
