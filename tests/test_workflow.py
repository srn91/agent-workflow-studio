from __future__ import annotations

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
