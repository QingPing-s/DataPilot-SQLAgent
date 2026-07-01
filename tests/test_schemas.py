from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas import (
    DatabaseSchema,
    EvalCase,
    EvalResult,
    FinalAnswer,
    GeneratedSQL,
    JudgeResult,
    SQLExecutionResult,
    SQLPlan,
    SQLRepairResult,
    TableSchema,
)


def test_schema_models_can_be_instantiated():
    table = TableSchema(
        table_name="customers",
        columns=[{"name": "customer_id", "type": "TEXT"}],
        primary_keys=["customer_id"],
        foreign_keys=[],
        sample_rows=[{"customer_id": "ALFKI"}],
    )
    database = DatabaseSchema(db_path="data/northwind/northwind.db", tables=[table])
    plan = SQLPlan(
        question="Which customers generated the most revenue?",
        relevant_tables=["customers", "orders", "order_details"],
        relevant_columns=["customer_id", "unit_price", "quantity"],
        join_keys=["customers.customer_id = orders.customer_id"],
        filters=[],
        aggregations=["SUM(unit_price * quantity)"],
        order_by=["revenue DESC"],
        limit=10,
        reasoning="Join orders and order details by customer.",
    )
    generated_sql = GeneratedSQL(sql="SELECT 1", explanation="Demo SQL.")
    execution = SQLExecutionResult(
        success=True,
        sql="SELECT 1",
        columns=["value"],
        rows=[{"value": 1}],
        row_count=1,
    )
    repair = SQLRepairResult(repaired_sql="SELECT 1", repair_reason="No repair needed.")
    answer = FinalAnswer(
        question="Demo?",
        sql="SELECT 1",
        answer="The value is 1.",
        key_insights=["Single row returned."],
    )
    judge = JudgeResult(
        question_sql_alignment=5,
        answer_faithfulness=5,
        explanation_quality=4,
        result_usefulness=4,
        error_analysis_quality=3,
        has_hallucination=False,
        issues=[],
        overall_judge_score=4.5,
        judge_reason="Good result.",
    )
    case = EvalCase(
        case_id="case_001",
        db_id="northwind",
        db_path="data/northwind/northwind.db",
        question="Demo?",
        gold_sql="SELECT 1",
    )
    result = EvalResult(
        case_id="case_001",
        question="Demo?",
        generated_sql="SELECT 1",
        gold_sql="SELECT 1",
        sql_valid=True,
        execution_correct=True,
        exact_match=True,
        repaired=False,
        retry_count=0,
        judge_result=judge,
    )

    assert database.tables[0].table_name == "customers"
    assert plan.limit == 10
    assert generated_sql.sql == "SELECT 1"
    assert execution.row_count == 1
    assert repair.repaired_sql == "SELECT 1"
    assert answer.key_insights == ["Single row returned."]
    assert case.difficulty is None
    assert result.judge_result == judge


def test_judge_score_range_validation():
    with pytest.raises(ValidationError):
        JudgeResult(
            question_sql_alignment=0,
            answer_faithfulness=5,
            explanation_quality=5,
            result_usefulness=5,
            error_analysis_quality=5,
            has_hallucination=False,
            overall_judge_score=5,
            judge_reason="Invalid score.",
        )


def test_row_count_must_be_non_negative():
    with pytest.raises(ValidationError):
        SQLExecutionResult(
            success=True,
            sql="SELECT 1",
            columns=[],
            rows=[],
            row_count=-1,
        )
