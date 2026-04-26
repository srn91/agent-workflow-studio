from __future__ import annotations

from uuid import uuid4

from app.models import TraceEvent, WorkflowRequest, WorkflowState
from app.storage import append_trace, persist_run, persist_summary
from app.tools import load_order, load_policy


def _trace(state: WorkflowState, step: str, status: str, detail: str) -> None:
    append_trace(TraceEvent(run_id=state.run_id, step=step, status=status, detail=detail))


def run_workflow(request: WorkflowRequest) -> dict[str, object]:
    state = WorkflowState(
        run_id=f"run-{uuid4().hex[:10]}",
        order_id=request.order_id,
        requested_amount=request.requested_amount,
        reason_code=request.reason_code,
        simulate_order_lookup_failure=request.simulate_order_lookup_failure,
    )

    _trace(state, "supervisor_plan", "started", "Supervisor planned refund-review workflow.")

    while True:
        try:
            state.order = load_order(state.order_id, state.simulate_order_lookup_failure, state.retries_used)
            _trace(state, "load_order_tool", "success", f"Loaded order {state.order_id}.")
            break
        except RuntimeError as exc:
            _trace(state, "load_order_tool", "retry", str(exc))
            state.retries_used += 1
            if state.retries_used > 1:
                raise

    state.policy = load_policy(state.reason_code)
    _trace(state, "load_policy_tool", "success", f"Loaded policy for reason {state.reason_code}.")

    approval_threshold = float(state.policy["auto_approval_limit"])
    if state.requested_amount > approval_threshold:
        state.status = "needs_human_approval"
        state.decision_reason = "Requested amount exceeds auto-approval limit."
        _trace(state, "approval_gate", "blocked", state.decision_reason)
    elif bool(state.order["already_refunded"]):
        state.status = "rejected"
        state.decision_reason = "Order was already refunded."
        _trace(state, "decision", "rejected", state.decision_reason)
    else:
        state.status = "approved"
        state.decision_reason = "Request is within policy and eligible for automatic approval."
        _trace(state, "decision", "approved", state.decision_reason)

    summary = {
        "run_id": state.run_id,
        "order_id": state.order_id,
        "requested_amount": state.requested_amount,
        "reason_code": state.reason_code,
        "retries_used": state.retries_used,
        "status": state.status,
        "decision_reason": state.decision_reason,
        "order": state.order,
        "policy": state.policy,
    }
    persist_summary(summary)
    persist_run(state)
    return summary
