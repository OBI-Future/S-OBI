"""CLI for validating the formal task files and their image references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import validate_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a local sentence-OBI dataset")
    parser.add_argument("--dataset-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_dataset(args.dataset_root)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
