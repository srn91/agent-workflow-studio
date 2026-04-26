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
                decision_reason text not null,
                resolution_actor text,
                resolution_note text,
                run_payload text not null default '{}'
            )
            """
        )
        columns = {
            row[1] for row in connection.execute("pragma table_info(workflow_runs)").fetchall()
        }
        if "resolution_actor" not in columns:
            connection.execute("alter table workflow_runs add column resolution_actor text")
        if "resolution_note" not in columns:
            connection.execute("alter table workflow_runs add column resolution_note text")
        if "run_payload" not in columns:
            connection.execute(
                "alter table workflow_runs add column run_payload text not null default '{}'"
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


def load_run_summary(run_id: str) -> dict[str, object] | None:
    ensure_storage()
    connection = sqlite3.connect(DB_PATH)
    try:
        row = connection.execute(
            "select run_payload from workflow_runs where run_id = ?",
            (run_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return json.loads(row[0])


def persist_run(state: WorkflowState, summary: dict[str, object]) -> None:
    ensure_storage()
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(
            """
            insert or replace into workflow_runs (
                run_id,
                order_id,
                requested_amount,
                reason_code,
                status,
                decision_reason,
                resolution_actor,
                resolution_note,
                run_payload
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.run_id,
                state.order_id,
                state.requested_amount,
                state.reason_code,
                state.status,
                state.decision_reason,
                state.resolution_actor,
                state.resolution_note,
                json.dumps(summary),
            ),
        )
        connection.commit()
    finally:
        connection.close()
