from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.metrics import summarize_metrics
from src.graph import run_datapilot
from src.sql_verifier import verify_sql_against_gold


def run_eval(
    cases_path: str = "data/spider_subset/eval_cases.json",
    limit: int = 50,
    output_dir: str = "eval",
) -> dict[str, Any]:
    cases = _load_cases(cases_path)[:limit]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    for case in cases:
        results.append(_run_single_case(case))

    metrics = summarize_metrics(results)
    payload = {
        "cases_path": cases_path,
        "limit": limit,
        "metrics": metrics,
        "results": results,
    }

    results_path = output_path / "eval_results.json"
    report_path = output_path / "metrics_report.md"
    results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(_build_metrics_report(results, metrics), encoding="utf-8")

    return {
        "metrics": metrics,
        "results": results,
        "eval_results_path": str(results_path),
        "metrics_report_path": str(report_path),
    }


def _run_single_case(case: dict[str, Any]) -> dict[str, Any]:
    base_result = {
        "case_id": case.get("case_id", ""),
        "db_id": case.get("db_id", ""),
        "difficulty": case.get("difficulty"),
        "question": case.get("question", ""),
        "generated_sql": "",
        "gold_sql": case.get("gold_sql", ""),
        "sql_valid": False,
        "execution_correct": False,
        "exact_match": False,
        "repaired": False,
        "retry_count": 0,
        "fallback_used": False,
        "error": None,
        "judge_result": None,
        "skipped": False,
        "status": "pending",
    }

    db_path = case.get("db_path", "")
    if not db_path or not Path(db_path).exists():
        base_result["error"] = f"Database not found: {db_path}"
        base_result["skipped"] = True
        base_result["status"] = "skipped"
        return base_result

    try:
        state = run_datapilot(
            {
                "question": case.get("question", ""),
                "db_path": db_path,
                "db_id": case.get("db_id"),
                "gold_sql": case.get("gold_sql"),
                "retry_count": 0,
                "fallback_used": False,
                "trace": [],
            }
        )
        generated_sql = state.get("generated_sql", "")
        verification = verify_sql_against_gold(db_path, generated_sql, case.get("gold_sql", ""))

        base_result.update(
            {
                "generated_sql": generated_sql,
                "sql_valid": verification.get("sql_valid", False),
                "execution_correct": verification.get("execution_correct", False),
                "exact_match": verification.get("exact_match", False),
                "repaired": bool(state.get("repaired_sql")),
                "retry_count": int(state.get("retry_count") or 0),
                "fallback_used": bool(state.get("fallback_used")),
                "error": verification.get("error") or state.get("error"),
                "judge_result": state.get("judge_result"),
                "status": "completed" if not verification.get("error") else "failed",
            }
        )
    except Exception as exc:
        base_result["error"] = str(exc)
        base_result["status"] = "failed"

    return base_result


def _build_metrics_report(results: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    lines = ["# DataPilot Offline Evaluation Report", ""]

    lines.extend(["## Overall Metrics", ""])
    metric_labels = {
        "total_cases": "Total Cases",
        "sql_valid_rate": "SQL Valid Rate",
        "execution_accuracy": "Execution Accuracy",
        "exact_match_rate": "Exact Match Rate",
        "repair_success_rate": "Repair Success Rate",
        "average_retry_count": "Average Retry Count",
        "average_judge_score": "Average Judge Score",
        "hallucination_rate": "Hallucination Rate",
    }
    for key, label in metric_labels.items():
        lines.append(f"- {label}: {_format_metric(metrics.get(key))}")
    lines.append("")

    lines.extend(["## Difficulty Breakdown", ""])
    breakdown = _difficulty_breakdown(results)
    if breakdown:
        lines.extend(["| Difficulty | Cases | SQL Valid Rate | Execution Accuracy | Exact Match Rate |", "| --- | ---: | ---: | ---: | ---: |"])
        for difficulty, summary in breakdown.items():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(difficulty),
                        str(summary["total_cases"]),
                        _format_metric(summary["sql_valid_rate"]),
                        _format_metric(summary["execution_accuracy"]),
                        _format_metric(summary["exact_match_rate"]),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No difficulty labels available.")
    lines.append("")

    lines.extend(["## Failed Cases", ""])
    failed_cases = [result for result in results if result.get("error") or not result.get("execution_correct")]
    if failed_cases:
        for result in failed_cases:
            lines.append(
                f"- `{result.get('case_id')}` execution_correct={result.get('execution_correct')} "
                f"fallback_used={result.get('fallback_used')} error={result.get('error') or 'None'}"
            )
    else:
        lines.append("No failed cases.")
    lines.append("")

    lines.extend(["## Judge Metrics", ""])
    lines.append(f"- Average Judge Score: {_format_metric(metrics.get('average_judge_score'))}")
    lines.append(f"- Hallucination Rate: {_format_metric(metrics.get('hallucination_rate'))}")
    judged_count = sum(1 for result in results if isinstance(result.get("judge_result"), dict))
    lines.append(f"- Judged Cases: {judged_count}")
    lines.append("")

    lines.extend(["## Case Results", ""])
    if results:
        lines.extend(
            [
                "| Case | Difficulty | SQL Valid | Execution Correct | Exact Match | Repaired | Retries | Fallback Used |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for result in results:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(result.get("case_id")),
                        str(result.get("difficulty") or "unknown"),
                        str(result.get("sql_valid")),
                        str(result.get("execution_correct")),
                        str(result.get("exact_match")),
                        str(result.get("repaired")),
                        str(result.get("retry_count")),
                        str(result.get("fallback_used")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("No cases evaluated.")

    return "\n".join(lines) + "\n"


def _difficulty_breakdown(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        difficulty = result.get("difficulty") or "unknown"
        grouped.setdefault(difficulty, []).append(result)
    return {difficulty: summarize_metrics(items) for difficulty, items in grouped.items()}


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _load_cases(cases_path: str) -> list[dict[str, Any]]:
    path = Path(cases_path)
    if not path.exists():
        raise FileNotFoundError(f"Eval cases file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise ValueError("Eval cases file must contain a JSON list")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DataPilot Spider-style offline evaluation.")
    parser.add_argument("--cases", default="data/spider_subset/eval_cases.json", help="Path to eval_cases.json.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of cases to evaluate.")
    args = parser.parse_args()

    result = run_eval(cases_path=args.cases, limit=args.limit)
    print("Evaluation complete.")
    print(f"eval_results.json: {result['eval_results_path']}")
    print(f"metrics_report.md: {result['metrics_report_path']}")
    print("Overall metrics:")
    for key, value in result["metrics"].items():
        print(f"- {key}: {_format_metric(value)}")


if __name__ == "__main__":
    main()
