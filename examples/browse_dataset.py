#!/usr/bin/env python3
"""Print a few model-visible tasks as JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sobi import SOBIDataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Browse model-visible S-OBI tasks")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--task", choices=("T1", "T2", "T3"), action="append")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must be non-negative")
    for index, task in enumerate(SOBIDataset(args.dataset_root).iter_tasks(args.task)):
        if index >= args.limit:
            break
        print(json.dumps(task.model_input(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
