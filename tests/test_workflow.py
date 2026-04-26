from __future__ import annotations

import json
import sqlite3

import app.storage as storage
from app.models import WorkflowRequest
from app.workflow import run_workflow


def test_retry_and_auto_approval_path() -> None:
    summary = run_workflow(
        WorkflowRequest(
            order_id="ord_1002",
            requested_amount=85.0,
            reason_code="damaged_item",
            simulate_order_lookup_failure=True,
        )
    )

    assert summary["retries_used"] == 1
    assert summary["status"] == "approved"


def test_human_approval_path() -> None:
    summary = run_workflow(
        WorkflowRequest(
            order_id="ord_1001",
            requested_amount=250.0,
            reason_code="damaged_item",
            simulate_order_lookup_failure=False,
        )
    )

    assert summary["status"] == "needs_human_approval"
    assert "auto-approval limit" in summary["decision_reason"]


def test_reject_already_refunded_order() -> None:
    summary = run_workflow(
        WorkflowRequest(
            order_id="ord_1003",
            requested_amount=20.0,
            reason_code="late_delivery",
            simulate_order_lookup_failure=False,
        )
    )

    assert summary["status"] == "rejected"
    assert "already refunded" in summary["decision_reason"]


def test_run_persists_summary_trace_and_sqlite_record(tmp_path, monkeypatch) -> None:
    generated_dir = tmp_path / "generated"
    monkeypatch.setattr(storage, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(storage, "TRACE_PATH", generated_dir / "workflow_trace.jsonl")
    monkeypatch.setattr(storage, "SUMMARY_PATH", generated_dir / "workflow_summary.json")
    monkeypatch.setattr(storage, "DB_PATH", generated_dir / "workflow_runs.sqlite3")

    summary = run_workflow(
        WorkflowRequest(
            order_id="ord_1002",
            requested_amount=85.0,
            reason_code="damaged_item",
            simulate_order_lookup_failure=True,
        )
    )

    saved_summary = json.loads(storage.SUMMARY_PATH.read_text(encoding="utf-8"))
    assert saved_summary["run_id"] == summary["run_id"]

    trace_events = [
        json.loads(line)
        for line in storage.TRACE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert trace_events
    assert {event["run_id"] for event in trace_events} == {summary["run_id"]}

    connection = sqlite3.connect(storage.DB_PATH)
    try:
        row = connection.execute(
            "select status, decision_reason from workflow_runs where run_id = ?",
            (summary["run_id"],),
        ).fetchone()
    finally:
        connection.close()

    assert row == (summary["status"], summary["decision_reason"])
