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


class RateLimit:
    """In-memory ceilings per caller and per day (0 turns one off). They reset when the instance restarts."""

    def __init__(self, per_ip_hour: int, per_day: int) -> None:
        self.per_ip_hour, self.per_day = per_ip_hour, per_day
        self._by_ip: dict[str, deque] = {}
        self._today: deque = deque()

    def allow(self, ip: str) -> bool:
        now = time.time()
        while self._today and now - self._today[0] > 86400:
            self._today.popleft()
        hits = self._by_ip.setdefault(ip, deque())
        while hits and now - hits[0] > 3600:
            hits.popleft()
        if len(self._by_ip) > 2000:
            for k in [k for k, v in self._by_ip.items() if not v and k != ip]:
                del self._by_ip[k]
        if (self.per_day and len(self._today) >= self.per_day) or (self.per_ip_hour and len(hits) >= self.per_ip_hour):
            return False
        hits.append(now)
        self._today.append(now)
        return True


# Each chat calls Gemini, so it gets the tight limit. A library design runs no model, only the design code.
chat_limit = RateLimit(int(os.environ.get("GENOHACK_CHATS_PER_IP_HOUR", "20")), int(os.environ.get("GENOHACK_CHATS_PER_DAY", "300")))
design_limit = RateLimit(int(os.environ.get("GENOHACK_DESIGNS_PER_IP_HOUR", "60")), int(os.environ.get("GENOHACK_DESIGNS_PER_DAY", "1500")))


def _caller(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")  # Cloud Run puts the caller first
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


class DesignIn(BaseModel):
    targets: list[str]


@app.post("/api/design")
def design(body: DesignIn, request: Request) -> JSONResponse:
    """Design the picked targets from the target library panel: the same report a chat request returns, with no model call."""
    if not design_limit.allow(_caller(request)):
        return JSONResponse({"error": "design limit reached, try again later"}, status_code=429)
    ids = [t for t in dict.fromkeys(body.targets) if t in agent.TARGETS]
    if not ids:
        return JSONResponse({"error": "none of those ids is a target"}, status_code=400)
    try:
        report = agent.run_design(ids)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({**report, "request": "Target library: " + ", ".join(c["id"] for c in report["candidates"])})


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    if not chat_limit.allow(_caller(request)):
        return JSONResponse({"error": "chat limit reached, try again later"}, status_code=429)

    def events():
        for ev in agent.chat(body.message.strip()[:2000], body.history[-6:]):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# The static web page (pnpm build:site writes web/site). Mounted last so the /api routes win.
SITE = Path(agent.__file__).resolve().parents[2] / "web" / "site"
if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
