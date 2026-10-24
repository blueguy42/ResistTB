"use client";

import { useCallback, useEffect, useState } from "react";
import type { Report, ToolStep } from "@/lib/types";
import AgentPanel from "./AgentPanel";
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

  const shown = active?.reports.find((r) => r.id === active.activeReportId)?.report ?? initial;
  useEffect(() => setSelectedId(shown.candidates[0]?.id ?? ""), [shown]);

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
    async (ids: string[]) => {
      if (!active || runningSid) return;
      const sid = active.id;
      const names = ids.map((id) => library.targets.find((t) => t.id === id)).map((t, i) => (t ? `${t.gene} ${t.mutation}` : ids[i]));
      const msgId = startTurn(sid, `Design from the target library: ${names.join(", ")}`);
      setRunningSid(sid);
      try {
        const res = await fetch(`${apiBase()}/api/design`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ targets: ids }),
        });
        if (res.status === 429) throw new Error("LIMIT:The design limit was reached. Please try again later.");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const next = (await res.json()) as Report;
        patch(sid, msgId, (m) => ({ ...m, text: next.summary, steps: next.steps }));
        addReport(sid, msgId, next);
        document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
      document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" });
    },
    [active, update],
  );

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
          <span className="hidden rounded-full border border-line px-3 py-1 text-xs text-muted sm:inline">{shown.dataset.name}</span>
        </div>
      </header>

      {shown.mock && (
        <div role="status" className="border-b border-line bg-warn-soft px-5 py-2 text-center text-xs text-warn">
          Demo data: sequences, scores and coverage are placeholders to show the interface, not results.
        </div>
      )}

      <main className="mx-auto grid w-full max-w-[1400px] flex-1 gap-5 px-5 py-5 lg:grid-cols-[380px_minmax(0,1fr)]">
        <div className="h-[34rem] lg:sticky lg:top-5 lg:h-[calc(100vh-6.5rem)]">
          <AgentPanel
            session={active}
            sessions={sessions}
            running={runningSid !== null && runningSid === activeId}
            busyElsewhere={runningSid !== null && runningSid !== activeId}
            storageOk={storageOk}
            onSend={send}
            onNew={create}
            onSelect={select}
            onRename={rename}
            onDelete={remove}
            onShowReport={showReport}
          />
        </div>
        <div className="min-w-0 space-y-5">
          <TargetLibrary library={library} current={shown.candidates.map((c) => c.id)} busy={runningSid !== null} onDesign={designFromLibrary} />
          {active && <ReportSwitcher session={active} onShow={showReport} />}
          <div id="report" className="scroll-mt-5">
            <ReportView report={shown} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </div>
      </main>
    </div>
  );
}
