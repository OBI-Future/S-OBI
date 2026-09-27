"""CLI implementation for printing model-visible sentence-OBI tasks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import SOBIDataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect model-visible S-OBI tasks")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--task", choices=("T1", "T2", "T3"), action="append")
    parser.add_argument("--limit", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.limit < 0:
        raise SystemExit("--limit must be non-negative")
    dataset = SOBIDataset(args.dataset_root)
    for index, task in enumerate(dataset.iter_tasks(args.task)):
        if index >= args.limit:
            break
        print(json.dumps(task.model_input(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
