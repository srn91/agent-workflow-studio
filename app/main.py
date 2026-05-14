from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from app.config import SUMMARY_PATH, TRACE_PATH
from app.models import ApprovalDecisionRequest, WorkflowRequest
from app.workflow import resolve_approval, run_workflow


app = FastAPI(
    title="Agent Workflow Studio",
    description="A narrow workflow-control demo with retries, approval gates, and execution traces.",
    version="0.1.0",
)


def _load_latest_summary() -> dict[str, object]:
    if not SUMMARY_PATH.exists():
        raise HTTPException(status_code=404, detail="No workflow run has been recorded yet.")
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Workflow Studio</title>
<style>
body{margin:0;background:#f8fafc;color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.5}
main{max-width:1080px;margin:0 auto;padding:56px 24px}.hero{background:linear-gradient(135deg,#111827,#1d4ed8);color:white;border-radius:22px;padding:38px;box-shadow:0 24px 60px rgba(15,23,42,.18)}
.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#bfdbfe;font-weight:700}h1{font-size:42px;line-height:1.05;margin:10px 0 14px}.hero p{font-size:17px;color:#dbeafe;max-width:780px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:22px 0}.card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:18px;box-shadow:0 10px 30px rgba(15,23,42,.06)}
.metric{font-size:25px;font-weight:800;color:#0f172a}.label{font-size:13px;color:#64748b;margin-top:3px}.links{display:flex;flex-wrap:wrap;gap:12px;margin-top:22px}
a.button{background:#0f172a;color:white;text-decoration:none;padding:11px 14px;border-radius:10px;font-weight:700}a.secondary{background:white;color:#0f172a;border:1px solid #cbd5e1}
@media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:34px}}
</style></head>
<body><main>
<section class="hero"><div class="eyebrow">Agent workflow control</div><h1>Agent Workflow Studio</h1>
<p>Workflow orchestration service with bounded tools, retry handling, approval gates, persisted run records, and trace output.</p>
<div class="links"><a class="button" href="/docs">Run demo from API docs</a><a class="button secondary" href="/runs/latest">Latest run</a><a class="button secondary" href="/runs/latest/trace">Latest trace</a></div></section>
<section class="grid">
<div class="card"><div class="metric">retry</div><div class="label">tool failure handling</div></div>
<div class="card"><div class="metric">approval</div><div class="label">human gate path</div></div>
<div class="card"><div class="metric">JSONL</div><div class="label">execution trace</div></div>
<div class="card"><div class="metric">SQLite</div><div class="label">run records</div></div>
</section>
<section class="card"><p>Use the API docs to run a deterministic workflow, then inspect the latest run summary and trace to see the control flow.</p></section>
</main></body></html>"""


@app.post("/runs")
def run_custom(request: WorkflowRequest) -> dict[str, object]:
    return run_workflow(request)


@app.post("/runs/demo")
def run_demo() -> dict[str, object]:
    return run_workflow(
        WorkflowRequest(
            order_id="ord_1002",
            requested_amount=85.0,
            reason_code="damaged_item",
            simulate_order_lookup_failure=True,
        )
    )


@app.get("/runs/latest")
def latest_run() -> dict[str, object]:
    return _load_latest_summary()


@app.post("/runs/{run_id}/approval")
def approval_action(run_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
    try:
        return resolve_approval(run_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/runs/latest/trace")
def latest_trace() -> dict[str, object]:
    latest = _load_latest_summary()
    if not TRACE_PATH.exists():
        raise HTTPException(status_code=404, detail="No workflow trace has been recorded yet.")
    events = [
        json.loads(line)
        for line in TRACE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    latest_run_id = latest["run_id"]
    filtered_events = [event for event in events if event["run_id"] == latest_run_id]
    return {
        "events": filtered_events,
        "timing_summary": latest.get("timing_summary", {}),
    }
