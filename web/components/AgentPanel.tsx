"use client";

import { useEffect, useRef, useState } from "react";
import type { ToolStep } from "@/lib/types";
import { ago, type ChatMessage, type Session } from "@/lib/sessions";

const EXAMPLES = [
  "Design assays for ethambutol resistance",
  "Patients in Bandung treated with rifampicin did not improve. What primers and probes should the assay include?",
  "Which drugs can you design for?",
];

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function StepIcon({ status }: { status: ToolStep["status"] }) {
  if (status === "done")
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-surface" aria-label="done">
        <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M2.5 6.5l2.2 2.2L9.5 3.8" />
        </svg>
      </span>
    );
  if (status === "running") return <span className="h-5 w-5 shrink-0 animate-pulse rounded-full border-2 border-accent" aria-label="running" />;
  return <span className="h-5 w-5 shrink-0 rounded-full border-2 border-line" aria-label="pending" />;
}

function Steps({ steps, pending }: { steps: ToolStep[]; pending: boolean }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;
  const total = steps.reduce((t, s) => t + (s.seconds ?? 0), 0);
  // While the reply is being written the steps show live; afterwards they fold into one line.
  if (!pending && !open)
    return (
      <button type="button" onClick={() => setOpen(true)} className="flex items-center gap-2 text-xs text-muted hover:text-ink" aria-expanded={false}>
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-accent text-surface">
          <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M2.5 6.5l2.2 2.2L9.5 3.8" />
          </svg>
        </span>
        {steps.length} steps · {total.toFixed(1)} s
        <span aria-hidden>▸</span>
      </button>
    );
  return (
    <div>
      {!pending && (
        <button type="button" onClick={() => setOpen(false)} className="mb-1.5 text-xs text-muted hover:text-ink" aria-expanded>
          Hide steps ▾
        </button>
      )}
      <ol className="space-y-2.5" aria-label="Tool steps">
        {steps.map((s) => (
          <li key={s.id} className="flex gap-3">
            <StepIcon status={s.status} />
            <div className="min-w-0 flex-1">
              <div className="text-sm leading-5">{s.label}</div>
              <div className="flex flex-wrap items-center gap-x-2 text-xs text-muted">
                <code className="font-mono">{s.tool}</code>
                {s.detail && <span className="break-all">· {s.detail}</span>}
                {s.status === "done" && s.seconds !== undefined && <span>· {s.seconds.toFixed(1)} s</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Message({ m, activeReportId, onShowReport }: { m: ChatMessage; activeReportId: string | null; onShowReport: (id: string) => void }) {
  if (m.role === "user") return <div className="ml-6 whitespace-pre-wrap rounded-2xl rounded-tr-md bg-accent-soft px-4 py-2.5 text-sm">{m.text}</div>;
  return (
    <div className="space-y-3">
      <Steps steps={m.steps ?? []} pending={!!m.pending} />
      {m.pending && !m.text && (m.steps?.length ?? 0) === 0 && <div className="text-xs text-muted">Working on it…</div>}
      {m.text && <div className="mr-6 whitespace-pre-wrap rounded-2xl rounded-tl-md border border-line px-4 py-3 text-sm leading-6">{m.text}</div>}
      {m.error && (
        <div role="alert" className="rounded-xl border border-line bg-warn-soft px-4 py-3 text-sm text-warn">
          {m.error}
        </div>
      )}
      {m.reportId &&
        (m.reportId === activeReportId ? (
          <div className="text-xs text-accent">Showing this report in the results</div>
        ) : (
          <button type="button" onClick={() => onShowReport(m.reportId!)} className="rounded-lg border border-line px-2.5 py-1 text-xs text-ink hover:border-accent">
            Show this report
          </button>
        ))}
    </div>
  );
}

function ChatList({
  sessions,
  activeId,
  onSelect,
  onNew,
  onRename,
  onDelete,
}: {
  sessions: Session[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const [editing, setEditing] = useState("");
  const [name, setName] = useState("");
  const finish = () => {
    if (editing) onRename(editing, name);
    setEditing("");
  };
  return (
    <div className="space-y-3">
      <button type="button" onClick={onNew} className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-medium text-surface">
        New chat
      </button>
      <ul className="space-y-1.5" aria-label="Saved chats">
        {sessions.map((s) => (
          <li key={s.id} className={`group rounded-xl border px-3 py-2 ${s.id === activeId ? "border-accent bg-accent-soft" : "border-line hover:border-accent"}`}>
            {editing === s.id ? (
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={finish}
                onKeyDown={(e) => {
                  if (e.key === "Enter") finish();
                  if (e.key === "Escape") setEditing("");
                }}
                aria-label="Chat name"
                className="w-full rounded-md border border-line bg-bg px-2 py-1 text-sm outline-none focus:border-accent"
              />
            ) : (
              <div className="flex items-start gap-2">
                <button type="button" onClick={() => onSelect(s.id)} className="min-w-0 flex-1 text-left">
                  <div className="truncate text-sm">{s.title}</div>
                  <div className="text-xs text-muted">
                    {plural(s.messages.filter((m) => m.role === "user").length, "message")} · {plural(s.reports.length, "report")} · {ago(s.updatedAt)}
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditing(s.id);
                    setName(s.title);
                  }}
                  aria-label={`Rename ${s.title}`}
                  className="rounded p-1 text-xs text-muted hover:text-ink"
                >
                  Rename
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(`Delete "${s.title}" and its ${s.reports.length} saved reports?`)) onDelete(s.id);
                  }}
                  aria-label={`Delete ${s.title}`}
                  className="rounded p-1 text-xs text-muted hover:text-bad"
                >
                  Delete
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AgentPanel({
  session,
  sessions,
  running,
  busyElsewhere,
  storageOk,
  onSend,
  onNew,
  onSelect,
  onRename,
  onDelete,
  onShowReport,
}: {
  session: Session | null;
  sessions: Session[];
  running: boolean;
  busyElsewhere: boolean;
  storageOk: boolean;
  onSend: (text: string) => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onShowReport: (id: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const [view, setView] = useState<"chat" | "list">("chat");
  const scroller = useRef<HTMLDivElement>(null);
  const messages = session?.messages ?? [];
  const last = messages[messages.length - 1];

  // Keep the newest message in view while a reply streams in.
  useEffect(() => {
    if (view === "chat") scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages.length, last?.text, last?.steps?.length, view, session?.id]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || running || busyElsewhere) return;
    setDraft("");
    setView("chat");
    onSend(text);
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-line bg-surface">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-sm font-medium">{view === "list" ? "Saved chats" : session?.title ?? "Assistant"}</h2>
          <p className="truncate text-xs text-muted">{view === "list" ? `${sessions.length} in this browser` : "Plans the design, calls the tools, explains the result."}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            onNew();
            setView("chat");
          }}
          disabled={running}
          className="rounded-lg border border-line px-2.5 py-1 text-xs hover:border-accent disabled:opacity-40"
        >
          New chat
        </button>
        <button
          type="button"
          onClick={() => setView(view === "list" ? "chat" : "list")}
          aria-pressed={view === "list"}
          className={`rounded-lg border px-2.5 py-1 text-xs ${view === "list" ? "border-accent bg-accent-soft" : "border-line hover:border-accent"}`}
        >
          Chats ({sessions.length})
        </button>
      </div>

      <div ref={scroller} className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
        {view === "list" ? (
          <ChatList
            sessions={sessions}
            activeId={session?.id ?? ""}
            onSelect={(id) => {
              onSelect(id);
              setView("chat");
            }}
            onNew={() => {
              onNew();
              setView("chat");
            }}
            onRename={onRename}
            onDelete={onDelete}
          />
        ) : messages.length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-muted">Ask for an assay in your own words. Try one of these:</p>
            {EXAMPLES.map((q) => (
              <button
                key={q}
                type="button"
                disabled={running || busyElsewhere}
                onClick={() => onSend(q)}
                className="block w-full rounded-xl border border-line px-3 py-2 text-left text-sm hover:border-accent disabled:opacity-40"
              >
                {q}
              </button>
            ))}
          </div>
        ) : (
          messages.map((m) => <Message key={m.id} m={m} activeReportId={session?.activeReportId ?? null} onShowReport={onShowReport} />)
        )}
      </div>

      {!storageOk && (
        <div role="status" className="border-t border-line bg-warn-soft px-4 py-1.5 text-xs text-warn">
          Chats cannot be saved in this browser (storage is blocked), so they will be lost when you leave.
        </div>
      )}
      {busyElsewhere && !running && (
        <div role="status" className="border-t border-line px-4 py-1.5 text-xs text-muted">
          A reply is being written in another chat. You can send here when it finishes.
        </div>
      )}

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
            disabled={running || busyElsewhere || !draft.trim()}
            className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-surface transition-opacity disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
