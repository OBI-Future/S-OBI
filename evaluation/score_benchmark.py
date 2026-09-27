#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "sentence-OBI"
DEFAULT_TASK_DIR = DEFAULT_DATASET_ROOT / "benchmark_tasks"
DEFAULT_RUNTIME_DIR = REPO_ROOT / ".runtime" / "evaluation"
DEFAULT_TEMPLATE_PATH = DEFAULT_RUNTIME_DIR / "prediction_template.jsonl"
DEFAULT_OUTPUT_DIR = DEFAULT_RUNTIME_DIR / "results"
TASK_FILES = [
    "T1_sentence_meaning_order.jsonl",
    "T2_semantic_slots_qa.jsonl",
    "T3_order_sensitive.jsonl",
]
ID_KEYS = ("task_id", "id")
PREDICTION_KEYS = ("prediction", "pred", "output", "response", "answer")

PUNCT = "，。！？；：、,.!?;: 「」『』“”\"'（）()[]【】<>《》 \t\r\n"
NOTE_MARKS = "①②③④⑤⑥⑦⑧⑨⑩"
NO_OUTCOME_CANONICAL = "未見明確驗辭/結果"
NO_OUTCOME_VARIANTS = {
    NO_OUTCOME_CANONICAL,
    "未见明确验辞/结果",
    "未見明確驗辭",
    "未见明确验辞",
    "未見明確結果",
    "未见明确结果",
    "未見結果",
    "未见结果",
    "無",
    "无",
    "沒有",
    "没有",
    "不明",
    "",
}

