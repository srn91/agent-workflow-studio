from __future__ import annotations

import app.cli as cli


def test_demo_cli_prints_timing_summary(capsys) -> None:
    cli.demo()

    output = capsys.readouterr().out
    assert "total_duration_ms=" in output
    assert "slowest_step=" in output
    assert "trace_path=generated/workflow_trace.jsonl" in output
