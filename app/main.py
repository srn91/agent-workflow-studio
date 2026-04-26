from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException

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
def latest_trace() -> dict[str, list[dict[str, object]]]:
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
    return {"events": filtered_events}