STYLE_REPLACEMENTS = {
    "贞": "貞",
    "卜辞": "卜辭",
    "释文": "釋文",
    "问": "問",
    "语": "語",
    "义": "義",
    "时": "時",
    "会": "會",
    "为": "爲",
    "这": "這",
    "灾": "災",
    "祸": "禍",
    "见": "見",
    "验": "驗",
    "辞": "辭",
    "结": "結",
    "果": "果",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def load_gold(task_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for name in TASK_FILES:
        path = task_dir / name
        for row in load_jsonl(path):
            row["_source_file"] = name
            rows.append(row)
    return rows


def validate_prediction_ids(predictions: dict[str, Any], gold_rows: list[dict[str, Any]]) -> None:
    gold_ids = {row.get("task_id") for row in gold_rows}
    unknown = sorted(task_id for task_id in predictions if task_id not in gold_ids)
    if unknown:
        preview = ", ".join(repr(task_id) for task_id in unknown[:10])
        suffix = "..." if len(unknown) > 10 else ""
        raise ValueError(f"Prediction contains unknown task_id(s): {preview}{suffix}")


def load_predictions(path: Path) -> dict[str, Any]:
    predictions: dict[str, Any] = {}
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                return predictions
            validate_prediction_columns(reader.fieldnames, path)
            for row in reader:
                task_id, prediction = validated_prediction_row(row, path, reader.line_num)
                add_prediction(predictions, task_id, prediction, path, reader.line_num)
        return predictions

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid prediction JSONL at {path}:{line_no}: {exc}") from exc
            task_id, prediction = validated_prediction_row(row, path, line_no)
            add_prediction(predictions, task_id, prediction, path, line_no)
    return predictions


def validate_prediction_columns(fieldnames: list[str], path: Path) -> None:
    names = {name.strip() for name in fieldnames if name is not None}
    if not names.intersection(ID_KEYS):
        raise ValueError(f"Prediction CSV {path} must contain task_id (or id).")
    if not names.intersection(PREDICTION_KEYS):
        raise ValueError(
            f"Prediction CSV {path} must contain one of: {', '.join(PREDICTION_KEYS)}."
        )


def validated_prediction_row(row: Any, path: Path, line_no: int) -> tuple[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"Prediction row at {path}:{line_no} must be a JSON object or CSV row.")
    task_id = next(
        (row.get(key) for key in ID_KEYS if isinstance(row.get(key), str) and row.get(key).strip()),
        None,
    )
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError(f"Prediction row at {path}:{line_no} must have a non-empty string task_id.")
    if not any(key in row for key in PREDICTION_KEYS):
        raise ValueError(
            f"Prediction row at {path}:{line_no} must contain one of: {', '.join(PREDICTION_KEYS)}."
        )
    return task_id.strip(), first_present(row, list(PREDICTION_KEYS))


def add_prediction(
    predictions: dict[str, Any], task_id: str, prediction: Any, path: Path, line_no: int
) -> None:
    if task_id in predictions:
        raise ValueError(f"Duplicate prediction task_id {task_id!r} at {path}:{line_no}.")
    predictions[task_id] = prediction


def first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def normalize_text(value: Any, keep_punct: bool = True) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value).strip()
    for old, new in STYLE_REPLACEMENTS.items():
        text = text.replace(old, new)
    text = "".join(ch for ch in text if ch not in NOTE_MARKS)
    text = re.sub(r"\s+", "", text)
    if not keep_punct:
        text = "".join(ch for ch in text if ch not in PUNCT and ch != "→")
    return text


def strip_punctuation(value: Any) -> str:
    return normalize_text(value, keep_punct=False)


def split_order_units(text: str) -> list[str]:
    text = normalize_text(text)
    if "→" in text:
        return [strip_punctuation(part) for part in text.split("→") if strip_punctuation(part)]
    parts = [strip_punctuation(part) for part in re.split(r"[，。！？；：、,.!?;:]+", text)]
    return [part for part in parts if part]


def boundaries(text: str) -> set[int]:
    clean_index = 0
    out = set()
    for ch in normalize_text(text):
        if ch in NOTE_MARKS or ch.isspace():
            continue
        if ch in "，；：、,;:":
            if clean_index > 0:
                out.add(clean_index)
        elif ch in "。！？.!?":
            pass
        elif ch not in "（）()[]【】「」『』“”\"'<>《》":
            clean_index += 1
    return out


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def edit_similarity(a: str, b: str) -> float:
    a = normalize_text(a, keep_punct=False)
    b = normalize_text(b, keep_punct=False)
    denom = max(len(a), len(b), 1)
    return max(0.0, 1.0 - edit_distance(a, b) / denom)


def lcs_length(a: str, b: str) -> int:
    prev = [0] * (len(b) + 1)
    for ca in a:
        curr = [0]
        for j, cb in enumerate(b, start=1):
            curr.append(prev[j - 1] + 1 if ca == cb else max(prev[j], curr[-1]))
        prev = curr
    return prev[-1]


def f1_from_sets(pred: set[Any], gold: set[Any]) -> dict[str, float]:
    if not pred and not gold:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not pred:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not gold:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    hit = len(pred & gold)
    precision = hit / len(pred)
    recall = hit / len(gold)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def list_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = value
    elif isinstance(value, tuple):
        raw = list(value)
    elif isinstance(value, str):
        if not value.strip():
            raw = []
        else:
            raw = re.split(r"[，,、；;|/]+", value)
    else:
        raw = [value]
    out = []
    for item in raw:
        text = normalize_text(item)
        if text and text not in out:
            out.append(text)
    return out


def parse_json_object(value: Any) -> tuple[dict[str, Any] | None, bool]:
    if isinstance(value, dict):
        return value, True
    if value is None:
        return None, False
    text = str(value).strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, dict):
                return parsed, True
        except Exception:
            pass
    return None, False


