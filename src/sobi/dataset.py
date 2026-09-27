"""Reader and validator for the public sentence-OBI benchmark.

The benchmark archive contains several auxiliary JSON files.  The public
dataset API deliberately reads only the three task JSONL files under
``benchmark_tasks``.  Gold answers are available through an explicit
``iter_gold_tasks`` method and are never included in ``Task.model_input``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any


TASK_FILES: Mapping[str, str] = {
    "T1": "T1_sentence_meaning_order.jsonl",
    "T2": "T2_semantic_slots_qa.jsonl",
    "T3": "T3_order_sensitive.jsonl",
}
EXPECTED_COUNTS: Mapping[str, int] = {"T1": 190, "T2": 350, "T3": 155}
EXPECTED_TOTAL = sum(EXPECTED_COUNTS.values())


class DatasetError(RuntimeError):
    """Base class for malformed or incomplete benchmark data."""


class DataFormatError(DatasetError):
    """Raised when a formal task record does not follow the public schema."""


def _copy_json(value: Any) -> Any:
    """Make an immutable-by-convention copy without adding dependencies."""

    return json.loads(json.dumps(value, ensure_ascii=False))


def _normalise_root(root: str | Path) -> Path:
    path = Path(root).expanduser().resolve()
    if (path / "benchmark_tasks").is_dir():
        return path
    nested = path / "sentence-OBI"
    if (nested / "benchmark_tasks").is_dir():
        return nested
    raise FileNotFoundError(
        f"{path} does not contain benchmark_tasks/; run scripts/download_data.py first"
    )


def _safe_member_path(root: Path, value: str) -> Path:
    """Resolve an archive/schema path below *root* and reject traversal."""

    if not isinstance(value, str) or not value.strip():
        raise DataFormatError("image must be a non-empty string")
    # The source archive uses POSIX separators.  Treat backslashes as
    # separators too, so a malformed record cannot escape on Windows.
    text = value.replace("\\", "/")
    pure = PurePosixPath(text)
    parts = list(pure.parts)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise DataFormatError(f"unsafe image path: {value!r}")
    if parts and parts[0] == "sentence-OBI":
        parts = parts[1:]
    if not parts:
        raise DataFormatError(f"unsafe image path: {value!r}")
    candidate = (root.joinpath(*parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise DataFormatError(f"image escapes dataset root: {value!r}") from exc
    return candidate


def _task_metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return fields useful to a model that do not contain answer material."""

    allowed = (
        "task",
        "subtask",
        "record_id",
        "base_sample_id",
        "image_kind",
        "difficulty",
    )
    return {key: _copy_json(raw[key]) for key in allowed if key in raw}


@dataclass(frozen=True)
class Task:
    """A single model-visible benchmark task.

    ``Task`` intentionally has no answer or gold field.  Call
    :meth:`model_input` when passing a task to a model backend.
    """

    task_id: str
    benchmark: str
    question: str
    options: Any
    image_path: Path
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def model_input(self) -> dict[str, Any]:
        """Return the only payload that an inference backend should receive."""

        return {
            "task_id": self.task_id,
            "benchmark": self.benchmark,
            "question": self.question,
            "options": _copy_json(self.options),
            "image": str(self.image_path),
            "metadata": _copy_json(dict(self.metadata)),
        }


@dataclass(frozen=True)
class GoldTask(Task):
    """A task plus gold data for evaluators; never pass this object to models."""

    gold: Mapping[str, Any] = field(default_factory=dict)


