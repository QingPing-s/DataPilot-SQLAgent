from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from src.graph import run_datapilot
from src.report import save_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DataPilot SQL Agent.")
    parser.add_argument("--db-path", required=True, help="Path to SQLite database.")
    parser.add_argument("--question", required=True, help="Natural language data question.")
    parser.add_argument("--db-id", default=None, help="Optional database identifier.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for output files.")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print("Database not found. If you want to run the Northwind demo, please run:")
        print("python scripts/create_northwind_db.py")
        print("python scripts/check_databases.py")
        return

    output_dir = Path(args.output_dir)
    trace_dir = Path("traces")
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set. Running with local fallback SQL generation where needed.")

    initial_state: dict[str, Any] = {
        "question": args.question,
        "db_path": str(db_path),
        "db_id": args.db_id,
        "retry_count": 0,
        "fallback_used": False,
        "trace": [],
    }

    state = initial_state
    try:
        state = run_datapilot(initial_state)
    except Exception as exc:
        state["error"] = str(exc)
        state.setdefault("trace", []).append(
            {
                "node": "main",
                "status": "error",
                "message": str(exc),
                "payload": {},
            }
        )

    paths = _save_outputs(state, output_dir, trace_dir)
    _print_summary(state, paths)


def _save_outputs(state: dict[str, Any], output_dir: Path, trace_dir: Path) -> dict[str, Path]:
    generated_sql_path = output_dir / "generated_sql.sql"
    query_result_path = output_dir / "query_result.json"
    answer_path = output_dir / "answer.md"
    report_path = output_dir / "analysis_report.md"
    trace_path = trace_dir / "latest_trace.json"

    generated_sql_path.write_text(state.get("generated_sql", ""), encoding="utf-8")
    query_result_path.write_text(
        json.dumps(state.get("execution_result", {}), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    final_answer = state.get("final_answer", {})
    if isinstance(final_answer, dict):
        answer_text = final_answer.get("answer", "")
        insights = final_answer.get("key_insights") or []
        if insights:
            answer_text += "\n\n## Key Insights\n\n" + "\n".join(f"- {item}" for item in insights)
    else:
        answer_text = str(final_answer)
    answer_path.write_text(answer_text, encoding="utf-8")

    report = state.get("final_report") or ""
    save_report(report, str(report_path))

    trace_path.write_text(
        json.dumps(state.get("trace", []), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "generated_sql": generated_sql_path,
        "query_result": query_result_path,
        "answer": answer_path,
        "analysis_report": report_path,
        "trace": trace_path,
    }


def _print_summary(state: dict[str, Any], paths: dict[str, Path]) -> None:
    execution_result = state.get("execution_result", {})
    print("Generated SQL:")
    print(state.get("generated_sql", ""))
    print("")
    print(f"Success: {execution_result.get('success')}")
    if execution_result.get("error") or state.get("error"):
        print(f"Error: {execution_result.get('error') or state.get('error')}")
    print("")
    print("Output paths:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
