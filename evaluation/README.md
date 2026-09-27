# Sentence-OBI Evaluation Toolkit

This folder provides the evaluation code for `sentence-OBI`.

The scorer reads the benchmark files from the dataset directory. After extracting the
provided `sentence-OBI.zip`, place the resulting `sentence-OBI/` directory at
`data/sentence-OBI/` (or pass another location with `--dataset-root`). The macOS
`__MACOSX/` metadata entries are not needed by the scorer.

`sentence-OBI` keeps T1 and T2 unchanged, and keeps only T3-1 and T3-5:

- `ordered_grid_segmentation_open`
- `mask30_context_char_mcq`

## Files

- `METRICS.md`: metric definitions for the retained tasks.
- `score_benchmark.py`: scoring script.
- The extracted ZIP contains `evaluation/prediction_template.jsonl` and
  `evaluation/examples/gold_predictions.jsonl`; the repository keeps generated
  templates and results under `.runtime/evaluation/` by default.

## Prediction Template

From the repository root, generate a template using the default dataset location:

```bash
python evaluation/score_benchmark.py --dataset-root data/sentence-OBI --write-template
```

This writes `.runtime/evaluation/prediction_template.jsonl`. Each row contains
`task_id`, image path, question, choices when present, and a blank `prediction`.
Provide a path after `--write-template` to choose another location.

## Prediction Format

JSONL:

```json
{"task_id": "T1-meaning-base_001", "prediction": "D"}
{"task_id": "T3-seg-open-grid_001", "prediction": "庚辰卜，仧貞：朕芻于鬥。"}
```

CSV:

```csv
task_id,prediction
T1-meaning-base_001,D
```

MCQ tasks accept `A/B/C/D` or the full option text. T2 should output a JSON object.

## Scoring

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --predictions path/to/predictions.jsonl \
  --output-dir .runtime/evaluation/results/my_model
```

If `--output-dir` is omitted, results are written to
`.runtime/evaluation/results/`. `--tasks-dir` remains available as an advanced
override for callers that already have a direct `benchmark_tasks/` path.

Outputs:

- `metrics_summary.json`
- `per_item_scores.csv`

The recommended main score is `balanced_task_primary_score`, which averages T1, T2, and T3 task means.

The scorer implements the weighted protocol shipped with this ZIP. The repository
does not claim that these commands reproduce any accuracy table from the paper
without the same model outputs and evaluation conditions.
