"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Report, ToolStep } from "@/lib/types";
import AgentPanel from "./AgentPanel";
import ReportView from "./ReportView";
import TargetLibrary from "./TargetLibrary";
import { loadLibrary } from "@/lib/library";

// Same host as the page, so localhost, 127.0.0.1 and a LAN address all reach the API on this machine.
const library = loadLibrary();
const apiBase = () => process.env.NEXT_PUBLIC_API_URL ?? `http://${window.location.hostname}:8000`;

type Turn = { role: "user" | "model"; text: string };

type ChatEvent =
  | { type: "step"; step: ToolStep }
  | { type: "report"; report: Report }
  | { type: "text"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

export default function App({ report: initial }: { report: Report }) {
  const [report, setReport] = useState(initial);
  const [request, setRequest] = useState(initial.request);
  const [summary, setSummary] = useState(initial.summary);
  const [steps, setSteps] = useState<ToolStep[]>(initial.steps);
  const [running, setRunning] = useState(false);
  const [libBusy, setLibBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(initial.candidates[0].id);
  const history = useRef<Turn[]>([]);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  useEffect(() => clearTimers, []);

  // Used only while the report is demo data and the backend is not running.
  const replay = useCallback(() => {
    clearTimers();
    setRunning(true);
    setSummary("");
    setSteps(initial.steps.map((s, i) => ({ ...s, status: i === 0 ? "running" : "pending" })));
    initial.steps.forEach((_, i) => {
      timers.current.push(
        setTimeout(() => {
          setSteps((prev) => prev.map((s, j) => (j === i ? { ...s, status: "done" } : j === i + 1 ? { ...s, status: "running" } : s)));
          if (i === initial.steps.length - 1) {
            setRunning(false);
            setSummary(initial.summary);
          }
        }, 700 * (i + 1)),
      );
    });
  }, [initial]);

  const handle = useCallback((ev: ChatEvent) => {
    if (ev.type === "step") {
      setSteps((prev) => (prev.some((s) => s.id === ev.step.id) ? prev.map((s) => (s.id === ev.step.id ? ev.step : s)) : [...prev, ev.step]));
    } else if (ev.type === "report") {
      setReport(ev.report);
      setSelectedId(ev.report.candidates[0]?.id ?? "");
    } else if (ev.type === "text") {
      setSummary(ev.text);
      history.current.push({ role: "model", text: ev.text });
    } else if (ev.type === "error") {
      setError(ev.message);
    }
  }, []);

  const send = useCallback(
    async (text: string) => {
      clearTimers();
      setRequest(text);
      setSteps([]);
      setSummary("");
      setError("");
      setRunning(true);
      const prior = history.current.slice();
      history.current.push({ role: "user", text });
      try {
        const res = await fetch(`${apiBase()}/api/chat`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: text, history: prior }),
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
            if (line.startsWith("data: ")) handle(JSON.parse(line.slice(6)) as ChatEvent);
          }
        }
      } catch (err) {
        if (initial.mock) {
          replay();
          return;
        }
        const why = err instanceof Error ? err.message : String(err);
        if (why.startsWith("LIMIT:")) {
          setError(why.slice(6));
          return;
        }
        setError(`Chat failed (${why}). Is the backend running? uvicorn genohack.api:app --port 8000, API at ${apiBase()}`);
      } finally {
        setRunning(false);
      }
    },
    [handle, initial.mock, replay],
  );

  // Design the targets picked in the library panel: same report as a chat request, with no model call.
  const designFromLibrary = useCallback(
    async (ids: string[]) => {
      clearTimers();
      setError("");
      setLibBusy(true);
      try {
        const res = await fetch(`${apiBase()}/api/design`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ targets: ids }),
        });
        if (res.status === 429) throw new Error("LIMIT:The design limit was reached. Please try again later.");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const next = (await res.json()) as Report;
        setReport(next);
        setRequest(next.request);
        setSummary(next.summary);
        setSteps(next.steps);
        setSelectedId(next.candidates[0]?.id ?? "");
        document.getElementById("report")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (err) {
        const why = err instanceof Error ? err.message : String(err);
        setError(why.startsWith("LIMIT:") ? why.slice(6) : `Design failed (${why}). Is the backend running? API at ${apiBase()}`);
      } finally {
        setLibBusy(false);
      }
    },
    [],
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
          <span className="hidden rounded-full border border-line px-3 py-1 text-xs text-muted sm:inline">{report.dataset.name}</span>
        </div>
      </header>

      {report.mock && (
        <div role="status" className="border-b border-line bg-warn-soft px-5 py-2 text-center text-xs text-warn">
          Demo data: sequences, scores and coverage are placeholders to show the interface, not results.
        </div>
      )}

      <main className="mx-auto grid w-full max-w-[1400px] flex-1 gap-5 px-5 py-5 lg:grid-cols-[380px_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-5 lg:h-[calc(100vh-6.5rem)]">
          <AgentPanel request={request} steps={steps} summary={summary} error={error} running={running} onSend={send} />
        </div>
        <div className="min-w-0 space-y-5">
          <TargetLibrary library={library} current={report.candidates.map((c) => c.id)} busy={libBusy || running} onDesign={designFromLibrary} />
          <div id="report" className="scroll-mt-5">
            <ReportView report={report} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </div>
      </main>
    </div>
  );
}
