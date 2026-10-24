"""HTTP API for the interface. Run: uvicorn genohack.api:app --port 8000"""
from __future__ import annotations

import json
from pathlib import Path

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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


@app.post("/api/chat")
def chat(body: ChatIn) -> StreamingResponse:
    def events():
        for ev in agent.chat(body.message.strip()[:2000], body.history[-6:]):
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