def parse_mcq_label(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = first_present(value, ["label", "answer", "prediction", "output", "text"])
    text = str(value).strip().upper()
    text = text.replace("選", " ").replace("选", " ").replace("答案", " ")
    match = re.search(r"\b([ABCD])\b", text)
    if match:
        return match.group(1)
    if text in {"A", "B", "C", "D"}:
        return text
    return ""


def choice_text_from_prediction(record: dict[str, Any], prediction: Any) -> tuple[str, str, float]:
    choices = {choice["label"]: choice["text"] for choice in record.get("choices", [])}
    label = parse_mcq_label(prediction)
    if label in choices:
        return label, choices[label], 1.0
    pred_text = normalize_text(prediction)
    for choice in record.get("choices", []):
        if normalize_text(choice["text"]) == pred_text:
            return choice["label"], choice["text"], 1.0
    return label, str(prediction or ""), 0.0


def adjacent_pairs(sequence: str) -> set[str]:
    chars = list(strip_punctuation(sequence))
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def position_accuracy(pred: str, gold: str) -> float:
    pred_chars = list(strip_punctuation(pred))
    gold_chars = list(strip_punctuation(gold))
    denom = max(len(gold_chars), 1)
    return sum(1 for idx, ch in enumerate(gold_chars) if idx < len(pred_chars) and pred_chars[idx] == ch) / denom


def score_mcq(record: dict[str, Any], prediction: Any) -> dict[str, float | str]:
    label, pred_text, valid = choice_text_from_prediction(record, prediction)
    answer_label = record.get("answer", "")
    answer_text = record.get("answer_text", "")
    return {
        "pred_label": label,
        "pred_text": pred_text,
        "valid_choice": valid,
        "choice_accuracy": 1.0 if label == answer_label else 0.0,
        "answer_text_exact": 1.0 if normalize_text(pred_text) == normalize_text(answer_text) else 0.0,
    }


def score_t1(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    metrics = score_mcq(record, prediction)
    subtask = record.get("subtask")
    if subtask == "translation_order_mcq":
        pred_units = split_order_units(str(metrics["pred_text"]))
        gold_units = split_order_units(record.get("answer_text", ""))
        unit_scores = f1_from_sets(set(pred_units), set(gold_units))
        pred_joined = "".join(pred_units)
        gold_joined = "".join(gold_units)
        adj = f1_from_sets(adjacent_pairs(pred_joined), adjacent_pairs(gold_joined))
        unit_position = sum(
            1 for idx, unit in enumerate(gold_units) if idx < len(pred_units) and pred_units[idx] == unit
        ) / max(len(gold_units), 1)
        metrics.update(
            {
                "unit_set_precision": unit_scores["precision"],
                "unit_set_recall": unit_scores["recall"],
                "unit_set_f1": unit_scores["f1"],
                "unit_position_accuracy": unit_position,
                "adjacent_pair_f1": adj["f1"],
                "sequence_edit_similarity": edit_similarity(pred_joined, gold_joined),
            }
        )
        metrics["primary_score"] = (
            0.50 * float(metrics["choice_accuracy"])
            + 0.20 * unit_position
            + 0.20 * adj["f1"]
            + 0.10 * unit_scores["f1"]
        )
    else:
        metrics["primary_score"] = float(metrics["choice_accuracy"])
    return metrics


def score_slot_string(pred: Any, gold: Any) -> float:
    return 1.0 if normalize_text(pred) == normalize_text(gold) else 0.0


def score_slot_list(pred: Any, gold: Any, prefix: str) -> dict[str, float]:
    pred_set = set(list_values(pred))
    gold_set = set(list_values(gold))
    scores = f1_from_sets(pred_set, gold_set)
    return {
        f"{prefix}_precision": scores["precision"],
        f"{prefix}_recall": scores["recall"],
        f"{prefix}_f1": scores["f1"],
        f"{prefix}_exact": 1.0 if pred_set == gold_set else 0.0,
    }


def score_t2(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    gold = record["qa_pairs"][0]["answer"]
    pred, parsed = parse_json_object(prediction)
    metrics: dict[str, Any] = {"json_parse": 1.0 if parsed else 0.0}
    if pred is None:
        pred = {}

    metrics["subject_exact"] = score_slot_string(pred.get("subject"), gold.get("subject"))
    metrics["outcome_exact"] = score_outcome(pred.get("outcome"), gold.get("outcome"))
    metrics["charge_exact"] = score_slot_string(pred.get("charge"), gold.get("charge"))
    metrics["charge_char_similarity"] = edit_similarity(pred.get("charge", ""), gold.get("charge", ""))

    for slot in ["action", "object_or_target", "time"]:
        metrics.update(score_slot_list(pred.get(slot), gold.get(slot), slot))

    pred_preface = pred.get("preface") if isinstance(pred.get("preface"), dict) else {}
    gold_preface = gold.get("preface", {})
    preface_fields = []
    for key in ["date", "diviner", "divination_marker"]:
        score = score_slot_string(pred_preface.get(key), gold_preface.get(key))
        metrics[f"preface_{key}_exact"] = score
        preface_fields.append(score)
    metrics["preface_exact"] = 1.0 if all(score == 1.0 for score in preface_fields) else 0.0
    metrics["preface_macro"] = sum(preface_fields) / len(preface_fields)

    slot_components = [
        metrics["subject_exact"],
        metrics["action_f1"],
        metrics["object_or_target_f1"],
        metrics["time_f1"],
        metrics["outcome_exact"],
        metrics["preface_macro"],
        metrics["charge_char_similarity"],
    ]
    metrics["slot_all_exact"] = 1.0 if all(
        [
            metrics["subject_exact"] == 1.0,
            metrics["action_exact"] == 1.0,
            metrics["object_or_target_exact"] == 1.0,
            metrics["time_exact"] == 1.0,
            metrics["outcome_exact"] == 1.0,
            metrics["preface_exact"] == 1.0,
            metrics["charge_exact"] == 1.0,
        ]
    ) else 0.0
    metrics["primary_score"] = sum(slot_components) / len(slot_components) if parsed else 0.0
    return metrics


def score_outcome(pred: Any, gold: Any) -> float:
    pred_norm = normalize_text(pred)
    gold_norm = normalize_text(gold)
    if gold_norm == normalize_text(NO_OUTCOME_CANONICAL):
        return 1.0 if pred_norm in {normalize_text(item) for item in NO_OUTCOME_VARIANTS} else 0.0
    return 1.0 if pred_norm == gold_norm else 0.0


def score_segmentation_open(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    pred = str(prediction or "")
    gold = record.get("answer_text", "")
    pred_chars = strip_punctuation(pred)
    gold_chars = strip_punctuation(gold)
    boundary_scores = f1_from_sets(boundaries(pred), boundaries(gold))
    metrics = {
        "char_sequence_exact": 1.0 if pred_chars == gold_chars else 0.0,
        "punctuation_exact": 1.0 if normalize_text(pred) == normalize_text(gold) else 0.0,
        "boundary_precision": boundary_scores["precision"],
        "boundary_recall": boundary_scores["recall"],
        "boundary_f1": boundary_scores["f1"],
        "edit_similarity": edit_similarity(pred, gold),
    }
    metrics["primary_score"] = (
        0.25 * metrics["char_sequence_exact"]
        + 0.35 * metrics["boundary_f1"]
        + 0.25 * metrics["edit_similarity"]
        + 0.15 * metrics["punctuation_exact"]
    )
    return metrics


def score_segmentation_mcq(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    metrics = score_mcq(record, prediction)
    boundary_scores = f1_from_sets(boundaries(str(metrics["pred_text"])), boundaries(record.get("answer_text", "")))
    metrics.update(
        {
            "boundary_precision": boundary_scores["precision"],
            "boundary_recall": boundary_scores["recall"],
            "boundary_f1": boundary_scores["f1"],
            "edit_similarity": edit_similarity(metrics["pred_text"], record.get("answer_text", "")),
        }
    )
    metrics["primary_score"] = 0.70 * float(metrics["choice_accuracy"]) + 0.30 * boundary_scores["f1"]
    return metrics


def sequence_metrics(prediction: Any, gold: str) -> dict[str, float]:
    pred = strip_punctuation(prediction)
    gold_clean = strip_punctuation(gold)
    adj = f1_from_sets(adjacent_pairs(pred), adjacent_pairs(gold_clean))
    multiset_exact = 1.0 if sorted(pred) == sorted(gold_clean) else 0.0
    lcs_ratio = lcs_length(pred, gold_clean) / max(len(gold_clean), 1)
    return {
        "char_sequence_exact": 1.0 if pred == gold_clean else 0.0,
        "char_multiset_exact": multiset_exact,
        "position_accuracy": position_accuracy(pred, gold_clean),
        "adjacent_pair_f1": adj["f1"],
        "edit_similarity": edit_similarity(pred, gold_clean),
        "lcs_ratio": lcs_ratio,
    }


def score_shuffle_open(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    metrics = sequence_metrics(prediction, record.get("answer_text", ""))
    metrics["primary_score"] = (
        0.40 * metrics["char_sequence_exact"]
        + 0.25 * metrics["position_accuracy"]
        + 0.20 * metrics["edit_similarity"]
        + 0.15 * metrics["adjacent_pair_f1"]
    )
    return metrics


def score_shuffle_mcq(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    metrics = score_mcq(record, prediction)
    seq = sequence_metrics(metrics["pred_text"], record.get("answer_text", ""))
    metrics.update(seq)
    partial = 0.40 * seq["char_sequence_exact"] + 0.25 * seq["position_accuracy"] + 0.20 * seq["edit_similarity"] + 0.15 * seq["adjacent_pair_f1"]
    metrics["primary_score"] = 0.70 * float(metrics["choice_accuracy"]) + 0.30 * partial
    return metrics


def score_mask_mcq(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    metrics = score_mcq(record, prediction)
    pred_text = strip_punctuation(metrics["pred_text"])
    answer_text = strip_punctuation(record.get("answer_text", ""))
    metrics["target_char_exact"] = 1.0 if pred_text == answer_text else 0.0
    metrics["primary_score"] = float(metrics["choice_accuracy"])
    return metrics


def score_t3(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    subtask = record.get("subtask")
    if subtask == "ordered_grid_segmentation_open":
        return score_segmentation_open(record, prediction)
    if subtask == "ordered_grid_segmentation_mcq":
        return score_segmentation_mcq(record, prediction)
    if subtask == "shuffled_grid_reorder_open":
        return score_shuffle_open(record, prediction)
    if subtask == "shuffled_grid_reorder_mcq":
        return score_shuffle_mcq(record, prediction)
    if subtask == "mask30_context_char_mcq":
        return score_mask_mcq(record, prediction)
    return {"primary_score": 0.0}


def score_item(record: dict[str, Any], prediction: Any) -> dict[str, Any]:
    task = record.get("task", "")
    base = {
        "task_id": record.get("task_id", ""),
        "task": task,
        "subtask": record.get("subtask", "semantic_slots"),
        "record_id": record.get("record_id", ""),
        "base_sample_id": record.get("base_sample_id", ""),
        "difficulty": (record.get("difficulty") or {}).get("level", ""),
        "image_kind": record.get("image_kind") or infer_image_kind(record),
        "has_prediction": 1.0 if prediction is not None else 0.0,
    }
    if prediction is None:
        return {**base, "primary_score": 0.0}
    if task.startswith("T1"):
        metrics = score_t1(record, prediction)
    elif task.startswith("T2"):
        metrics = score_t2(record, prediction)
    elif task.startswith("T3"):
        metrics = score_t3(record, prediction)
    else:
        metrics = {"primary_score": 0.0}
    return {**base, **metrics}


def infer_image_kind(record: dict[str, Any]) -> str:
    image = record.get("image", "")
    for part in [
        "base",
        "variant1_random_replace",
        "variant2_grid_ordered",
        "variant2_grid_shuffled",
        "variant2_mask30",
    ]:
        if f"/{part}/" in image:
            return part
    return ""


def numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    out = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)):
            out.append(float(value))
    return out


def mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric_keys = sorted({key for row in rows for key, value in row.items() if isinstance(value, (int, float))})
    summary: dict[str, Any] = {"count": len(rows)}
    for key in metric_keys:
        vals = numeric_values(rows, key)
        if vals:
            summary[key] = mean(vals)
    return summary


def grouped_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key, ""))].append(row)
    return {group: summarize_group(items) for group, items in sorted(groups.items())}


def variant_consistency(rows: list[dict[str, Any]], predictions: dict[str, Any]) -> dict[str, Any]:
    t2_rows = [row for row in rows if row.get("task") == "T2_semantic_slot_qa"]
    gold_by_task_id = {row["task_id"]: row for row in t2_rows}
    values = []
    for row in t2_rows:
        if row.get("image_kind") != "variant1_random_replace":
            continue
        base_task_id = f"T2-slots-{row.get('base_sample_id')}"
        if row["task_id"] not in predictions or base_task_id not in predictions or base_task_id not in gold_by_task_id:
            continue
        pred_variant, ok_variant = parse_json_object(predictions[row["task_id"]])
        pred_base, ok_base = parse_json_object(predictions[base_task_id])
        if not ok_variant or not ok_base or pred_variant is None or pred_base is None:
            values.append(0.0)
            continue
        components = [
            score_slot_string(pred_variant.get("subject"), pred_base.get("subject")),
            score_slot_list(pred_variant.get("action"), pred_base.get("action"), "tmp")["tmp_f1"],
            score_slot_list(pred_variant.get("object_or_target"), pred_base.get("object_or_target"), "tmp")["tmp_f1"],
            score_slot_list(pred_variant.get("time"), pred_base.get("time"), "tmp")["tmp_f1"],
            score_outcome(pred_variant.get("outcome"), pred_base.get("outcome")),
        ]
        values.append(sum(components) / len(components))
    return {
        "variant1_base_prediction_consistency": mean(values),
        "variant1_consistency_pairs": len(values),
    }


def build_summary(per_item: list[dict[str, Any]], gold_rows: list[dict[str, Any]], predictions: dict[str, Any]) -> dict[str, Any]:
    by_task = grouped_summary(per_item, "task")
    task_primary = [summary.get("primary_score") for summary in by_task.values() if isinstance(summary.get("primary_score"), (int, float))]
    return {
        "overall": summarize_group(per_item),
        "benchmark_scores": {
            "item_macro_primary_score": mean(numeric_values(per_item, "primary_score")),
            "balanced_task_primary_score": mean([float(v) for v in task_primary]),
        },
        "by_task": by_task,
        "by_subtask": grouped_summary(per_item, "subtask"),
        "by_difficulty": grouped_summary(per_item, "difficulty"),
        "by_image_kind": grouped_summary(per_item, "image_kind"),
        "robustness": variant_consistency(gold_rows, predictions),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_template(path: Path, gold_rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in gold_rows:
            item = {
                "task_id": row["task_id"],
                "task": row["task"],
                "subtask": row.get("subtask", "semantic_slots"),
                "image": row.get("image"),
                "question": row.get("question") or row.get("qa_pairs", [{}])[0].get("question"),
                "prediction": "",
            }
            if "choices" in row:
                item["choices"] = row["choices"]
            if row.get("task") == "T2_semantic_slot_qa":
                item["answer_template"] = row["qa_pairs"][0].get("answer_template")
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Sentence-OBI multimodal benchmark predictions.")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
        help="Dataset directory containing benchmark_tasks/ (default: %(default)s).",
    )
    parser.add_argument(
        "--tasks-dir",
        type=Path,
        help="Optional direct override for the benchmark_tasks directory.",
    )
    parser.add_argument("--predictions", type=Path, help="Prediction JSONL/CSV with task_id and prediction columns.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for score files (default: %(default)s).",
    )
    parser.add_argument(
        "--write-template",
        type=Path,
        nargs="?",
        const=DEFAULT_TEMPLATE_PATH,
        metavar="PATH",
        help="Write a blank prediction template JSONL and exit; omit PATH for the local runtime path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    task_dir = args.tasks_dir or args.dataset_root / "benchmark_tasks"
    gold_rows = load_gold(task_dir)
    if args.write_template:
        args.write_template.parent.mkdir(parents=True, exist_ok=True)
        write_template(args.write_template, gold_rows)
        print(f"Wrote prediction template: {args.write_template}")
        return
    if not args.predictions:
        raise SystemExit("--predictions is required unless --write-template is used.")

    predictions = load_predictions(args.predictions)
    try:
        validate_prediction_ids(predictions, gold_rows)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    per_item = [score_item(row, predictions.get(row["task_id"])) for row in gold_rows]
    summary = build_summary(per_item, gold_rows, predictions)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "per_item_scores.csv", per_item)
    (args.output_dir / "metrics_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["benchmark_scores"], ensure_ascii=False, indent=2))
    print(f"Wrote: {args.output_dir / 'metrics_summary.json'}")
    print(f"Wrote: {args.output_dir / 'per_item_scores.csv'}")


if __name__ == "__main__":
    main()
