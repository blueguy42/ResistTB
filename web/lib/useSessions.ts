"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MAX_SESSIONS, deleteSession, loadSessions, newSession, saveSession, type Session } from "./sessions";

const ACTIVE_KEY = "resisttb:active";

const remember = (id: string) => {
  try {
    localStorage.setItem(ACTIVE_KEY, id);
  } catch {
    /* storage blocked: the newest chat opens next time instead */
  }
};

/** Sessions kept in this browser: the list, the open one, and changes that are saved shortly after they happen. */
export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState("");
  const [ready, setReady] = useState(false);
  const [storageOk, setStorageOk] = useState(true);
  const dirty = useRef(new Set<string>());
  const latest = useRef<Session[]>([]);
  useEffect(() => {
    latest.current = sessions; // read by the save and delete paths, which run outside of render
  }, [sessions]);

  // Load once. If nothing is saved, start with one empty chat.
  useEffect(() => {
    let alive = true;
    loadSessions().then((saved) => {
      if (!alive) return;
      const list = saved.length ? saved : [newSession()];
      let wanted = "";
      try {
        wanted = localStorage.getItem(ACTIVE_KEY) ?? "";
      } catch {
        /* blocked */
      }
      setSessions(list);
      setActiveId(list.some((s) => s.id === wanted) ? wanted : list[0].id);
      setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  // Save changed sessions 400 ms after the last change, so streaming does not write on every event.
  useEffect(() => {
    if (!ready || dirty.current.size === 0) return;
    const t = setTimeout(async () => {
      const ids = [...dirty.current];
      dirty.current.clear();
      const results = await Promise.all(ids.map((id) => latest.current.find((s) => s.id === id)).filter(Boolean).map((s) => saveSession(s!)));
      setStorageOk(results.every(Boolean));
    }, 400);
    return () => clearTimeout(t);
  }, [sessions, ready]);

  const update = useCallback((id: string, fn: (s: Session) => Session) => {
    dirty.current.add(id);
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...fn(s), updatedAt: Date.now() } : s)));
  }, []);

  const select = useCallback((id: string) => {
    setActiveId(id);
    remember(id);
  }, []);

  const create = useCallback(() => {
    const s = newSession();
    dirty.current.add(s.id);
    setSessions((prev) => {
      const next = [s, ...prev];
      for (const old of next.slice(MAX_SESSIONS)) {
        dirty.current.delete(old.id);
        void deleteSession(old.id);
      }
      return next.slice(0, MAX_SESSIONS);
    });
    setActiveId(s.id);
    remember(s.id);
    return s.id;
  }, []);

  const remove = useCallback(
    (id: string) => {
      dirty.current.delete(id);
      void deleteSession(id);
      const rest = latest.current.filter((s) => s.id !== id);
      if (rest.length === 0) {
        const s = newSession();
        dirty.current.add(s.id);
        setSessions([s]);
        setActiveId(s.id);
        remember(s.id);
        return;
      }
      setSessions(rest);
      if (id === activeId) {
        setActiveId(rest[0].id);
        remember(rest[0].id);
      }
    },
    [activeId],
  );

  const rename = useCallback((id: string, title: string) => {
    update(id, (s) => ({ ...s, title: title.trim() || s.title }));
  }, [update]);

  return { sessions, activeId, active: sessions.find((s) => s.id === activeId) ?? null, ready, storageOk, update, select, create, remove, rename };
}
