from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


RunStatus = Literal["approved", "needs_human_approval", "rejected"]
ApprovalAction = Literal["approve", "reject"]


@dataclass(frozen=True)
class WorkflowRequest:
    order_id: str
    requested_amount: float
    reason_code: str
    simulate_order_lookup_failure: bool = True


@dataclass(frozen=True)
class ApprovalDecisionRequest:
    action: ApprovalAction
    actor: str
    note: str | None = None


@dataclass
class WorkflowState:
    run_id: str
    order_id: str
    requested_amount: float
    reason_code: str
    simulate_order_lookup_failure: bool
    retries_used: int = 0
    order: dict[str, object] | None = None
    policy: dict[str, object] | None = None
    status: RunStatus | None = None
    decision_reason: str | None = None
    resolution_actor: str | None = None
    resolution_note: str | None = None
    trace_events: list["TraceEvent"] = field(default_factory=list)


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    step: str
    attempt: int
    status: str
    detail: str
    started_at: str
    completed_at: str
    duration_ms: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
