"""The assistant: a Gemini model on Vertex AI that plans the work and calls our tools.

The model never produces a number. Every figure in the report comes from the tools; the model chooses
which tools to run, in what order, and writes the explanation. Tool arguments are validated here."""
from __future__ import annotations

import os
import subprocess
import threading
import time
from collections.abc import Iterator
from typing import Any

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

from .assay import build_report
from .genome import load_genes
from .snapshot import DEFAULT_SNAPSHOT
from .targets import default_targets

PROJECT = os.environ.get("GENOHACK_PROJECT", "haduh-512512")
LOCATION = os.environ.get("GENOHACK_LOCATION", "global")
MODEL = os.environ.get("GENOHACK_MODEL", "gemini-3.5-flash-lite")
RESULTS = os.environ.get("GENOHACK_RESULTS", "results")
# A precomputed copy of the variant windows (see snapshot.py). Set GENOHACK_SNAPSHOT to a file to use it, or leave
# it unset: the bundled snapshot is used only when there is no results/ folder, as in a small container.
SNAPSHOT = os.environ.get("GENOHACK_SNAPSHOT") or (
    str(DEFAULT_SNAPSHOT) if not __import__("pathlib").Path(RESULTS).exists() and DEFAULT_SNAPSHOT.exists() else None
)
MAX_TURNS = 5

TARGETS = {t.id: t for t in default_targets(load_genes())}
TARGET_DOC = {
    "rpoB_S450L": "rifampicin resistance (rpoB Ser450Leu)",
    "katG_S315T": "isoniazid resistance (katG Ser315Thr)",
    "inhA_c-15": "isoniazid and ethionamide resistance (inhA promoter, c.-15C>T)",
    "gyrA_D94G": "fluoroquinolone resistance (gyrA Asp94Gly)",
}

SYSTEM = f"""You are ChatGP-TB, an assistant that designs qPCR primers and allele-specific probes for drug-resistant
Mycobacterium tuberculosis, using genomes from Indonesian patients.

Rules:
- Call design_assays to get any primer, probe, score or coverage. Never invent or estimate numbers or sequences.
- Pick targets from the drugs the user names: rifampicin -> rpoB_S450L; isoniazid -> katG_S315T and inhA_c-15;
  fluoroquinolones -> gyrA_D94G. If the user names no drug, use all four. Do not add targets they did not ask for.
- After the tool returns, summarise in plain language: which assay ranks first and why, the coverage, and the main
  limits. Quote numbers exactly as returned, and give each assay's isolate_matches sentence word for word, without saying that name. Never write a coverage
  figure like '14/14'. Write plain text: no markdown, no asterisks, no bullet symbols, and never mention tool or field
  names. Keep it under 120 words.
- Always say the results are in silico only, not tested in the lab, and that they were designed and measured on the same
  isolates, which come from the regions named in the result (see regions).
- If the user asks how an assay does in a region, quote that region's region_matches sentence word for word.
- If the result has a multiplex section, say which assays can share a tube and that the grouping is a model.
- If asked something unrelated to TB assay design, say briefly that you only help with this.
Targets: {"; ".join(f"{k} = {v}" for k, v in TARGET_DOC.items())}."""

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="design_assays",
            description="Design and score qPCR primer pairs and wild-type/mutant probes for resistance targets, "
                        "using the finished isolates from all regions together. Returns ranked assays with scores and coverage.",
            parameters_json_schema={
                "type": "object",
                "properties": {"targets": {
                    "type": "array", "minItems": 1,
                    "items": {"type": "string", "enum": list(TARGETS)},
                    "description": "Targets to design for. " + "; ".join(f"{k}: {v}" for k, v in TARGET_DOC.items()),
                }},
                "required": ["targets"],
            },
        )
    ])
]

_client: genai.Client | None = None
_client_lock = threading.Lock()
_report_cache: dict[tuple, dict] = {}


def _make_client() -> genai.Client:
    """On Cloud Run, Application Default Credentials work. On a laptop with only `gcloud auth login`,
    fall back to a short-lived gcloud access token."""
    try:
        return genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    except Exception:
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
        return genai.Client(vertexai=True, project=PROJECT, location=LOCATION, credentials=Credentials(token=token))


def client() -> genai.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = _make_client()
        return _client


def refresh_client() -> None:
    global _client
    with _client_lock:
        _client = None


def coverage_text(cov: dict) -> str:
    """One sentence the model quotes verbatim, so it cannot blur exact matches with near matches."""
    n, one, fail = cov["isolates_total"], cov["one_mismatch"], cov["failing"]
    return (f"{cov['perfect_match']} of {n} isolates match every oligo exactly; {one} more {'has' if one == 1 else 'have'} a single "
            f"mismatch that should not break the assay; {fail} {'carries' if fail == 1 else 'carry'} a variant likely to break it")


