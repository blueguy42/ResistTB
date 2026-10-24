import type { Report, ToolStep } from "./types";

// A chat session: its transcript and one saved report per turn that produced one. Kept in this browser (IndexedDB),
// so nothing is sent anywhere and there is no login.

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  steps?: ToolStep[];
  error?: string;
  reportId?: string; // the report this turn produced
  pending?: boolean; // the assistant's reply is still being written
  at: number;
}

export interface SessionReport {
  id: string;
  report: Report;
  at: number;
  label: string; // what the report is of, e.g. "embB p.Met306Val, rpsL p.Lys43Arg"
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  reports: SessionReport[];
  activeReportId: string | null; // null: the page's starting report
}

export const MAX_SESSIONS = 50;
export const MAX_REPORTS_PER_SESSION = 20;

export const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36);

export function newSession(): Session {
  const now = Date.now();
  return { id: uid(), title: "New chat", createdAt: now, updatedAt: now, messages: [], reports: [], activeReportId: null };
}

export function titleFrom(text: string): string {
  const t = text.replace(/\s+/g, " ").trim();
  return t.length > 48 ? `${t.slice(0, 47)}…` : t || "New chat";
}

export function reportLabel(r: Report): string {
  const names = r.candidates.map((c) => `${c.gene} ${c.mutation}`);
  return names.length > 3 ? `${names.slice(0, 3).join(", ")} +${names.length - 3}` : names.join(", ") || "no assays";
}

/** What the backend remembers of the chat: finished turns only, newest last. The server keeps the last six. */
export function modelHistory(messages: ChatMessage[]): { role: "user" | "model"; text: string }[] {
  return messages
    .filter((m) => !m.pending && m.text.trim())
    .map((m) => ({ role: m.role === "user" ? ("user" as const) : ("model" as const), text: m.text }))
    .slice(-12);
}

export function ago(ms: number, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - ms) / 1000));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

// ---- storage -------------------------------------------------------------------------------------------------------

const DB_NAME = "resisttb";
const STORE = "sessions";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") return reject(new Error("no IndexedDB"));
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function run<T>(mode: IDBTransactionMode, fn: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const req = fn(tx.objectStore(STORE));
        tx.oncomplete = () => {
          db.close();
          resolve(req.result);
        };
        tx.onerror = tx.onabort = () => {
          db.close();
          reject(tx.error);
        };
      }),
  );
}

/** Saved sessions, newest first. Empty when storage is unavailable (private window, blocked site data). */
export async function loadSessions(): Promise<Session[]> {
  try {
    const all = (await run("readonly", (s) => s.getAll())) as Session[];
    return all
      .filter((s) => s && Array.isArray(s.messages) && Array.isArray(s.reports))
      .map((s) => ({ ...s, messages: s.messages.map((m) => (m.pending ? { ...m, pending: false, error: m.error ?? "This reply was interrupted." } : m)) }))
      .sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export async function saveSession(s: Session): Promise<boolean> {
  try {
    await run("readwrite", (store) => store.put(s));
    return true;
  } catch {
    return false;
  }
}

export async function deleteSession(id: string): Promise<boolean> {
  try {
    await run("readwrite", (store) => store.delete(id));
    return true;
  } catch {
    return false;
  }
}
