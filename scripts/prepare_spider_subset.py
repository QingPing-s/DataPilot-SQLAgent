from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def prepare_spider_subset(
    spider_root: str,
    split: str = "dev",
    limit: int = 50,
    output_dir: str = "data/spider_subset",
) -> dict[str, object]:
    spider_root_path = Path(spider_root)
    output_path = Path(output_dir)
    databases_output_path = output_path / "databases"
    eval_cases_path = output_path / "eval_cases.json"

    split_path = _get_split_path(spider_root_path, split)
    if not split_path.exists():
        raise FileNotFoundError(f"Spider split file not found: {split_path}")

    samples = json.loads(split_path.read_text(encoding="utf-8-sig"))
    output_path.mkdir(parents=True, exist_ok=True)
    databases_output_path.mkdir(parents=True, exist_ok=True)

    cases = []
    copied_db_ids = set()

    for sample in samples:
        if len(cases) >= limit:
            break

        db_id = sample.get("db_id")
        question = sample.get("question")
        gold_sql = sample.get("query")
        if not db_id or not question or not gold_sql:
            print(f"Warning: skipping malformed Spider sample: {sample}")
            continue

        source_db_dir = spider_root_path / "database" / db_id
        source_sqlite = source_db_dir / f"{db_id}.sqlite"
        if not source_db_dir.exists() or not source_sqlite.exists():
            print(f"Warning: database not found for db_id={db_id}: {source_db_dir}")
            continue

        target_db_dir = databases_output_path / db_id
        target_sqlite = target_db_dir / f"{db_id}.sqlite"
        if db_id not in copied_db_ids:
            if target_db_dir.exists():
                shutil.rmtree(target_db_dir)
            shutil.copytree(source_db_dir, target_db_dir)
            copied_db_ids.add(db_id)

        cases.append(
            {
                "case_id": f"spider_{len(cases) + 1:03d}",
                "db_id": db_id,
                "db_path": str(target_sqlite.as_posix()),
                "question": question,
                "gold_sql": gold_sql,
                "difficulty": None,
            }
        )

    eval_cases_path.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "case_count": len(cases),
        "database_count": len(copied_db_ids),
        "eval_cases_path": eval_cases_path,
    }


def _get_split_path(spider_root: Path, split: str) -> Path:
    if split == "dev":
        return spider_root / "dev.json"
    if split == "train":
        return spider_root / "train_spider.json"
    raise ValueError("--split must be either 'train' or 'dev'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a local Spider subset for DataPilot evaluation.")
    parser.add_argument("--spider-root", required=True, help="Path to local Spider dataset root.")
    parser.add_argument("--split", choices=["train", "dev"], default="dev", help="Spider split to sample.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of cases to extract.")
    parser.add_argument("--output-dir", default="data/spider_subset", help="Output directory.")
    args = parser.parse_args()

    result = prepare_spider_subset(
        spider_root=args.spider_root,
        split=args.split,
        limit=args.limit,
        output_dir=args.output_dir,
    )

    print(f"Generated cases: {result['case_count']}")
    print(f"Copied databases: {result['database_count']}")
    print(f"eval_cases.json: {result['eval_cases_path']}")


if __name__ == "__main__":
    main()
