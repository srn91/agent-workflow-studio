# agent-workflow-studio

`agent-workflow-studio` is a narrow workflow-orchestration demo for purchase-order exception triage. It shows how a supervisor/worker graph can route one business workflow through bounded local tools, one retry branch, one human approval gate, and an auditable execution trace.

## Problem

Refund and exception workflows are a poor fit for an open-ended agent loop. Operations teams need a flow that is easy to debug, easy to constrain, and explicit about when automation should stop and ask for human approval.

In production, the value is not generic autonomy. The value is a single controlled lane that can evaluate one exception, explain why it made a decision, and stop cleanly when the policy says a human needs to look at it.

This repo focuses on one workflow only:

- a purchase-order exception arrives
- the supervisor plans the run
- the worker loads the order and policy context with local tools
- the graph either auto-approves, rejects, or pauses for human approval

## Architecture

```mermaid
flowchart TD
    A["Exception Request"] --> B["Supervisor Plan Step"]
    B --> C["Worker: load_order tool"]
    C -->|temporary timeout| D["Retry once"]
    D --> C
    C --> E["Worker: load_policy tool"]
    E --> F{"Policy decision"}
    F -->|amount over limit| G["Approval gate"]
    F -->|already refunded| H["Reject request"]
    F -->|within policy| I["Approve request"]
    G --> J["Persist summary + JSONL trace + SQLite record"]
    H --> J
    I --> J
```

## Execution Flow

This repo is the "Hello World" version of an agent workflow:

1. Input: a purchase-order exception request enters the system.
2. Supervisor: the planner picks the only supported workflow path and decides whether a retry is allowed.
3. Worker: local tools load order and policy context.
4. Decision: the graph approves, rejects, or routes the request to human review.
5. Output: a summary, trace, and SQLite run record are written for later inspection.

## Why This Shape

- A supervisor/worker graph is easier to reason about than a free-running loop.
- Two local tools keep the boundary small and testable.
- A single retry path demonstrates transient failure handling without pretending to solve distributed systems.
- A first-class approval gate makes the stop condition explicit.
- JSONL traces plus a small SQLite run log make the flow inspectable after execution.

## Repository Layout

```text
app/
  cli.py          # local demo entry point
  main.py         # FastAPI app for replaying the workflow
  models.py       # request, state, and trace models
  storage.py      # summary, trace, and SQLite persistence
  tools.py        # local order/policy tools
  workflow.py     # supervisor/worker orchestration
fixtures/
  orders.json
  policies.json
tests/
generated/        # created after demo or API runs
```

## Tradeoffs

- This is intentionally one workflow, not a generic agent platform.
- The tools are local JSON-backed lookups instead of external services so the repo stays deterministic.
- The graph demonstrates control and auditability over breadth.
- The approval gate is modeled as a status transition, not a full human task system.

## Run Steps

### 1. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Run the full local verification flow

```bash
make verify
```

That command runs linting, tests, and a deterministic demo that writes:

- `generated/workflow_summary.json`
- `generated/workflow_trace.jsonl`
- `generated/workflow_runs.sqlite3`

If you only want the shortest version, `python3 -m app.cli demo` runs the same workflow without starting the API server.

### 3. Start the API

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8005
```

### 4. Trigger the default retry scenario

```bash
curl -X POST http://127.0.0.1:8005/runs/demo
```

### 5. Trigger the approval path directly

```bash
curl -X POST http://127.0.0.1:8005/runs \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ord_1001",
    "requested_amount": 250.0,
    "reason_code": "damaged_item",
    "simulate_order_lookup_failure": false
  }'
```

### 6. Inspect the latest run summary and filtered trace

```bash
curl http://127.0.0.1:8005/runs/latest
curl http://127.0.0.1:8005/runs/latest/trace
```

## Validation

The repo is only considered publishable when these checks pass:

- `ruff check app tests`
- `pytest -q`
- `python3 -m app.cli demo`

The tests cover:

- retry then auto-approval
- approval-gate routing
- reject path for an already-refunded order
- FastAPI demo and trace endpoints

## What To Look At First

- `app/workflow.py` for the actual graph logic
- `app/tools.py` for the bounded tool surface
- `app/storage.py` for the audit trail
- `tests/test_workflow.py` for the three business branches

## Next Steps

- replace JSON fixtures with a small service adapter layer
- store richer per-step timing in the trace
- add a manual approval action endpoint
- support multiple workflow templates behind the same control surface
