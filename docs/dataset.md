# S-OBI dataset schema

This document describes the contents of the `sentence-OBI.zip` release asset. The archive is the only dataset distribution in scope for this repository. It is intentionally kept out of Git history.

## Version and accounting

The v1.0.0 archive contains:

| Quantity | Count |
| --- | ---: |
| Base inscriptions | 95 |
| T1 items | 190 |
| T2 items | 350 |
| T3 items | 155 |
| Total benchmark items | 695 |
| Original JPG images | 95 |
| Benchmark PNG images | 505 |

Task accounting:

| Task | Subtask or variant | Count |
| --- | --- | ---: |
| T1 | meaning questions | 95 |
| T1 | translation-order questions | 95 |
| T2 | base | 95 |
| T2 | random replacement | 255 |
| T3 | `ordered_grid_segmentation_open` | 95 |
| T3 | `mask30_context_char_mcq` | 60 |

S-OBI does not define train, validation, or test splits. A provenance field that says `train`, `val`, or `test` refers to the source material and must not be used as an S-OBI benchmark split.

## Archive layout

After extraction, the relevant layout is:

```text
sentence-OBI/
├── benchmark_tasks/
│   ├── T1_sentence_meaning_order.jsonl
│   ├── T2_semantic_slots_qa.jsonl
│   ├── T3_order_sensitive.jsonl
│   ├── summary.json
│   └── review_data.json
├── evaluation/
├── images/
│   ├── base/
│   ├── variant1_random_replace/
│   ├── variant2_grid_ordered/
│   └── variant2_mask30/
├── meta.json
├── original_images/
└── transforms.jsonl
```

The archive also contains macOS `__MACOSX/` metadata entries. They are filesystem metadata, not benchmark records, and should be ignored.

## Task records

The three JSONL files under `benchmark_tasks/` are the files consumed by the repository scorer. Records share identifiers and image references, with task-specific fields.

Common fields can include:

| Field | Meaning |
| --- | --- |
| `task_id` | Stable identifier used to join a prediction to a task record |
| `task` | Top-level task name, such as `T1_sentence_level_interpretation` |
| `subtask` | Scored subtask name |
| `record_id` / `base_sample_id` | Source or variant grouping identifiers |
| `image` / image reference fields | Relative path to the image; archive records commonly include the `sentence-OBI/` prefix |
| `question` | Prompt shown to the model |
| `choices` | Multiple-choice options, when applicable |
| `answer` / `answer_text` | Gold response used by the supplied scorer |
| `difficulty` | Difficulty metadata, when present |

### T1

`T1_sentence_meaning_order.jsonl` contains the meaning and translation-order records. Meaning records use multiple-choice answers. Translation-order records expose the units or order information required by the ordering metrics. The scorer accepts a choice label (`A`, `B`, `C`, or `D`) or the full option text for multiple-choice items.

### T2

`T2_semantic_slots_qa.jsonl` contains semantic-slot question and answer records. The question and gold answer for the scored item are in `qa_pairs[0]`; loaders should read that pair rather than assuming a top-level question/answer. A model response should be a JSON object. The public scorer evaluates fields including:

```json
{
  "subject": "string",
  "action": ["string"],
  "object_or_target": ["string"],
  "time": ["string"],
  "outcome": "string",
  "preface": {
    "date": "string",
    "diviner": "string",
    "divination_marker": "string"
  },
  "charge": "string"
}
```

The exact gold values remain in the release archive. Use the task record and the scorer's normalization rules as the source of truth for a run.

### T3

`T3_order_sensitive.jsonl` contains two retained subtasks:

- `ordered_grid_segmentation_open`: return a punctuation-restored sentence for an ordered, punctuation-free grid image.
- `mask30_context_char_mcq`: return the option label or option text for the masked-character question.

## Metadata files

`meta.json` and `transforms.jsonl` preserve dataset and image provenance. The supplied `transforms.jsonl` has 570 records; 65 of those records reference images that are not present. These records are metadata observations and do not change the formal benchmark accounting. All 695 formal task records reference an available benchmark image.

`summary.json` and `review_data.json` are included in the archive for dataset context and review. The repository scorer uses the three task JSONL files listed above and does not treat metadata provenance labels as a split.

## Image paths

Resolve paths relative to the extracted `sentence-OBI/` root. Archive records may include a leading `sentence-OBI/` component; the repository loader removes that component before resolving the path. Keep the original directory names and Unicode text intact. A robust loader should ignore `__MACOSX/` entries and should fail with a clear path error when an expected image is unavailable.

## Related files in this repository

- [`evaluation/README.md`](../evaluation/README.md) defines prediction files and the command-line interface.
- [`evaluation/METRICS.md`](../evaluation/METRICS.md) defines the weighted primary metrics.
- [`data/README.md`](../data/README.md) describes download, checksum, and data terms.
