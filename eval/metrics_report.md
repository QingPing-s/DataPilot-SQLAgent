# DataPilot Spider Benchmark Report

## Evaluation Scope

- Dataset: Spider Dev subset
- Cases: 50
- Database schemas: 10
- Sampling: first 5 cases from each of 10 database schemas
- Model path: SQL Planner + SQL Generator + SQL Executor + Answer Analyst + Judge
- Fallback cases: 0
- Skipped cases: 0

This is an initial engineering benchmark, not a full Spider leaderboard submission.

## Main Results

| Metric | Result |
| --- | ---: |
| SQL Valid Rate | 100% |
| Value-based Execution Accuracy | 92% |
| Strict Column-and-Row Match | 20% |
| Exact Match Rate | 20% |
| Average Retry Count | 0.00 |
| Fallback Rate | 0% |
| Average Latency | 6.91 seconds |
| Average Judge Score | 5.00 / 5 |
| Judge Hallucination Rate | 0% |

Value-based Execution Accuracy compares result values while ignoring column aliases and equivalent column permutations. Row order is ignored only when the gold SQL has no `ORDER BY`.

Strict Column-and-Row Match is retained as a diagnostic metric. It is substantially lower because equivalent SQL often uses different aggregate aliases or projection order.

## Repair Comparison

### Natural Cases

All 50 generated SQL statements were executable, so the natural workflow did not enter the repair node.

| Version | SQL Valid Rate | Execution Accuracy |
| --- | ---: | ---: |
| Initial SQL without repair | 100% | 92% |
| Full workflow with repair enabled | 100% | 92% |
| Delta | 0 percentage points | 0 percentage points |

Natural Repair Success Rate is therefore **N/A**. Reporting it as 0% would incorrectly imply attempted repairs failed.

### Controlled Fault-Injection Stress Test

- Cases: 20 across 10 databases
- Missing-table faults: 10
- Syntax faults: 10
- Maximum repair attempts: 2

| Metric | Before Repair | After Repair | Delta |
| --- | ---: | ---: | ---: |
| Executable SQL | 0% | 100% | +100 pp |
| Correct execution result | 0% | 100% | +100 pp |
| Average attempts | - | 1.00 | - |

This stress test measures recovery from known execution failures. It does not prove that repair improves semantically incorrect but executable SQL.

## Failed Cases

Four cases failed value-based execution comparison:

| Case | Failure |
| --- | --- |
| `spider_017` | String literal casing differed: `Jetblue Airways` vs stored `JetBlue Airways`. |
| `spider_019` | Same case-sensitive entity-value mismatch. |
| `spider_023` | Generated SQL returned an additional age column instead of names only. |
| `spider_048` | Generated SQL followed the question and returned `result`, while the gold SQL omitted that requested column. |

The last case indicates a possible question/gold inconsistency and should be reviewed separately rather than treated as an unambiguous model failure.

## RRF and Rerank

RRF and reranking comparisons are not applicable. The current system injects the full SQLite schema into the prompt and does not use vector retrieval, RAG, RRF, or a reranker.

## Reliability and Limitations

- The sample contains 50 cases, not the full Spider Dev split.
- Sampling is schema-balanced but not randomized or difficulty-stratified.
- Execution comparison is project-defined rather than the official Spider test-suite evaluator.
- Query results are capped at 100 rows.
- Results come from one model run at temperature 0.2.
- The Judge uses the same model family and produced uniformly high scores, so Judge metrics should be treated as auxiliary rather than objective.
- A larger evaluation should use the complete Dev split, official hardness labels or evaluator, repeated runs, latency and token accounting, and confidence intervals.
