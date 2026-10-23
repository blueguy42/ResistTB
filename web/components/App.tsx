"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Report, ToolStep } from "@/lib/types";
import AgentPanel from "./AgentPanel";
import ReportView from "./ReportView";

// While the backend is not connected, a request replays the report's own tool steps one by one,
// so the interface behaves like a streaming agent. Swap `replay` for a fetch to the API later.
export default function App({ report }: { report: Report }) {
  const [request, setRequest] = useState(report.request);
  const [steps, setSteps] = useState<ToolStep[]>(report.steps);
  const [running, setRunning] = useState(false);
  const [selectedId, setSelectedId] = useState(report.candidates[0].id);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  useEffect(() => clearTimers, []);

  const replay = useCallback(
    (text: string) => {
      clearTimers();
      setRequest(text);
      setRunning(true);
      setSteps(report.steps.map((s, i) => ({ ...s, status: i === 0 ? "running" : "pending" })));
      report.steps.forEach((_, i) => {
        timers.current.push(
          setTimeout(() => {
            setSteps((prev) =>
              prev.map((s, j) => (j === i ? { ...s, status: "done" } : j === i + 1 ? { ...s, status: "running" } : s)),
            );
            if (i === report.steps.length - 1) setRunning(false);
          }, 700 * (i + 1)),
        );
      });
    },
    [report.steps],
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
          <AgentPanel report={report} request={request} steps={steps} running={running} onSend={replay} />
        </div>
        <ReportView report={report} selectedId={selectedId} onSelect={setSelectedId} />
      </main>
    </div>
  );
}