def _compact(report: dict) -> dict:
    """What the model sees: enough to explain the result, nothing it could mistake for an invitation to invent."""
    return {
        "isolates": report["dataset"]["isolates"],
        "regions": report["dataset"].get("regions", {}),
        "assays": [
            {
                "rank": c["rank"], "target": f"{c['gene']} {c['mutation']}", "drug": c["drug"], "who_tier": c["who_tier"],
                "scores": c["scores"], "isolate_matches": coverage_text(c["coverage"]),
                "probe_tm_gap_c": [o["mismatch_dtm"] for o in c["oligos"] if "mismatch_dtm" in o],
                "specificity": c["specificity"]["note"], "caveats": c["caveats"],
                **({"region_matches": {r: f"{v['perfect_match']} of {v['isolates']} isolates match every oligo exactly; "
                                          f"{v['failing']} likely to fail" for r, v in c["coverage"]["by_region"].items()}}
                   if len(c["coverage"].get("by_region", {})) > 1 else {}),
            }
            for c in report["candidates"]
        ],
        "multiplex": (None if not report.get("multiplex") else {
            "tubes": report["multiplex"]["tubes"], "note": report["multiplex"]["note"],
            "conflicts": [f"{p['a']} x {p['b']}" for p in report["multiplex"]["pairs"] if p["status"] == "conflict"],
        }),
        "validation": "in silico only",
    }


def run_design(targets: list[str]) -> dict:
    ids = [t for t in dict.fromkeys(targets) if t in TARGETS]
    if not ids:
        raise ValueError("no valid targets")
    key = (tuple(sorted(ids)), SNAPSHOT or RESULTS, 0 if SNAPSHOT else len(list(__import__("pathlib").Path(RESULTS).glob("*/DONE"))))
    if key not in _report_cache:
        _report_cache[key] = build_report(RESULTS, target_ids=ids, snapshot=SNAPSHOT)
    return _report_cache[key]


def chat(message: str, history: list[dict] | None = None) -> Iterator[dict[str, Any]]:
    """Yield events for the interface: step, report, text, error, done."""
    contents: list[types.Content] = []
    for turn in history or []:
        contents.append(types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["text"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM, tools=TOOLS, temperature=0.2)

    step_no = 0
    t0 = time.perf_counter()
    yield {"type": "step", "step": {"id": "s0", "tool": "plan", "label": "Read the request and plan the tools", "status": "running"}}
    try:
        for turn in range(MAX_TURNS):
            try:
                resp = client().models.generate_content(model=MODEL, contents=contents, config=cfg)
            except Exception as exc:  # token expired or transient: retry once with a fresh client
                refresh_client()
                try:
                    resp = client().models.generate_content(model=MODEL, contents=contents, config=cfg)
                except Exception:
                    raise exc
            if turn == 0:
                yield {"type": "step", "step": {"id": "s0", "tool": "plan", "label": "Read the request and plan the tools",
                                                  "status": "done", "seconds": round(time.perf_counter() - t0, 1)}}
            content = resp.candidates[0].content
            calls = [p.function_call for p in content.parts if p.function_call]
            if not calls:
                yield {"type": "text", "text": (resp.text or "").replace("**", "").replace("isolate_matches", "coverage").strip()}
                break
            contents.append(content)
            replies = []
            for call in calls:
                step_no += 1
                sid = f"s{step_no}"
                args = dict(call.args or {})
                label = "Design primers and probes, check specificity and coverage"
                yield {"type": "step", "step": {"id": sid, "tool": call.name, "label": label,
                                                  "detail": ", ".join(args.get("targets", [])), "status": "running"}}
                t1 = time.perf_counter()
                try:
                    if call.name != "design_assays":
                        raise ValueError(f"unknown tool {call.name}")
                    report = {**run_design(list(args.get("targets", []))), "request": message}  # the cache holds the default text
                    result = _compact(report)
                    yield {"type": "report", "report": report}
                except Exception as exc:
                    result = {"error": str(exc)}
                yield {"type": "step", "step": {"id": sid, "tool": call.name, "label": label,
                                                  "detail": ", ".join(args.get("targets", [])),
                                                  "status": "done", "seconds": round(time.perf_counter() - t1, 1)}}
                replies.append(types.Part.from_function_response(name=call.name, response={"result": result}))
            contents.append(types.Content(role="user", parts=replies))
        else:
            yield {"type": "text", "text": "I could not finish within the allowed number of steps."}
    except Exception as exc:
        yield {"type": "error", "message": f"{type(exc).__name__}: {exc}"[:400]}
    yield {"type": "done"}