class SOBIDataset:
    """Lazy reader for the 695 formal sentence-OBI tasks."""

    def __init__(self, dataset_root: str | Path):
        self.root = _normalise_root(dataset_root)
        self.task_root = self.root / "benchmark_tasks"

    def _records(
        self, task_types: str | Iterable[str] | None = None
    ) -> Iterator[tuple[str, int, Mapping[str, Any]]]:
        if task_types is None:
            selected = tuple(TASK_FILES)
        elif isinstance(task_types, str):
            selected = (task_types.upper(),)
        else:
            selected = tuple(str(item).upper() for item in task_types)
        unknown = sorted(set(selected) - set(TASK_FILES))
        if unknown:
            raise ValueError(f"unknown task type(s): {', '.join(unknown)}")
        for benchmark in selected:
            path = self.task_root / TASK_FILES[benchmark]
            if not path.is_file():
                raise FileNotFoundError(path)
            with path.open("r", encoding="utf-8-sig") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise DataFormatError(
                            f"invalid JSON in {path}:{line_number}: {exc.msg}"
                        ) from exc
                    if not isinstance(value, dict):
                        raise DataFormatError(
                            f"record in {path}:{line_number} must be an object"
                        )
                    yield benchmark, line_number, value

    def _task_from_record(
        self, benchmark: str, line_number: int, raw: Mapping[str, Any], *, include_gold: bool
    ) -> Task | GoldTask:
        location = f"{benchmark}:{line_number}"
        task_id = raw.get("task_id")
        question = raw.get("question")
        image = raw.get("image")
        if not isinstance(task_id, str) or not task_id:
            raise DataFormatError(f"{location}: task_id must be a non-empty string")
        image_path = _safe_member_path(self.root, image)

        if benchmark == "T1":
            options = raw.get("choices", [])
            if not isinstance(options, list):
                raise DataFormatError(f"{location}: choices must be a list")
        elif benchmark == "T2":
            pairs = raw.get("qa_pairs")
            if not isinstance(pairs, list) or not pairs or not isinstance(pairs[0], dict):
                raise DataFormatError(f"{location}: qa_pairs must contain one object")
            pair = pairs[0]
            pair_question = pair.get("question")
            if isinstance(pair_question, str) and pair_question:
                question = pair_question
            options = {"answer_template": _copy_json(pair.get("answer_template", {}))}
        else:
            choices = raw.get("choices")
            if isinstance(choices, list):
                options = _copy_json(choices)
            else:
                options = {"answer_format": str(raw.get("answer_format", ""))}

        if not isinstance(question, str) or not question:
            raise DataFormatError(f"{location}: question must be a non-empty string")

        base = dict(
            task_id=task_id,
            benchmark=benchmark,
            question=question,
            options=_copy_json(options),
            image_path=image_path,
            metadata=_task_metadata(raw),
        )
        if not include_gold:
            return Task(**base)

        if benchmark == "T1":
            gold = {
                "answer": _copy_json(raw.get("answer")),
                "answer_text": _copy_json(raw.get("answer_text")),
                "gold": _copy_json(raw.get("gold")),
            }
        elif benchmark == "T2":
            pair = raw["qa_pairs"][0]
            gold = {
                "answer": _copy_json(pair.get("answer")),
                "gold": _copy_json(raw.get("gold")),
            }
        else:
            gold = {
                "answer": _copy_json(raw.get("answer")),
                "answer_text": _copy_json(raw.get("answer_text")),
                "gold": _copy_json(raw.get("gold")),
            }
        return GoldTask(**base, gold=gold)

    def iter_tasks(
        self, task_types: str | Iterable[str] | None = None
    ) -> Iterator[Task]:
        """Yield model-visible tasks without gold answers."""

        for benchmark, line_number, raw in self._records(task_types):
            task = self._task_from_record(benchmark, line_number, raw, include_gold=False)
            assert isinstance(task, Task)
            yield task

    def iter_gold_tasks(
        self, task_types: str | Iterable[str] | None = None
    ) -> Iterator[GoldTask]:
        """Yield tasks with gold answers for evaluation and audits only."""

        for benchmark, line_number, raw in self._records(task_types):
            task = self._task_from_record(benchmark, line_number, raw, include_gold=True)
            assert isinstance(task, GoldTask)
            yield task

    def __iter__(self) -> Iterator[Task]:
        return self.iter_tasks()

    def task(self, task_id: str, *, include_gold: bool = False) -> Task | GoldTask:
        """Find one task by stable ID."""

        iterator = self.iter_gold_tasks() if include_gold else self.iter_tasks()
        for task in iterator:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)


@dataclass(frozen=True)
class ValidationReport:
    total_tasks: int
    counts: Mapping[str, int]
    duplicate_task_ids: tuple[str, ...]
    missing_images: tuple[str, ...]
    transforms_missing_images: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def warnings(self) -> tuple[str, ...]:
        if not self.transforms_missing_images:
            return ()
        return (
            f"{len(self.transforms_missing_images)} transforms.jsonl records reference "
            "missing images; these are auxiliary records and do not affect formal tasks",
        )

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total_tasks": self.total_tasks,
            "counts": dict(self.counts),
            "duplicate_task_ids": list(self.duplicate_task_ids),
            "missing_images": list(self.missing_images),
            "transforms_missing_images": list(self.transforms_missing_images),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _transform_image_path(root: Path, value: str) -> Path:
    return _safe_member_path(root, value)


def validate_dataset(
    dataset_root: str | Path,
    *,
    expected_counts: Mapping[str, int] | None = EXPECTED_COUNTS,
) -> ValidationReport:
    """Validate formal task IDs/images and report auxiliary transform warnings."""

    dataset = SOBIDataset(dataset_root)
    counts: dict[str, int] = {key: 0 for key in TASK_FILES}
    seen: set[str] = set()
    duplicates: set[str] = set()
    missing: list[str] = []
    errors: list[str] = []
    try:
        for task in dataset.iter_tasks():
            counts[task.benchmark] += 1
            if task.task_id in seen:
                duplicates.add(task.task_id)
            seen.add(task.task_id)
            if not task.image_path.is_file():
                missing.append(f"{task.task_id}: {task.image_path}")
    except (DatasetError, OSError, KeyError) as exc:
        errors.append(str(exc))

    if duplicates:
        errors.append("duplicate task_id values: " + ", ".join(sorted(duplicates)))
    if missing:
        errors.append(f"{len(missing)} formal task image(s) are missing")
    if expected_counts is not None:
        for benchmark, expected in expected_counts.items():
            actual = counts.get(benchmark, 0)
            if actual != expected:
                errors.append(f"{benchmark} has {actual} tasks; expected {expected}")

    transform_missing: list[str] = []
    transform_path = dataset.root / "transforms.jsonl"
    if transform_path.is_file():
        try:
            with transform_path.open("r", encoding="utf-8-sig") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    image = record.get("image") if isinstance(record, dict) else None
                    if isinstance(image, str):
                        try:
                            image_path = _transform_image_path(dataset.root, image)
                        except DataFormatError:
                            transform_missing.append(f"line {line_number}: {image}")
                        else:
                            if not image_path.is_file():
                                transform_missing.append(f"line {line_number}: {image}")
        except OSError as exc:
            errors.append(f"could not read transforms.jsonl: {exc}")

    return ValidationReport(
        total_tasks=sum(counts.values()),
        counts=counts,
        duplicate_task_ids=tuple(sorted(duplicates)),
        missing_images=tuple(missing),
        transforms_missing_images=tuple(transform_missing),
        errors=tuple(errors),
    )
