import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = REPO_ROOT / "evaluation"
sys.path.insert(0, str(EVALUATION_DIR))

import score_benchmark as scorer  # noqa: E402


class EvaluationFixture:
    """Small, synthetic task set that exercises the public scorer interface."""

    def __init__(self, root: Path) -> None:
        self.dataset_root = root / "data" / "sentence-OBI"
        self.task_dir = self.dataset_root / "benchmark_tasks"
        self.task_dir.mkdir(parents=True)

        t1 = {
            "task_id": "T1-meaning-fixture",
            "task": "T1_sentence_level_interpretation",
            "subtask": "meaning_mcq",
            "record_id": "fixture-1",
            "difficulty": {"level": "easy", "label": "易"},
            "question": "Choose.",
            "choices": [{"label": "A", "text": "甲骨文释义"}, {"label": "B", "text": "错误"}],
            "answer": "A",
            "answer_text": "甲骨文释义",
        }
        t2 = {
            "task_id": "T2-slots-base_fixture",
            "task": "T2_semantic_slot_qa",
            "subtask": "semantic_slots",
            "image_kind": "base",
            "record_id": "fixture-1",
            "base_sample_id": "base_fixture",
            "difficulty": {"level": "easy", "label": "易"},
            "qa_pairs": [
                {
                    "question": "Extract slots.",
                    "answer": {
                        "subject": "王",
                        "action": ["占卜"],
                        "object_or_target": ["祖先"],
                        "time": ["甲子"],
                        "outcome": "未見明確驗辭/結果",
                        "preface": {"date": "甲子", "diviner": "某", "divination_marker": "卜"},
                        "charge": "祭祀。",
                    },
                }
            ],
        }
        t3 = {
            "task_id": "T3-seg-open-grid_fixture",
            "task": "T3_order_sensitive_understanding",
            "subtask": "ordered_grid_segmentation_open",
            "record_id": "fixture-1",
            "base_sample_id": "base_fixture",
            "question": "Restore punctuation.",
            "answer_text": "甲，乙。",
        }
        for name, rows in {
            "T1_sentence_meaning_order.jsonl": [t1],
            "T2_semantic_slots_qa.jsonl": [t2],
            "T3_order_sensitive.jsonl": [t3],
        }.items():
            (self.task_dir / name).write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )

        self.gold_predictions = {
            "T1-meaning-fixture": "A",
            "T2-slots-base_fixture": t2["qa_pairs"][0]["answer"],
            "T3-seg-open-grid_fixture": "甲，乙。",
        }


class EvaluationTests(unittest.TestCase):
    def test_gold_predictions_are_perfect_for_all_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = EvaluationFixture(Path(tmp))
            gold_rows = scorer.load_gold(fixture.task_dir)
            per_item = [scorer.score_item(row, fixture.gold_predictions[row["task_id"]]) for row in gold_rows]
            summary = scorer.build_summary(per_item, gold_rows, fixture.gold_predictions)

            self.assertEqual(len(gold_rows), 3)
            self.assertEqual(summary["benchmark_scores"]["item_macro_primary_score"], 1.0)
            self.assertEqual(summary["benchmark_scores"]["balanced_task_primary_score"], 1.0)

    def test_cli_uses_dataset_root_and_writes_requested_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = EvaluationFixture(Path(tmp))
            predictions = Path(tmp) / "predictions.jsonl"
            predictions.write_text(
                "".join(
                    json.dumps({"task_id": task_id, "prediction": prediction}, ensure_ascii=False) + "\n"
                    for task_id, prediction in fixture.gold_predictions.items()
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "results"
            result = subprocess.run(
                [
                    sys.executable,
                    str(EVALUATION_DIR / "score_benchmark.py"),
                    "--dataset-root",
                    str(fixture.dataset_root),
                    "--predictions",
                    str(predictions),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / "metrics_summary.json").is_file())
            self.assertTrue((output_dir / "per_item_scores.csv").is_file())
            summary = json.loads((output_dir / "metrics_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["benchmark_scores"]["balanced_task_primary_score"], 1.0)

    def test_common_invalid_inputs_keep_existing_zero_score_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = EvaluationFixture(Path(tmp))
            rows = scorer.load_gold(fixture.task_dir)
            t1 = next(row for row in rows if row["task"].startswith("T1"))
            t2 = next(row for row in rows if row["task"].startswith("T2"))

            missing = scorer.score_item(t1, None)
            invalid_choice = scorer.score_item(t1, "Z")
            invalid_json = scorer.score_item(t2, "not json")

            self.assertEqual(missing["primary_score"], 0.0)
            self.assertEqual(invalid_choice["valid_choice"], 0.0)
            self.assertEqual(invalid_choice["primary_score"], 0.0)
            self.assertEqual(invalid_json["json_parse"], 0.0)
            self.assertEqual(invalid_json["primary_score"], 0.0)

    def test_malformed_jsonl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"task_id": "x",\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                scorer.load_predictions(path)

    def test_prediction_schema_rejects_missing_fields_and_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                "not_object.jsonl": "[1]\n",
                "missing_id.jsonl": '{"prediction": "A"}\n',
                "missing_prediction.jsonl": '{"task_id": "x"}\n',
                "duplicate.jsonl": '{"task_id": "x", "prediction": "A"}\n{"task_id": "x", "prediction": "B"}\n',
            }
            for name, content in cases.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    scorer.load_predictions(path)

            csv_cases = {
                "missing_id.csv": "prediction\nA\n",
                "missing_prediction.csv": "task_id\nx\n",
                "duplicate.csv": "task_id,prediction\nx,A\nx,B\n",
            }
            for name, content in csv_cases.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                with self.subTest(name=name), self.assertRaises(ValueError):
                    scorer.load_predictions(path)

    def test_empty_prediction_file_is_allowed_as_all_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.jsonl"
            path.write_text("", encoding="utf-8")
            self.assertEqual(scorer.load_predictions(path), {})

    def test_id_alias_and_prediction_alias_remain_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aliases.jsonl"
            path.write_text('{"id": "x", "pred": "A"}\n', encoding="utf-8")
            self.assertEqual(scorer.load_predictions(path), {"x": "A"})

    def test_unknown_prediction_ids_are_rejected_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = EvaluationFixture(Path(tmp))
            gold_rows = scorer.load_gold(fixture.task_dir)
            with self.assertRaises(ValueError):
                scorer.validate_prediction_ids({"unknown-task": "A"}, gold_rows)

    def test_runtime_defaults_are_local(self) -> None:
        self.assertEqual(scorer.DEFAULT_DATASET_ROOT, REPO_ROOT / "data" / "sentence-OBI")
        self.assertEqual(scorer.DEFAULT_TEMPLATE_PATH, REPO_ROOT / ".runtime" / "evaluation" / "prediction_template.jsonl")
        self.assertEqual(scorer.DEFAULT_OUTPUT_DIR, REPO_ROOT / ".runtime" / "evaluation" / "results")


if __name__ == "__main__":
    unittest.main()
