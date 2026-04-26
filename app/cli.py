from __future__ import annotations

from app.config import SUMMARY_PATH, TRACE_PATH
from app.models import WorkflowRequest
from app.workflow import run_workflow


def demo() -> None:
    summary = run_workflow(
        WorkflowRequest(
            order_id="ord_1002",
            requested_amount=85.0,
            reason_code="damaged_item",
            simulate_order_lookup_failure=True,
        )
    )
    print(f"run_id={summary['run_id']}")
    print(f"status={summary['status']}")
    timing_summary = summary["timing_summary"]
    print(f"total_duration_ms={timing_summary['total_duration_ms']}")
    print(
        "slowest_step="
        f"{timing_summary['slowest_step']['step']}"
        f"#{timing_summary['slowest_step']['attempt']}"
        f"({timing_summary['slowest_step']['duration_ms']}ms)"
    )
    print(f"trace_path={TRACE_PATH.relative_to(TRACE_PATH.parent.parent)}")
    print(f"summary_path={SUMMARY_PATH.relative_to(SUMMARY_PATH.parent.parent)}")


def main() -> None:
    import sys

    if len(sys.argv) != 2 or sys.argv[1] != "demo":
        raise SystemExit("usage: python3 -m app.cli demo")

    demo()


if __name__ == "__main__":
    main()
