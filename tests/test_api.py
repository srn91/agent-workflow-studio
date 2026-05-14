from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main
import app.storage as storage


def _configure_generated_paths(tmp_path: Path, monkeypatch) -> None:
    generated_dir = tmp_path / "generated"
    monkeypatch.setattr(storage, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(storage, "TRACE_PATH", generated_dir / "workflow_trace.jsonl")
    monkeypatch.setattr(storage, "SUMMARY_PATH", generated_dir / "workflow_summary.json")
    monkeypatch.setattr(storage, "DB_PATH", generated_dir / "workflow_runs.sqlite3")
    monkeypatch.setattr(main, "TRACE_PATH", generated_dir / "workflow_trace.jsonl")
    monkeypatch.setattr(main, "SUMMARY_PATH", generated_dir / "workflow_summary.json")


def test_root_endpoint_lists_public_api_paths() -> None:
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project"] == "agent-workflow-studio"
    assert payload["status"] == "ready"
    assert payload["endpoints"]["docs"] == "/docs"


def test_demo_run_and_trace_endpoints(tmp_path, monkeypatch) -> None:
    _configure_generated_paths(tmp_path, monkeypatch)
    client = TestClient(main.app)
    response = client.post("/runs/demo")

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "approved"
    assert run["timing_summary"]["total_duration_ms"] > 0

    trace_response = client.get("/runs/latest/trace")
    assert trace_response.status_code == 200
    payload = trace_response.json()
    events = payload["events"]
    assert len(events) >= 4
    assert {event["run_id"] for event in events} == {run["run_id"]}
    assert payload["timing_summary"]["slowest_step"]["duration_ms"] > 0
    assert all("duration_ms" in event and "started_at" in event and "completed_at" in event for event in events)


def test_custom_run_exposes_approval_branch(tmp_path, monkeypatch) -> None:
    _configure_generated_paths(tmp_path, monkeypatch)
    client = TestClient(main.app)
    response = client.post(
        "/runs",
        json={
            "order_id": "ord_1001",
            "requested_amount": 250.0,
            "reason_code": "damaged_item",
            "simulate_order_lookup_failure": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_human_approval"


def test_manual_approval_endpoint_resolves_paused_run(tmp_path, monkeypatch) -> None:
    _configure_generated_paths(tmp_path, monkeypatch)
    client = TestClient(main.app)
    pending = client.post(
        "/runs",
        json={
            "order_id": "ord_1001",
            "requested_amount": 250.0,
            "reason_code": "damaged_item",
            "simulate_order_lookup_failure": False,
        },
    ).json()

    response = client.post(
        f"/runs/{pending['run_id']}/approval",
        json={
            "action": "approve",
            "actor": "finance-manager",
            "note": "Approved after refund exception review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["resolution_actor"] == "finance-manager"
    assert body["timing_summary"]["steps"][-1]["step"] == "manual_approval_action"


def test_manual_approval_endpoint_rejects_non_paused_run(tmp_path, monkeypatch) -> None:
    _configure_generated_paths(tmp_path, monkeypatch)
    client = TestClient(main.app)
    approved = client.post("/runs/demo").json()

    response = client.post(
        f"/runs/{approved['run_id']}/approval",
        json={"action": "reject", "actor": "finance-manager"},
    )

    assert response.status_code == 409
