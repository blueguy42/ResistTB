"""HTTP API for the interface. Run: uvicorn genohack.api:app --port 8000"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from . import agent

app = FastAPI(title="ChatGP-TB")
REPORT = Path(agent.__file__).resolve().parents[2] / "web" / "data" / "report.json"


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": agent.MODEL, "location": agent.LOCATION, "results": agent.RESULTS}


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
