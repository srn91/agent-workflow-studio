from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT_DIR / "fixtures"
GENERATED_DIR = ROOT_DIR / "generated"
TRACE_PATH = GENERATED_DIR / "workflow_trace.jsonl"
SUMMARY_PATH = GENERATED_DIR / "workflow_summary.json"
DB_PATH = GENERATED_DIR / "workflow_runs.sqlite3"
