from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.graph import run_datapilot
from src.llm_client import DEFAULT_MODEL_NAME
from src.schema_reader import get_connection, read_database_schema


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = "data/northwind/northwind.db"
EVAL_RESULTS_PATH = PROJECT_ROOT / "eval" / "eval_results.json"
FRONTEND_DIST_PATH = PROJECT_ROOT / "frontend" / "dist"

allowed_origins = [
    "http://127.0.0.1:5190",
    "http://localhost:5190",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
if os.getenv("FRONTEND_ORIGIN"):
    allowed_origins.append(os.environ["FRONTEND_ORIGIN"].rstrip("/"))

app = FastAPI(title="DataPilot SQL Agent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    question: str = Field(min_length=1, description="Natural-language data question.")
    db_path: str = Field(default=DEFAULT_DB_PATH, description="SQLite database path.")
    db_id: str | None = Field(default="northwind", description="Optional database identifier.")


def _resolve_db_path(db_path: str) -> Path:
    path = Path(db_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@app.get("/api/health")
def health() -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    return {
        "status": "ok",
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "model_name": os.getenv("MODEL_NAME", DEFAULT_MODEL_NAME),
        "database_exists": _resolve_db_path(DEFAULT_DB_PATH).is_file(),
    }


@app.get("/api/database-info")
def database_info(db_path: str = DEFAULT_DB_PATH) -> dict[str, Any]:
    resolved_path = _resolve_db_path(db_path)
    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail=f"Database not found: {db_path}")

    try:
        schema = read_database_schema(str(resolved_path), sample_limit=2)
        row_counts: dict[str, int] = {}
        with get_connection(str(resolved_path)) as connection:
            for table_schema in schema["tables"]:
                table = table_schema["table_name"]
                quoted_table = '"' + table.replace('"', '""') + '"'
                row_counts[table] = connection.execute(
                    f"SELECT COUNT(*) FROM {quoted_table}"
                ).fetchone()[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to inspect database: {exc}") from exc

    return {
        "db_id": "northwind",
        "db_path": db_path,
        "database_type": "SQLite",
        "tables": [
            {
                "table_name": table["table_name"],
                "row_count": row_counts[table["table_name"]],
                "columns": table["columns"],
                "primary_keys": table["primary_keys"],
                "foreign_keys": table["foreign_keys"],
                "sample_rows": table["sample_rows"],
            }
            for table in schema["tables"]
        ],
        "table_count": len(schema["tables"]),
        "row_counts": row_counts,
    }


@app.get("/api/evaluation")
def evaluation() -> dict[str, Any]:
    if not EVAL_RESULTS_PATH.is_file():
        return {
            "available": False,
            "message": "尚未找到评测结果，请先运行 eval/run_eval.py。",
            "metrics": None,
            "total_cases": 0,
            "completed_cases": 0,
            "failed_cases": [],
        }

    try:
        payload = json.loads(EVAL_RESULTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read evaluation results: {exc}") from exc

    results = payload.get("results", [])
    completed_results = [result for result in results if not result.get("error")]
    failed_cases = [
        {
            "case_id": result.get("case_id"),
            "question": result.get("question"),
            "error": result.get("error"),
        }
        for result in results
        if result.get("error")
    ]
    available = bool(completed_results)
    return {
        "available": available,
        "message": (
            "评测结果已加载。"
            if available
            else "没有成功完成的评测 Case，请准备 Spider 数据库后重新运行评测。"
        ),
        "metrics": payload.get("metrics") if available else None,
        "benchmark": payload.get("benchmark") if available else None,
        "total_cases": len(results),
        "completed_cases": len(completed_results),
        "failed_cases": failed_cases[:20],
    }


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    resolved_path = _resolve_db_path(request.db_path)
    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail=f"Database not found: {request.db_path}")

    initial_state = {
        "question": question,
        "db_path": str(resolved_path),
        "db_id": request.db_id,
        "retry_count": 0,
        "fallback_used": False,
        "trace": [],
    }
    try:
        state = run_datapilot(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DataPilot execution failed: {exc}") from exc

    return {
        "sql_plan": state.get("sql_plan", {}),
        "generated_sql": state.get("generated_sql", ""),
        "sql_explanation": state.get("sql_explanation", ""),
        "execution_result": state.get("execution_result", {}),
        "final_answer": state.get("final_answer", {}),
        "judge_result": state.get("judge_result", {}),
        "trace": state.get("trace", []),
        "fallback_used": bool(state.get("fallback_used", False)),
        "retry_count": state.get("retry_count", 0),
        "error": state.get("error"),
    }


if FRONTEND_DIST_PATH.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_PATH, html=True), name="frontend")
