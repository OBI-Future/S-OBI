# S-OBI: Sentence-Level Oracle Bone Inscription Understanding

[English](README.md) · [中文](README_zh.md)

**Beyond Single Character: Evaluating MLLMs for Sentence-Level Oracle Bone Inscription Understanding**

S-OBI is a benchmark for evaluating multimodal large language models (MLLMs) on sentence-level Oracle Bone Inscription (OBI) understanding. It is associated with an ICIG 2026 publication by Ziqi Li, Zijian Chen, Tingzhu Chen, and Guangtao Zhai.

The benchmark is designed to test whether a model can connect OBI images with sentence meaning, semantic structure, ordering, punctuation, and context. The benchmark archive is distributed as a single release asset; the Git repository contains the evaluation toolkit and documentation only.

## Benchmark at a glance

| Component | What it evaluates | Items |
| --- | --- | ---: |
| T1 | Sentence meaning and translation ordering | 190 |
| T2 | Semantic-slot extraction from base and random-replacement variants | 350 |
| T3 | Order-sensitive understanding: grid segmentation and masked-character context | 155 |
| **Total** | **Three-task benchmark** | **695** |

The archive is built from 95 base inscriptions. It contains 95 original JPG images and 505 PNG benchmark images. There is no benchmark train/validation/test split. Labels such as `train` that may occur in provenance metadata are source metadata and do not define an official S-OBI split.

## Tasks

- **T1 — sentence meaning and order.** This task includes 95 meaning questions and 95 translation-order questions. Multiple-choice items are scored by choice accuracy; ordering items additionally evaluate unit positions, adjacent pairs, and unit sets.
- **T2 — semantic slots.** This task contains 95 base items and 255 random-replacement items. A prediction is a JSON object with fields such as `subject`, `action`, `object_or_target`, `time`, `outcome`, `preface`, and `charge`.
- **T3 — order-sensitive understanding.** This task contains 95 `ordered_grid_segmentation_open` items and 60 `mask30_context_char_mcq` items. The first asks for punctuation restoration from an ordered grid; the second asks the model to recover a masked character from context.

The task files and gold annotations are in the release archive. They are deliberately not committed to this repository.

## Download the dataset

Download `sentence-OBI.zip` from the [v1.0.0 GitHub Release](https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0). The archive is the only dataset distribution covered by this repository. After installing the package, the recommended command is:

```bash
python scripts/download_data.py
```

The downloader verifies the SHA-256 digest recorded in [`data/SHA256SUMS`](data/SHA256SUMS), ignores macOS `__MACOSX/` metadata, and safely extracts the archive to `data/sentence-OBI/`. To use an existing local copy, pass `--archive /path/to/sentence-OBI.zip`.

For the archive's data terms and known limitations, read [`data/README.md`](data/README.md) and [`docs/dataset.md`](docs/dataset.md).

## Quickstart

The toolkit uses Python 3.10+ and the Python standard library. It does not download a model or call an external API. From a fresh checkout:

```bash
git clone https://github.com/OBI-Future/S-OBI.git
cd S-OBI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/download_data.py
```

The downloader verifies the release checksum and safely extracts the archive to `data/sentence-OBI/`. To use an existing local copy of the supplied ZIP instead, run `python scripts/download_data.py --archive /path/to/sentence-OBI.zip`.

Validate the extracted formal task files and inspect model-visible inputs:

```bash
python -m sobi.validate --dataset-root data/sentence-OBI
python -m sobi.inspect --dataset-root data/sentence-OBI --task T1 --limit 3
```

Generate a prediction template:

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --write-template
```

The default template is written to `.runtime/evaluation/prediction_template.jsonl`. Fill its `prediction` field and score it:

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --predictions path/to/predictions.jsonl \
  --output-dir .runtime/evaluation/results/my_model
```

The scorer also accepts CSV files with `task_id,prediction` columns. See [`evaluation/README.md`](evaluation/README.md) for the public prediction contract and [`docs/dataset.md`](docs/dataset.md) for the archive schema.

For an end-to-end smoke check without a model, run the deterministic mock backend and score its five predictions:

```bash
python -m examples.run_inference \
  --dataset-root data/sentence-OBI \
  --mock \
  --limit 5 \
  --output .runtime/predictions/smoke.jsonl
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --predictions .runtime/predictions/smoke.jsonl \
  --output-dir .runtime/evaluation/results/smoke
```

The mock backend is for wiring and smoke tests only; it is not a benchmark baseline.

To connect an MLLM, provide a Python function in the form `module:function`:

```python
# my_backend.py
from collections.abc import Mapping
from typing import Any

def predict(task: Mapping[str, Any]) -> Any:
    # task has task_id, benchmark, question, options, image, and metadata.
    # Load credentials/configuration from your local environment as needed.
    return call_your_model(task)
```

Run it with:

```bash
python -m examples.run_inference \
  --dataset-root data/sentence-OBI \
  --backend my_backend:predict \
  --output .runtime/predictions/my_model.jsonl
```

The backend receives `Task.model_input()` without gold answers and must return a JSON-serializable prediction. Return a choice label or text for multiple-choice tasks, a JSON object for T2, and a string for the open T3 subtask. Keep model credentials and local API configuration outside the repository.

## Evaluation and reporting

The scorer reports per-item results, task and subtask breakdowns, difficulty and image-kind breakdowns, and the benchmark-level scores `item_macro_primary_score` and `balanced_task_primary_score`. The recommended headline score for this toolkit is `balanced_task_primary_score`, the unweighted mean of the T1, T2, and T3 task means.

These metrics are the weighted protocol shipped with the provided archive. The repository does not claim that running this scorer reproduces an accuracy table from the ICIG 2026 paper: that requires the same model outputs, preprocessing, and evaluation conditions. Do not compare scores across incompatible prediction formats or task subsets.

## Reproducibility and fair use

Keep the archive version, checksum, model name and revision, image preprocessing, prompt, decoding settings, prediction file, and scorer output with every reported result. Report all three task scores alongside the aggregate, and state whether any items were omitted. A missing prediction receives zero for that item; inspect the per-item CSV before publishing a result.

Use the archive and annotations only in ways permitted by the rights holders and the release terms. The repository's MIT license applies to the repository code. The archive has no separate license statement in the supplied materials, so the data license is currently unspecified and must not be inferred from the code license. See [`data/README.md`](data/README.md) before redistributing or making a derivative dataset.

## Citation

If you use S-OBI, cite the ICIG 2026 paper:

```bibtex
@inproceedings{li2026sobi,
  title     = {Beyond Single Character: Evaluating MLLMs for Sentence-Level Oracle Bone Inscription Understanding},
  author    = {Li, Ziqi and Chen, Zijian and Chen, Tingzhu and Zhai, Guangtao},
  booktitle = {Proceedings of the International Conference on Image and Graphics (ICIG)},
  year      = {2026}
}
```

The machine-readable citation is in [`CITATION.cff`](CITATION.cff). No DOI or page range is asserted until an official bibliographic record is available.

## Repository layout

```text
evaluation/             scoring protocol and scorer
examples/               model-agnostic prediction examples
scripts/                local data and prediction utilities
src/sobi/               reusable dataset utilities
data/README.md          archive instructions and data terms
data/SHA256SUMS         release-asset checksum
docs/dataset.md         detailed schema and task accounting
```

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.
