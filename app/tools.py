from __future__ import annotations

import json

from app.config import FIXTURES_DIR


def load_order(order_id: str, simulate_failure: bool, retries_used: int) -> dict[str, object]:
    if simulate_failure and retries_used == 0:
        raise RuntimeError("temporary order service timeout")
    orders = json.loads((FIXTURES_DIR / "orders.json").read_text(encoding="utf-8"))
    for order in orders:
        if order["order_id"] == order_id:
            return order
    raise KeyError(order_id)


def load_policy(reason_code: str) -> dict[str, object]:
    policies = json.loads((FIXTURES_DIR / "policies.json").read_text(encoding="utf-8"))
    if reason_code not in policies:
        raise KeyError(reason_code)
    return policies[reason_code]
