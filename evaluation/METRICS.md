# Sentence-OBI Metrics

`sentence-OBI` contains T1, T2, and the retained T3 subtasks:

- `ordered_grid_segmentation_open`
- `mask30_context_char_mcq`

The scoring script reports:

- `item_macro_primary_score`: average `primary_score` over all items.
- `balanced_task_primary_score`: average of the T1, T2, and T3 task means.
- `by_task`: metrics grouped by T1/T2/T3.
- `by_subtask`: metrics grouped by subtask.
- `by_difficulty`: metrics grouped by difficulty.
- `by_image_kind`: metrics grouped by image type.

## T1

### `meaning_mcq`

Primary metric:

```text
primary_score = choice_accuracy
```

Other metrics:

- `valid_choice`
- `answer_text_exact`

### `translation_order_mcq`

Primary metric:

```text
0.50 * choice_accuracy
+ 0.20 * unit_position_accuracy
+ 0.20 * adjacent_pair_f1
+ 0.10 * unit_set_f1
```

Other metrics:

- `unit_set_precision`
- `unit_set_recall`
- `unit_set_f1`
- `unit_position_accuracy`
- `adjacent_pair_f1`
- `sequence_edit_similarity`

## T2

T2 evaluates semantic-slot extraction from base and random-replacement sentence images.

Expected prediction shape:

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

Primary metric:

```text
mean(
  subject_exact,
  action_f1,
  object_or_target_f1,
  time_f1,
  outcome_exact,
  preface_macro,
  charge_char_similarity
)
```

Other metrics:

- `json_parse`
- `slot_all_exact`
- `action_precision / action_recall / action_f1 / action_exact`
- `object_or_target_precision / object_or_target_recall / object_or_target_f1 / object_or_target_exact`
- `time_precision / time_recall / time_f1 / time_exact`
- `preface_date_exact`
- `preface_diviner_exact`
- `preface_divination_marker_exact`
- `charge_exact`

The summary also reports `variant1_base_prediction_consistency` when predictions contain paired base and variant1 items.

## T3

### `ordered_grid_segmentation_open`

This open task asks the model to restore punctuation for an ordered, punctuation-free grid image.

Primary metric:

```text
0.25 * char_sequence_exact
+ 0.35 * boundary_f1
+ 0.25 * edit_similarity
+ 0.15 * punctuation_exact
```

Other metrics:

- `char_sequence_exact`
- `punctuation_exact`
- `boundary_precision`
- `boundary_recall`
- `boundary_f1`
- `edit_similarity`

### `mask30_context_char_mcq`

This MCQ task asks the model to recover the masked character from context.

Primary metric:

```text
primary_score = choice_accuracy
```

Other metrics:

- `valid_choice`
- `answer_text_exact`
- `target_char_exact`
