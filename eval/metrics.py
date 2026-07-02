from __future__ import annotations


def compute_sql_valid_rate(results: list[dict]) -> float:
    return _mean_bool(result.get("sql_valid") for result in _evaluated(results))


def compute_execution_accuracy(results: list[dict]) -> float:
    return _mean_bool(result.get("execution_correct") for result in _evaluated(results))


def compute_exact_match_rate(results: list[dict]) -> float:
    return _mean_bool(result.get("exact_match") for result in _evaluated(results))


def compute_repair_success_rate(results: list[dict]) -> float:
    repaired_results = [
        result
        for result in results
        if not result.get("skipped")
        if result.get("repaired") is True or int(result.get("retry_count") or 0) > 0
    ]
    if not repaired_results:
        return 0.0
    return _mean_bool(result.get("sql_valid") or result.get("execution_correct") for result in repaired_results)


def compute_average_retry_count(results: list[dict]) -> float:
    evaluated = _evaluated(results)
    if not evaluated:
        return 0.0
    return sum(int(result.get("retry_count") or 0) for result in evaluated) / len(evaluated)


def compute_average_judge_score(results: list[dict]) -> float:
    scores = []
    for result in results:
        judge_result = result.get("judge_result")
        if isinstance(judge_result, dict) and judge_result.get("overall_judge_score") is not None:
            scores.append(float(judge_result["overall_judge_score"]))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def compute_hallucination_rate(results: list[dict]) -> float:
    hallucination_flags = []
    for result in results:
        judge_result = result.get("judge_result")
        if isinstance(judge_result, dict) and judge_result.get("has_hallucination") is not None:
            hallucination_flags.append(bool(judge_result["has_hallucination"]))
    if not hallucination_flags:
        return 0.0
    return sum(hallucination_flags) / len(hallucination_flags)


def summarize_metrics(results: list[dict]) -> dict:
    evaluated = _evaluated(results)
    return {
        "total_cases": len(results),
        "evaluated_cases": len(evaluated),
        "skipped_cases": len(results) - len(evaluated),
        "sql_valid_rate": compute_sql_valid_rate(results),
        "execution_accuracy": compute_execution_accuracy(results),
        "exact_match_rate": compute_exact_match_rate(results),
        "repair_success_rate": compute_repair_success_rate(results),
        "average_retry_count": compute_average_retry_count(results),
        "average_judge_score": compute_average_judge_score(results),
        "hallucination_rate": compute_hallucination_rate(results),
    }


def exact_match(predicted_sql: str, expected_sql: str) -> bool:
    return _normalize_sql(predicted_sql) == _normalize_sql(expected_sql)


def accuracy(matches: list[bool]) -> float:
    if not matches:
        return 0.0
    return sum(matches) / len(matches)


def _mean_bool(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(bool(value) for value in values) / len(values)


def _evaluated(results: list[dict]) -> list[dict]:
    return [result for result in results if not result.get("skipped")]


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").lower().split())
