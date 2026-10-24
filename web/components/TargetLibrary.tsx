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
  const [drug, setDrug] = useState("All drugs");
  const [query, setQuery] = useState("");
  const [showNoDesign, setShowNoDesign] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  const [region, setRegion] = useState("All regions");
  const [view, setView] = useState<"mutation" | "oligo">("mutation");

  const drugs = useMemo(() => {
    const count = new Map<string, number>();
    for (const t of library.targets) for (const d of drugsOf(t)) count.set(d, (count.get(d) ?? 0) + 1);
    return [...count.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [library]);

  const designed = library.targets.filter((t) => t.status === "designed").length;
  const regionNames = Object.keys(library.regions);
  const multiRegion = regionNames.length > 1;

  // Carriers of the variant in the chosen region (all regions together when none is chosen).
  const carriers = (t: LibraryTarget) => t.mutation_by_region?.[region === "All regions" ? "overall" : region]?.[0] ?? 0;

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const inRegion = region !== "All regions";
    return library.targets
      .filter((t) => (showNoDesign || t.status === "designed") && (drug === "All drugs" || drugsOf(t).includes(drug)))
      .filter((t) => !q || `${t.gene} ${t.mutation} ${t.id}`.toLowerCase().includes(q))
      .filter((t) => !inRegion || (t.mutation_by_region?.[region]?.[0] ?? 0) > 0)
      .sort((a, b) => (inRegion ? carriers(b) - carriers(a) : b.resistant_isolates - a.resistant_isolates));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [library, drug, query, showNoDesign, region]);

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < MAX_PICK ? [...p, id] : p));

  return (
    <section className="rounded-2xl border border-line bg-surface px-5 py-4" aria-label="Target library">
      <h3 className="text-sm font-medium">Target library</h3>
      <p className="mt-1 text-xs text-muted">
        {designed} WHO resistance variants have a design on {library.isolates} isolates
        {multiRegion ? ` from ${regionNames.length} regions` : ""}. Pick up to {MAX_PICK} to design them together.
      </p>

      <>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {multiRegion && (
              <>
                <label className="flex items-center gap-1.5">
                  <span className="text-muted">Region</span>
                  <select value={region} onChange={(e) => setRegion(e.target.value)} className="rounded-md border border-line bg-bg px-2 py-1">
                    <option>All regions</option>
                    {regionNames.map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </label>
                <div role="group" aria-label="Region columns show" className="flex overflow-hidden rounded-md border border-line">
                  {([["mutation", "Mutation carriers"], ["oligo", "Oligo matches"]] as const).map(([m, label]) => (
                    <button key={m} type="button" aria-pressed={view === m} onClick={() => setView(m)}
                      className={`px-2 py-1 ${view === m ? "bg-accent-soft text-ink" : "text-muted hover:text-ink"}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </>
            )}
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

          <div className="mt-3 max-h-[60vh] overflow-auto rounded-xl border border-line">
            <table className={`w-full text-left text-xs ${multiRegion ? "min-w-[760px]" : "min-w-[560px]"}`}>
              <thead className="sticky top-0 bg-surface text-muted">
                <tr className="border-b border-line">
                  <th className="w-8 py-1.5 pl-3 font-normal"><span className="sr-only">Pick</span></th>
                  <th className="py-1.5 pr-3 font-normal">Variant</th>
                  <th className="py-1.5 pr-3 font-normal">Drug</th>
                  <th className="py-1.5 pr-3 text-right font-normal" title="Resistant isolates the WHO catalogue lists with this variant">WHO isolates</th>
                  <th className="py-1.5 pr-3 text-right font-normal">Score</th>
                  <th className="py-1.5 pr-3 text-right font-normal">Exact match</th>
                  {multiRegion &&
                    regionNames.map((r) => (
                      <th key={r} className="py-1.5 pr-3 text-right font-normal" title={view === "mutation" ? `Isolates from ${r} carrying this variant, of those with a called base` : `Isolates from ${r} matching every oligo exactly`}>
                        {r}
                      </th>
                    ))}
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
                      {multiRegion &&
                        regionNames.map((r) => (
                          <td key={r} className="py-1.5 pr-3 text-right tabular-nums">
                            {view === "mutation"
                              ? t.mutation_by_region?.[r]
                                ? `${t.mutation_by_region[r][0]}/${t.mutation_by_region[r][1]}`
                                : "–"
                              : ok && t.by_region?.[r]
                                ? `${t.by_region[r][0]}/${t.by_region[r][1]}`
                                : "–"}
                          </td>
                        ))}
                    </tr>
                  );
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={6 + (multiRegion ? regionNames.length : 0)} className="py-4 text-center text-muted">
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
    </section>
  );
}
