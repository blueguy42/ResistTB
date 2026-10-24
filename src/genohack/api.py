"""HTTP API for the interface. Run: uvicorn genohack.api:app --port 8000"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent

ORIGINS = [o.strip() for o in os.environ.get("GENOHACK_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="ChatGP-TB")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    # Local dev: any localhost port, so a busy 3000 does not break chat. Off once GENOHACK_ORIGINS lists the hosted page.
    allow_origin_regex=None if ORIGINS else r"http://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
REPORT = Path(agent.__file__).resolve().parents[2] / "web" / "data" / "report.json"


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": agent.MODEL, "location": agent.LOCATION, "results": agent.RESULTS, "snapshot": agent.SNAPSHOT}


@app.get("/api/report")
def report() -> JSONResponse:
    if not REPORT.exists():
        return JSONResponse({"error": "no report yet"}, status_code=404)
    return JSONResponse(json.loads(REPORT.read_text()))


PER_IP_HOUR = int(os.environ.get("GENOHACK_CHATS_PER_IP_HOUR", "20"))  # 0 turns a limit off
PER_DAY = int(os.environ.get("GENOHACK_CHATS_PER_DAY", "300"))
_by_ip: dict[str, deque] = {}
_today: deque = deque()


def _allow(ip: str) -> bool:
    """In-memory limits: each chat calls Gemini, so a public link needs a ceiling. Resets when the instance restarts."""
    now = time.time()
    while _today and now - _today[0] > 86400:
        _today.popleft()
    hits = _by_ip.setdefault(ip, deque())
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(_by_ip) > 2000:
        for k in [k for k, v in _by_ip.items() if not v and k != ip]:
            del _by_ip[k]
    if (PER_DAY and len(_today) >= PER_DAY) or (PER_IP_HOUR and len(hits) >= PER_IP_HOUR):
        return False
    hits.append(now)
    _today.append(now)
    return True


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    fwd = request.headers.get("x-forwarded-for", "")  # Cloud Run puts the caller first
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    if not _allow(ip):
        return JSONResponse({"error": "chat limit reached, try again later"}, status_code=429)

    def events():
        for ev in agent.chat(body.message.strip()[:2000], body.history[-6:]):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# The static web page (pnpm build:site writes web/site). Mounted last so the /api routes win.
SITE = Path(agent.__file__).resolve().parents[2] / "web" / "site"
if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
