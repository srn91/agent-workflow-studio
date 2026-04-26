from __future__ import annotations

import json
import sqlite3

from app.config import DB_PATH, GENERATED_DIR, SUMMARY_PATH, TRACE_PATH
from app.models import TraceEvent, WorkflowState


def ensure_storage() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            create table if not exists workflow_runs (
                run_id text primary key,
                order_id text not null,
                requested_amount real not null,
                reason_code text not null,
                status text not null,
                decision_reason text not null
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def append_trace(event: TraceEvent) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    with TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict()) + "\n")


def persist_summary(summary: dict[str, object]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def persist_run(state: WorkflowState) -> None:
    ensure_storage()
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            insert or replace into workflow_runs (run_id, order_id, requested_amount, reason_code, status, decision_reason)
            values (?, ?, ?, ?, ?, ?)
            """,
            (
                state.run_id,
                state.order_id,
                state.requested_amount,
                state.reason_code,
                state.status,
                state.decision_reason,
            ),
        )
        connection.commit()
    finally:
        connection.close()
