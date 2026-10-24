"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Report, ToolStep } from "@/lib/types";
import AgentPanel from "./AgentPanel";
import Onboarding from "./Onboarding";
import ReportSwitcher from "./ReportSwitcher";
import ReportView from "./ReportView";
import TargetLibrary from "./TargetLibrary";
import { loadLibrary } from "@/lib/library";
import { MAX_REPORTS_PER_SESSION, modelHistory, reportLabel, titleFrom, uid, type ChatMessage } from "@/lib/sessions";
import { useSessions } from "@/lib/useSessions";

const library = loadLibrary();
// Same host as the page, so localhost, 127.0.0.1 and a LAN address all reach the API on this machine.
const apiBase = () => process.env.NEXT_PUBLIC_API_URL ?? `http://${window.location.hostname}:8000`;

type ChatEvent =
  | { type: "step"; step: ToolStep }
  | { type: "report"; report: Report }
  | { type: "text"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

const failure = (what: string, err: unknown) => {
  const why = err instanceof Error ? err.message : String(err);
  return why.startsWith("LIMIT:") ? why.slice(6) : `${what} failed (${why}). Is the backend running? API at ${apiBase()}`;
};

export default function App({ report: initial }: { report: Report }) {
  const { sessions, activeId, active, storageOk, update, select, create, remove, rename } = useSessions();
  const [runningSid, setRunningSid] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState(initial.candidates[0]?.id ?? "");
  const [tab, setTab] = useState<"results" | "library">("results");
  const [collapsed, setCollapsed] = useState(false);
  const [unread, setUnread] = useState(false);
  const [ready, setReady] = useState(false); // motion starts after the stored layout is applied, so a load does not animate
  const [welcome, setWelcome] = useState<"hidden" | "first" | "help">("hidden");
  const wasRunning = useRef<string | null>(null);
  const lastWelcome = useRef<"first" | "help">("help"); // the text stays put while the card animates shut

  // Preferences kept in this browser: the assistant starts open on a wide screen and minimized on a phone, and the
  // welcome card shows until it is closed once.
  useEffect(() => {
    let stored: string | null = null;
    let seen: string | null = null;
    try {
      stored = localStorage.getItem("chatgp-tb:assistant");
      seen = localStorage.getItem("chatgp-tb:welcome");
    } catch {
      /* storage blocked: use the defaults every time */
    }
    setCollapsed(stored ? stored === "collapsed" : !window.matchMedia("(min-width: 1024px)").matches);
    setWelcome(seen ? "hidden" : "first");
    const t = setTimeout(() => setReady(true), 100);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (welcome !== "hidden") lastWelcome.current = welcome;
  }, [welcome]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((c) => {
      try {
        localStorage.setItem("chatgp-tb:assistant", c ? "open" : "collapsed");
      } catch {
        /* blocked */
      }
      return !c;
    });
    setUnread(false);
  }, []);

  const closeWelcome = useCallback(() => {
    setWelcome("hidden");
    try {
      localStorage.setItem("chatgp-tb:welcome", "seen");
    } catch {
      /* blocked: it will show again next visit */
    }
  }, []);

  // A chat with no report yet shows an empty state; `initial` still supplies the dataset numbers for the header and welcome card.
  const current = active ? (active.reports.find((r) => r.id === active.activeReportId) ?? (active.activeReportId === null ? active.reports[active.reports.length - 1] : undefined))?.report : undefined;
  const shown = current ?? initial;
  useEffect(() => setSelectedId(shown.candidates[0]?.id ?? ""), [shown]);

  // A reply that finishes while the assistant is minimized leaves a dot on its button.
  useEffect(() => {
    if (wasRunning.current !== null && runningSid === null && collapsed) setUnread(true);
    wasRunning.current = runningSid;
  }, [runningSid, collapsed]);

  const patch = useCallback(
    (sid: string, msgId: string, fn: (m: ChatMessage) => ChatMessage) =>
      update(sid, (s) => ({ ...s, messages: s.messages.map((m) => (m.id === msgId ? fn(m) : m)) })),
    [update],
  );

  // Save a report in the chat, make it the one shown, and link the assistant's turn to it.
  const addReport = useCallback(
    (sid: string, msgId: string, report: Report) => {
      const rid = uid();
      update(sid, (s) => {
        const reports = [...s.reports, { id: rid, report, at: Date.now(), label: reportLabel(report) }].slice(-MAX_REPORTS_PER_SESSION);
        const kept = new Set(reports.map((r) => r.id));
        return {
          ...s,
          reports,
          activeReportId: rid,
          messages: s.messages.map((m) => ({ ...m, reportId: m.id === msgId ? rid : m.reportId && kept.has(m.reportId) ? m.reportId : undefined })),
        };
      });
    },
    [update],
  );

  // Add the user's turn and an assistant turn that fills in as the work happens. Returns the assistant message id.
  const startTurn = useCallback(
    (sid: string, text: string) => {
      const asst: ChatMessage = { id: uid(), role: "assistant", text: "", steps: [], pending: true, at: Date.now() };
      update(sid, (s) => ({
        ...s,
        title: s.messages.length === 0 ? titleFrom(text) : s.title,
        messages: [...s.messages, { id: uid(), role: "user", text, at: Date.now() }, asst],
      }));
      return asst.id;
    },
    [update],
  );

  const send = useCallback(
    async (text: string) => {
      if (!active || runningSid) return;
      const sid = active.id;
      const history = modelHistory(active.messages);
      const msgId = startTurn(sid, text);
      setRunningSid(sid);
      try {
        const res = await fetch(`${apiBase()}/api/chat`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: text, history }),
        });
        if (res.status === 429) throw new Error("LIMIT:The chat limit was reached. Please try again later.");
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let cut;
          while ((cut = buf.indexOf("\n\n")) >= 0) {
            const line = buf.slice(0, cut).trim();
            buf = buf.slice(cut + 2);
            if (!line.startsWith("data: ")) continue;
            const ev = JSON.parse(line.slice(6)) as ChatEvent;
            if (ev.type === "step") {
              patch(sid, msgId, (m) => {
                const steps = m.steps ?? [];
                return { ...m, steps: steps.some((s) => s.id === ev.step.id) ? steps.map((s) => (s.id === ev.step.id ? ev.step : s)) : [...steps, ev.step] };
              });
            } else if (ev.type === "report") addReport(sid, msgId, ev.report);
            else if (ev.type === "text") patch(sid, msgId, (m) => ({ ...m, text: ev.text }));
            else if (ev.type === "error") patch(sid, msgId, (m) => ({ ...m, error: ev.message }));
          }
        }
      } catch (err) {
        patch(sid, msgId, (m) => ({ ...m, error: failure("Chat", err) }));
      } finally {
        patch(sid, msgId, (m) => ({ ...m, pending: false }));
        setRunningSid(null);
      }
    },
    [active, runningSid, startTurn, patch, addReport],
  );

  // Design the targets picked in the library panel: a turn in the chat, with the same report, and no model call.
  const designFromLibrary = useCallback(
    async (ids: string[], region?: string) => {
      if (!active || runningSid) return;
      const sid = active.id;
      const names = ids.map((id) => library.targets.find((t) => t.id === id)).map((t, i) => (t ? `${t.gene} ${t.mutation}` : ids[i]));
      const msgId = startTurn(sid, `Design from the target library${region ? ` (${region} only)` : ""}: ${names.join(", ")}`);
      setRunningSid(sid);
      try {
        const res = await fetch(`${apiBase()}/api/design`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ targets: ids, regions: region ? [region] : [] }),
        });
        if (res.status === 429) throw new Error("LIMIT:The design limit was reached. Please try again later.");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const next = (await res.json()) as Report;
        patch(sid, msgId, (m) => ({ ...m, text: next.summary, steps: next.steps }));
        addReport(sid, msgId, next);
        setTab("results");
        setTimeout(() => document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
      } catch (err) {
        patch(sid, msgId, (m) => ({ ...m, error: failure("Design", err) }));
      } finally {
        patch(sid, msgId, (m) => ({ ...m, pending: false }));
        setRunningSid(null);
      }
    },
    [active, runningSid, startTurn, patch, addReport],
  );

  const showReport = useCallback(
    (id: string | null) => {
      if (!active) return;
      update(active.id, (s) => ({ ...s, activeReportId: id }));
      setTab("results");
      setTimeout(() => document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    },
    [active, update],
  );

  const designed = library.targets.filter((t) => t.status === "designed").length;
  const tabClass = (on: boolean) =>
    `-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm ${on ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`;
  const count = "rounded-full bg-accent-soft px-1.5 py-0.5 text-[11px] tabular-nums text-accent";
  const example = "Design qPCR assays for the main rifampicin, isoniazid and fluoroquinolone resistance mutations.";

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-4 px-5 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-sm font-semibold text-surface">GP</div>
            <div>
              <h1 className="text-base font-semibold leading-tight">ChatGP-TB</h1>
              <p className="text-xs text-muted">Genomics-guided primer and probe design for drug-resistant tuberculosis</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setTab("results");
                setWelcome((w) => (w === "hidden" ? "help" : "hidden"));
              }}
              aria-expanded={welcome !== "hidden"}
              className="shrink-0 whitespace-nowrap rounded-full border border-line px-3 py-1 text-xs hover:border-accent"
            >
              How it works
            </button>
          </div>
        </div>
      </header>

      {shown.mock && (
        <div role="status" className="border-b border-line bg-warn-soft px-5 py-2 text-center text-xs text-warn">
          Demo data: sequences, scores and coverage are placeholders to show the interface, not results.
        </div>
      )}

      <main
        className={`mx-auto grid w-full max-w-[1400px] flex-1 content-start gap-5 px-5 py-5 ${
          collapsed ? "lg:grid-cols-[3.5rem_minmax(0,1fr)]" : "lg:grid-cols-[380px_minmax(0,1fr)]"
        } ${ready ? "transition-[grid-template-columns] duration-300 ease-out motion-reduce:transition-none" : ""}`}
      >
        <div className={`${collapsed ? "h-14" : "h-[34rem]"} min-w-0 ${ready ? "transition-[height] duration-300 ease-out motion-reduce:transition-none" : ""} lg:sticky lg:top-5 lg:h-[calc(100vh-6.5rem)]`}>
          <AgentPanel
            session={active}
            sessions={sessions}
            running={runningSid !== null && runningSid === activeId}
            busyElsewhere={runningSid !== null && runningSid !== activeId}
            storageOk={storageOk}
            collapsed={collapsed}
            unread={unread}
            onToggleCollapsed={toggleCollapsed}
            onSend={send}
            onNew={create}
            onSelect={select}
            onRename={rename}
            onDelete={remove}
            onShowReport={showReport}
          />
        </div>

        <div className="min-w-0 space-y-4">
          <div role="tablist" aria-label="View" className="flex gap-1 border-b border-line">
            <button role="tab" id="tab-results" aria-selected={tab === "results"} aria-controls="panel-results" onClick={() => setTab("results")} className={tabClass(tab === "results")}>
              Results {current && <span className={count}>{current.candidates.length}</span>}
            </button>
            <button role="tab" id="tab-library" aria-selected={tab === "library"} aria-controls="panel-library" onClick={() => setTab("library")} className={tabClass(tab === "library")}>
              Target library <span className={count}>{designed}</span>
            </button>
          </div>

          {tab === "library" ? (
            <div role="tabpanel" id="panel-library" aria-labelledby="tab-library">
              <TargetLibrary library={library} current={(current?.candidates ?? []).map((c) => c.id)} busy={runningSid !== null} onDesign={designFromLibrary} />
            </div>
          ) : (
            <div role="tabpanel" id="panel-results" aria-labelledby="tab-results" className="flex flex-col">
              {/* Always mounted so it can animate shut; inert keeps it out of reach while closed. */}
              <div
                inert={welcome === "hidden"}
                aria-hidden={welcome === "hidden"}
                className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${
                  welcome === "hidden" ? "grid-rows-[0fr] opacity-0" : "grid-rows-[1fr] opacity-100"
                }`}
              >
                <div className="min-h-0 overflow-hidden">
                  <div className="pb-5">
                    <Onboarding
                      mode={welcome === "hidden" ? lastWelcome.current : welcome}
                      isolates={shown.dataset.isolates}
                      regions={Object.keys(shown.dataset.regions ?? {})}
                      designed={designed}
                      onTry={() => {
                        if (welcome === "first") closeWelcome();
                        else setWelcome("hidden");
                        if (collapsed) toggleCollapsed();
                        void send(example);
                      }}
                      onClose={welcome === "first" ? closeWelcome : () => setWelcome("hidden")}
                    />
                  </div>
                </div>
              </div>
              {active && (
                <div className="mb-5">
                  <ReportSwitcher session={active} onShow={showReport} />
                </div>
              )}
              <div id="report" className="scroll-mt-5">
                {current ? (
                  <ReportView report={current} selectedId={selectedId} onSelect={setSelectedId} />
                ) : (
                  <div className="rounded-2xl border border-dashed border-line bg-surface px-5 py-10 text-center">
                    <h2 className="text-sm font-medium">No results in this chat yet</h2>
                    <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-muted">
                      Ask the assistant which resistance mutations occur in a region, or pick variants in the Target library. Results appear here.
                    </p>
                    <div className="mt-4 flex flex-wrap justify-center gap-3">
                      <button
                        type="button"
                        onClick={() => {
                          if (collapsed) toggleCollapsed();
                          void send(example);
                        }}
                        disabled={runningSid !== null}
                        className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-surface disabled:opacity-50"
                      >
                        Try an example
                      </button>
                      <button type="button" onClick={() => setTab("library")} className="rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent">
                        Open the Target library
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
