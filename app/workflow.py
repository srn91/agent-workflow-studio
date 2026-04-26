from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.models import ApprovalDecisionRequest, TraceEvent, WorkflowRequest, WorkflowState
from app.storage import append_trace, load_run_summary, persist_run, persist_summary
from app.tools import load_order, load_policy


def _record_trace(
    state: WorkflowState,
    *,
    step: str,
    attempt: int,
    status: str,
    detail: str,
    started_at: datetime,
    started_counter: float,
) -> None:
    completed_at = datetime.now(UTC)
    event = TraceEvent(
        run_id=state.run_id,
        step=step,
        attempt=attempt,
        status=status,
        detail=detail,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=round((perf_counter() - started_counter) * 1000.0, 3),
    )
    state.trace_events.append(event)
    append_trace(event)


def _timed_step(
    state: WorkflowState,
    *,
    step: str,
    attempt: int = 1,
    success_detail: str,
    error_status: str = "failed",
):
    started_at = datetime.now(UTC)
    started_counter = perf_counter()

    def finalize(status: str, detail: str) -> None:
        _record_trace(
            state,
            step=step,
            attempt=attempt,
            status=status,
            detail=detail,
            started_at=started_at,
            started_counter=started_counter,
        )

    return finalize, success_detail


def _summary_from_state(state: WorkflowState) -> dict[str, object]:
    total_duration_ms = round(sum(event.duration_ms for event in state.trace_events), 3)
    slowest_event = max(state.trace_events, key=lambda event: event.duration_ms)
    return {
        "run_id": state.run_id,
        "order_id": state.order_id,
        "requested_amount": state.requested_amount,
        "reason_code": state.reason_code,
        "retries_used": state.retries_used,
        "status": state.status,
        "decision_reason": state.decision_reason,
        "resolution_actor": state.resolution_actor,
        "resolution_note": state.resolution_note,
        "order": state.order,
        "policy": state.policy,
        "timing_summary": {
            "total_duration_ms": total_duration_ms,
            "slowest_step": {
                "step": slowest_event.step,
                "attempt": slowest_event.attempt,
                "status": slowest_event.status,
                "duration_ms": slowest_event.duration_ms,
            },
            "steps": [
                {
                    "step": event.step,
                    "attempt": event.attempt,
                    "status": event.status,
                    "duration_ms": event.duration_ms,
                }
                for event in state.trace_events
            ],
        },
    }


def run_workflow(request: WorkflowRequest) -> dict[str, object]:
    state = WorkflowState(
        run_id=f"run-{uuid4().hex[:10]}",
        order_id=request.order_id,
        requested_amount=request.requested_amount,
        reason_code=request.reason_code,
        simulate_order_lookup_failure=request.simulate_order_lookup_failure,
    )

    finalize, detail = _timed_step(
        state,
        step="supervisor_plan",
        success_detail="Supervisor planned refund-review workflow.",
    )
    finalize("success", detail)

    while True:
        attempt = state.retries_used + 1
        finalize, detail = _timed_step(
            state,
            step="load_order_tool",
            attempt=attempt,
            success_detail=f"Loaded order {state.order_id}.",
        )
        try:
            state.order = load_order(state.order_id, state.simulate_order_lookup_failure, state.retries_used)
            finalize("success", detail)
            break
        except RuntimeError as exc:
            finalize("retry", str(exc))
            state.retries_used += 1
            if state.retries_used > 1:
                raise

    finalize, detail = _timed_step(
        state,
        step="load_policy_tool",
        success_detail=f"Loaded policy for reason {state.reason_code}.",
    )
    state.policy = load_policy(state.reason_code)
    finalize("success", detail)

    approval_threshold = float(state.policy["auto_approval_limit"])
    finalize, _ = _timed_step(state, step="policy_decision", success_detail="")
    if state.requested_amount > approval_threshold:
        state.status = "needs_human_approval"
        state.decision_reason = "Requested amount exceeds auto-approval limit."
        finalize("blocked", state.decision_reason)
    elif bool(state.order["already_refunded"]):
        state.status = "rejected"
        state.decision_reason = "Order was already refunded."
        finalize("rejected", state.decision_reason)
    else:
        state.status = "approved"
        state.decision_reason = "Request is within policy and eligible for automatic approval."
        finalize("approved", state.decision_reason)

    summary = _summary_from_state(state)
    persist_summary(summary)
    persist_run(state, summary)
    return summary


def resolve_approval(run_id: str, request: ApprovalDecisionRequest) -> dict[str, object]:
    summary = load_run_summary(run_id)
    if summary is None:
        raise KeyError(f"Run {run_id} was not found.")
    if summary["status"] != "needs_human_approval":
        raise ValueError("Only paused approval runs can be resolved manually.")

    status = "approved" if request.action == "approve" else "rejected"
    decision_reason = (
        f"Manual approval granted by {request.actor}."
        if request.action == "approve"
        else f"Manual rejection recorded by {request.actor}."
    )
    note_suffix = f" Note: {request.note}" if request.note else ""

    summary["status"] = status
    summary["decision_reason"] = decision_reason
    summary["resolution_actor"] = request.actor
    summary["resolution_note"] = request.note

    state = WorkflowState(
        run_id=summary["run_id"],
        order_id=summary["order_id"],
        requested_amount=float(summary["requested_amount"]),
        reason_code=summary["reason_code"],
        simulate_order_lookup_failure=False,
        retries_used=int(summary["retries_used"]),
        order=summary.get("order"),
        policy=summary.get("policy"),
        status=status,
        decision_reason=decision_reason,
        resolution_actor=request.actor,
        resolution_note=request.note,
    )
    historical_steps = summary.get("timing_summary", {}).get("steps", [])
    state.trace_events = [
        TraceEvent(
            run_id=summary["run_id"],
            step=str(step["step"]),
            attempt=int(step.get("attempt", 1)),
            status=str(step["status"]),
            detail="Historical event recorded in previous run segment.",
            started_at="persisted",
            completed_at="persisted",
            duration_ms=float(step["duration_ms"]),
        )
        for step in historical_steps
    ]
    finalize, _ = _timed_step(
        state,
        step="manual_approval_action",
        success_detail=f"{decision_reason}{note_suffix}",
    )
    finalize(status, f"{decision_reason}{note_suffix}")
    summary = _summary_from_state(state)
    persist_summary(summary)
    persist_run(state, summary)
    return summary
