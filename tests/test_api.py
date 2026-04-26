from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_demo_run_and_trace_endpoints() -> None:
    response = client.post("/runs/demo")

    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "approved"

    trace_response = client.get("/runs/latest/trace")
    assert trace_response.status_code == 200
    events = trace_response.json()["events"]
    assert len(events) >= 4
    assert {event["run_id"] for event in events} == {run["run_id"]}


def test_custom_run_exposes_approval_branch() -> None:
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


def test_manual_approval_endpoint_resolves_paused_run() -> None:
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


def test_manual_approval_endpoint_rejects_non_paused_run() -> None:
    approved = client.post("/runs/demo").json()

    response = client.post(
        f"/runs/{approved['run_id']}/approval",
        json={"action": "reject", "actor": "finance-manager"},
    )

    assert response.status_code == 409
