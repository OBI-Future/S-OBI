#!/usr/bin/env python3
"""Run a user-supplied backend over S-OBI and write predictions as JSONL.

Backend plugins have the form ``module:function`` and receive one dictionary
from ``Task.model_input()``.  That dictionary contains no gold answer.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from sobi import SOBIDataset


def _load_backend(spec: str) -> Callable[[Mapping[str, Any]], Any]:
    if ":" not in spec:
        raise ValueError("backend must be written as module:function")
    module_name, function_name = spec.split(":", 1)
    if not module_name or not function_name:
        raise ValueError("backend must be written as module:function")
    module = importlib.import_module(module_name)
    backend = getattr(module, function_name, None)
    if not callable(backend):
        raise TypeError(f"backend {spec!r} is not callable")
    return backend


def _read_resume_ids(path: Path, valid_ids: set[str]) -> set[str]:
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON in {path}:{line_number}") from exc
            if not isinstance(row, dict) or not isinstance(row.get("task_id"), str):
                raise ValueError(f"{path}:{line_number} must contain a task_id")
            if "prediction" not in row:
                raise ValueError(f"{path}:{line_number} must contain a prediction")
            task_id = row["task_id"]
            if task_id in seen:
                raise ValueError(f"duplicate task_id in existing predictions: {task_id}")
            if task_id not in valid_ids:
                raise ValueError(
                    f"prediction task_id {task_id!r} is not in this dataset "
                    "(possible cross-dataset resume)"
                )
            seen.add(task_id)
    return seen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an S-OBI inference backend")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--backend", help="backend plugin as module:function")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="use examples.mock_backend:predict (smoke-only; not a baseline)",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", choices=("T1", "T2", "T3"), action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mock and args.backend:
        raise SystemExit("choose either --backend or --mock")
    if not args.mock and not args.backend:
        raise SystemExit("provide --backend module:function or --mock")
    if args.limit is not None and args.limit < 0:
        raise SystemExit("--limit must be non-negative")
    if args.resume and args.overwrite:
        raise SystemExit("--resume and --overwrite cannot be combined")
    backend = _load_backend("examples.mock_backend:predict" if args.mock else args.backend)
    dataset = SOBIDataset(args.dataset_root)
    tasks = list(dataset.iter_tasks(args.task))
    valid_ids = {task.task_id for task in tasks}
    if len(valid_ids) != len(tasks):
        raise SystemExit("dataset contains duplicate task IDs; validate it before inference")

    existing: set[str] = set()
    if args.output.exists():
        if not args.resume and not args.overwrite:
            raise SystemExit(
                f"{args.output} exists; pass --resume or --overwrite explicitly"
            )
        if args.resume:
            try:
                existing = _read_resume_ids(args.output, valid_ids)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            with args.output.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                has_trailing_newline = True
                if size:
                    stream.seek(-1, 2)
                    has_trailing_newline = stream.read(1) == b"\n"
                if size and not has_trailing_newline:
                    with args.output.open("ab") as append_stream:
                        append_stream.write(b"\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"
    pending = [task for task in tasks if task.task_id not in existing]
    if args.limit is not None:
        pending = pending[: args.limit]
    with args.output.open(mode, encoding="utf-8") as stream:
        for task in pending:
            # Only this sanitized payload is exposed to the backend.
            prediction = backend(task.model_input())
            row = {"task_id": task.task_id, "prediction": prediction}
            try:
                encoded = json.dumps(row, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                raise TypeError(f"backend returned a non-JSON value for {task.task_id}") from exc
            stream.write(encoded + "\n")
            stream.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
