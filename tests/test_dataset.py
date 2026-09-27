from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from examples.run_inference import main as run_inference
from sobi import SOBIDataset, validate_dataset


def _write_dataset(root: Path) -> None:
    tasks = root / "benchmark_tasks"
    image = root / "images"
    tasks.mkdir(parents=True)
    image.mkdir()
    (image / "t1.png").write_bytes(b"png")
    (image / "t2.png").write_bytes(b"png")
    (image / "t3.png").write_bytes(b"png")
    records = {
        "T1": {
            "task_id": "T1-demo-001",
            "task": "T1_sentence_level_interpretation",
            "subtask": "meaning_mcq",
            "image": "sentence-OBI/images/t1.png",
            "question": "Choose.",
            "choices": [{"label": "A", "text": "one"}],
            "answer": "A",
            "answer_text": "one",
            "gold": {"raw_text": "secret"},
        },
        # T2's public schema intentionally has no top-level question.
        "T2": {
            "task_id": "T2-demo-001",
            "task": "T2_semantic_slot_qa",
            "image": "sentence-OBI/images/t2.png",
            "qa_pairs": [
                {
                    "question": "Fill the slots.",
                    "answer_template": {"subject": "string"},
                    "answer": {"subject": "secret"},
                }
            ],
            "gold": {"raw_text": "secret"},
        },
        "T3": {
            "task_id": "T3-demo-001",
            "task": "T3_order_sensitive_understanding",
            "subtask": "ordered_grid_segmentation_open",
            "image": "sentence-OBI/images/t3.png",
            "question": "Add punctuation.",
            "answer_text": "secret",
            "gold": {"raw_text": "secret"},
            "answer_format": "text",
        },
    }
    filenames = {
        "T1": "T1_sentence_meaning_order.jsonl",
        "T2": "T2_semantic_slots_qa.jsonl",
        "T3": "T3_order_sensitive.jsonl",
    }
    for benchmark, record in records.items():
        (tasks / filenames[benchmark]).write_text(
            json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
        )


class DatasetTests(unittest.TestCase):
    def test_nested_t2_question_and_gold_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_dataset(root)
            dataset = SOBIDataset(root)
            tasks = list(dataset.iter_tasks())
            self.assertEqual(
                [task.task_id for task in tasks],
                ["T1-demo-001", "T2-demo-001", "T3-demo-001"],
            )
            t2 = tasks[1]
            self.assertEqual(t2.question, "Fill the slots.")
            payload = t2.model_input()
            encoded = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("answer", payload)
            self.assertNotIn("gold", payload)
            self.assertNotIn("secret", encoded)
            self.assertFalse(hasattr(t2, "gold"))

            gold = list(dataset.iter_gold_tasks())[1]
            self.assertEqual(gold.gold["answer"]["subject"], "secret")
            self.assertNotIn("gold", gold.model_input())

    def test_task_filter_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_dataset(root)
            dataset = SOBIDataset(root)
            self.assertEqual([task.benchmark for task in dataset.iter_tasks("T2")], ["T2"])
            report = validate_dataset(root, expected_counts={"T1": 1, "T2": 1, "T3": 1})
            self.assertTrue(report.ok)
            self.assertEqual(report.total_tasks, 3)
            self.assertEqual(report.missing_images, ())

    def test_runner_resume_validates_prediction_and_repairs_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "dataset"
            _write_dataset(root)
            output = Path(directory) / "predictions.jsonl"
            output.write_text('{"task_id": "T1-demo-001"}', encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "prediction"):
                run_inference(
                    [
                        "--dataset-root",
                        str(root),
                        "--mock",
                        "--output",
                        str(output),
                        "--resume",
                    ]
                )

            output.write_text('{"task_id": "T1-demo-001", "prediction": "A"}', encoding="utf-8")
            run_inference(
                [
                    "--dataset-root",
                    str(root),
                    "--mock",
                    "--output",
                    str(output),
                    "--resume",
                    "--limit",
                    "1",
                ]
            )
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["task_id"] for row in rows], ["T1-demo-001", "T2-demo-001"])


if __name__ == "__main__":
    unittest.main()
