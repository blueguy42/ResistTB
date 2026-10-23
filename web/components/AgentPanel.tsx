"use client";

import { useState } from "react";
import type { Report, ToolStep } from "@/lib/types";

function StepIcon({ status }: { status: ToolStep["status"] }) {
  if (status === "done")
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent text-surface" aria-label="done">
        <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M2.5 6.5l2.2 2.2L9.5 3.8" />
        </svg>
      </span>
    );
  if (status === "running")
    return <span className="h-5 w-5 animate-pulse rounded-full border-2 border-accent" aria-label="running" />;
  return <span className="h-5 w-5 rounded-full border-2 border-line" aria-label="pending" />;
}

export default function AgentPanel({
  report,
  request,
  steps,
  running,
  onSend,
}: {
  report: Report;
  request: string;
  steps: ToolStep[];
  running: boolean;
  onSend: (text: string) => void;
}) {
  const [draft, setDraft] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || running) return;
    setDraft("");
    onSend(text);
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-line bg-surface">
      <div className="border-b border-line px-5 py-3.5">
        <h2 className="text-sm font-medium">Assistant</h2>
        <p className="text-xs text-muted">Plans the design, calls the tools, explains the result.</p>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
        <div className="ml-6 rounded-2xl rounded-tr-md bg-accent-soft px-4 py-2.5 text-sm">{request}</div>

        <ol className="space-y-3" aria-label="Tool steps">
          {steps.map((s) => (
            <li key={s.id} className="flex gap-3">
              <StepIcon status={s.status} />
              <div className="min-w-0 flex-1">
                <div className="text-sm leading-5">{s.label}</div>
                <div className="flex flex-wrap items-center gap-x-2 text-xs text-muted">
                  <code className="font-mono">{s.tool}</code>
                  {s.detail && <span>· {s.detail}</span>}
                  {s.status === "done" && s.seconds !== undefined && <span>· {s.seconds.toFixed(1)} s</span>}
                </div>
              </div>
            </li>
          ))}
        </ol>

        {!running && steps.every((s) => s.status === "done") && (
          <div className="mr-6 rounded-2xl rounded-tl-md border border-line px-4 py-3 text-sm leading-6">{report.summary}</div>
        )}
      </div>

      <form onSubmit={submit} className="border-t border-line p-3">
        <div className="flex items-end gap-2 rounded-xl border border-line bg-bg px-3 py-2 focus-within:border-accent">
          <label htmlFor="ask" className="sr-only">
            Ask for an assay design
          </label>
          <textarea
            id="ask"
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) submit(e);
            }}
            placeholder="Ask for an assay, for example: add gyrA"
            className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={running || !draft.trim()}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-surface transition-opacity disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
