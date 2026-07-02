# DataPilot Multi-Agent SQL Analyst

[简体中文](README.zh-CN.md) | **English**

DataPilot is a multi-agent Text-to-SQL analytics system built with LangGraph, DeepSeek API, and SQLite. It converts natural-language questions into executable SQL, repairs failed queries, explains results, evaluates response quality, and records the complete agent trace.

**Live demo:** [datapilot-sql-agent.gentlefield-019d4ae8.eastasia.azurecontainerapps.io](https://datapilot-sql-agent.gentlefield-019d4ae8.eastasia.azurecontainerapps.io/)

## System Architecture
![DataPilot-SQLAgent 系统架构图](docs/images/DataPilot.png)

## Features

- Natural-language to SQLite SQL
- Automatic schema discovery with sample rows and relationships
- SQL planning and generation with Pydantic validation
- Read-only SQL execution with unsafe-statement rejection
- LangGraph conditional self-repair loop with a two-retry limit
- Result-grounded answer generation
- LLM-as-a-Judge quality assessment
- Spider-style offline evaluation
- JSON trace logging and Markdown reports
- React + Vite analysis workspace
- Local fallback SQL generation when no API key is configured

## Workflow

```text
User Question
  -> Schema Agent
  -> SQL Planner
  -> SQL Generator
  -> SQL Executor
  -> SQL Debugger (on failure, max 2 retries)
  -> Answer Analyst
  -> Judge Agent
  -> Report Generator
```

## Tech Stack

- Python 3.10+
- LangGraph
- DeepSeek API through the OpenAI SDK
- FastAPI and Gunicorn
- SQLite and pandas
- Pydantic
- React and Vite
- pytest
- Docker
- Azure Container Apps and Azure Container Registry

## Project Structure

```text
data/       Northwind demo database and Spider subset
eval/       Offline evaluation runner and metrics
frontend/   React + Vite workspace
scripts/    Database creation, validation, and dataset preparation
src/        Agent graph, API, SQL tools, prompts, judge, and reports
tests/      Unit and integration tests
```

## Environment

Create `.env` from `.env.example`:

```env
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

The API key is read only by the Python backend. It is excluded from Git and is never embedded in the frontend. Without a key, the Northwind demo uses the local fallback generator.

## Local Setup

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python scripts/create_northwind_db.py
python scripts/check_databases.py
```

Run the command-line demo:

```bash
python -m src.main --db-path data/northwind/northwind.db --question "Which product categories have the highest sales?"
```

Run the API and frontend during development:

```bash
# Terminal 1
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to the Python API. A production Docker build serves the compiled frontend and API from one origin.

## Spider Evaluation

Spider is not downloaded automatically. Prepare a local subset:

```bash
python scripts/prepare_spider_subset.py --spider-root /path/to/spider --split dev --limit 50
```

Run the evaluation:

```bash
python eval/run_eval.py --cases data/spider_subset/eval_cases.json --limit 50
```

Cases with missing SQLite files are recorded as failures without stopping the full evaluation.

Objective metrics include SQL Valid Rate, Execution Accuracy, Exact Match Rate, Repair Success Rate, and Average Retry Count. Judge metrics include Question-SQL Alignment, Answer Faithfulness, Explanation Quality, Hallucination Rate, and Overall Judge Score.

### Initial Benchmark

On a 50-case Spider Dev subset covering 10 database schemas:

- SQL Valid Rate: **100%**
- Value-based Execution Accuracy: **92%**
- Exact Match Rate: **20%**
- Fallback Rate: **0%**
- Average latency: **6.91 seconds per case**

No naturally generated SQL failed to execute, so natural Repair Success Rate is **N/A** rather than 0%. A separate deterministic repair stress test injected 10 missing-table errors and 10 syntax errors; **20/20 recovered the correct result within one repair attempt**.

See [the benchmark report](eval/metrics_report.md) for methodology, failure analysis, comparison details, and limitations. This is an engineering benchmark, not a full Spider leaderboard result.

## Tests

```bash
pytest
cd frontend
npm run build
```

## Docker

```bash
docker build -t datapilot-sql-agent .
docker run --rm -p 8000:8000 --env-file .env datapilot-sql-agent
```

Open `http://127.0.0.1:8000`.

## Outputs

- `outputs/generated_sql.sql`
- `outputs/query_result.json`
- `outputs/answer.md`
- `outputs/analysis_report.md`
- `traces/latest_trace.json`
- `eval/eval_results.json`
- `eval/metrics_report.md`

## Engineering Highlights

- Implements an execution-grounded SQL Agent loop instead of stopping at SQL generation.
- Restricts database access to read-only `SELECT` and `WITH` statements.
- Uses explicit graph routing and bounded retries to prevent repair loops.
- Combines objective execution metrics with LLM-as-a-Judge evaluation.
- Supports local Northwind demos, Spider evaluation, trace replay, and container deployment.

## License

This repository is intended for learning, portfolio demonstration, and technical evaluation.
