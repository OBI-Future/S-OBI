<div align="center">

# S-OBI

**Beyond Single Character: Evaluating MLLMs for Sentence-Level Oracle Bone Inscription Understanding**

Ziqi Li · Zijian Chen · Tingzhu Chen · Guangtao Zhai · **ICIG 2026**

<p>
  <a href="https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/ICIG-2026-6f42c1.svg" alt="ICIG 2026"></a>
  <a href="https://github.com/OBI-Future/S-OBI"><img src="https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/OBI-Future/S-OBI/actions/workflows/tests.yml"><img src="https://github.com/OBI-Future/S-OBI/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/dataset-695%20QA-0f766e.svg" alt="695 benchmark questions"></a>
</p>

<p>
  <a href="#overview">Overview</a> ·
  <a href="#download-the-dataset">Dataset</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#evaluation-and-reporting">Evaluation</a> ·
  <a href="#citation">Citation</a>
</p>

<p><a href="README_zh.md">中文说明</a> · <a href="https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0">Dataset Release</a></p>

</div>

## Overview

S-OBI is a sentence-level benchmark for evaluating multimodal large language models (MLLMs) on Oracle Bone Inscription (OBI) understanding. It tests whether a model can connect an OBI image with sentence meaning, semantic structure, order, punctuation, and context.

<p align="center">
  <a href="assets/figures/fig1_obi_sources.png"><img src="assets/figures/fig1_obi_sources.png" alt="S-OBI source examples, paper Figure 1" width="920"></a>
</p>
<p align="center"><sub><strong>Paper Fig. 1.</strong> OBI forms covered by S-OBI and examples of sentence-level construction.</sub></p>

<table align="center">
  <tr>
    <td align="center"><strong>95</strong><br>base inscriptions</td>
    <td align="center"><strong>695</strong><br>benchmark questions</td>
    <td align="center"><strong>3</strong><br>task families</td>
  </tr>
</table>

The release archive contains 95 original JPG images and 505 PNG benchmark images. S-OBI has no official train/validation/test split; `train` labels that appear in provenance metadata do not define an S-OBI split.

## Tasks

| Task | Focus | Composition | Items |
| --- | --- | --- | ---: |
| **T1** | Sentence meaning and order | 95 meaning questions + 95 translation-order questions | **190** |
| **T2** | Semantic-slot extraction | 95 base items + 255 random-replacement items | **350** |
| **T3** | Order-sensitive understanding | 95 ordered-grid segmentation items + 60 masked-character context items | **155** |
| **Total** | Three task families | — | **695** |

### Construction overview

<p align="center">
  <a href="assets/figures/fig2_construction_pipeline.png"><img src="assets/figures/fig2_construction_pipeline.png" alt="S-OBI construction pipeline, paper Figure 2" width="920"></a>
</p>
<p align="center"><sub><strong>Paper Fig. 2.</strong> Construction pipeline and task design in the paper; the formal tasks in the current Release are defined by the table above and the supplied archive.</sub></p>

T1 uses choice accuracy for meaning questions and also evaluates unit positions, adjacent pairs, and unit sets for ordering questions. T2 expects a JSON object with fields such as `subject`, `action`, `object_or_target`, `time`, `outcome`, `preface`, and `charge`. T3 covers punctuation restoration from an ordered grid and masked-character recovery from context.

### Case studies

<p align="center">
  <a href="assets/figures/fig4_task_case_studies.png"><img src="assets/figures/fig4_task_case_studies.png" alt="S-OBI task case studies, paper Figure 4" width="920"></a>
</p>
<p align="center"><sub><strong>Paper Fig. 4.</strong> Semantic matching and contextual reasoning across four difficulty levels, with model responses reproduced from the paper.</sub></p>

All three figures are reproduced from the paper. See [figure sources](assets/figures/README.md) for the original figure numbers and page references; click a figure to view it at full resolution.

## Download the dataset

Download `sentence-OBI.zip` from the [v1.0.0 GitHub Release](https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0). This archive is the only dataset distribution covered by the repository; task files and gold annotations are not committed to Git.

After installing the package, run:

```bash
python scripts/download_data.py
```

The downloader verifies the SHA-256 digest in [`data/SHA256SUMS`](data/SHA256SUMS), ignores macOS `__MACOSX/` metadata, and safely extracts the archive to `data/sentence-OBI/`. To use an existing local copy:

```bash
python scripts/download_data.py --archive /path/to/sentence-OBI.zip
```

Read [`data/README.md`](data/README.md) and [`docs/dataset.md`](docs/dataset.md) for data terms, known limitations, and the archive schema.

## Quickstart

The toolkit requires Python 3.10+ and the Python standard library. It does not download a model or call an external API.

```bash
git clone https://github.com/OBI-Future/S-OBI.git
cd S-OBI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/download_data.py
```

Validate the formal task files and inspect model-visible inputs:

```bash
python -m sobi.validate --dataset-root data/sentence-OBI
python -m sobi.inspect --dataset-root data/sentence-OBI --task T1 --limit 3
```

Generate a prediction template and score a completed prediction file:

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --write-template

python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --predictions path/to/predictions.jsonl \
  --output-dir .runtime/evaluation/results/my_model
```

The template is written to `.runtime/evaluation/prediction_template.jsonl`. The scorer also accepts CSV files with `task_id,prediction` columns. See [`evaluation/README.md`](evaluation/README.md) for the public prediction contract.

<details>
<summary><strong>Optional: run an end-to-end smoke check without a model</strong></summary>

The deterministic mock backend checks the wiring with five predictions. It is for smoke tests only and is not a benchmark baseline.

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

</details>

<details>
<summary><strong>Connect your own MLLM backend</strong></summary>

Provide a Python function in the form `module:function`. The backend receives `Task.model_input()` without gold answers and must return a JSON-serializable prediction.

```python
# my_backend.py
from collections.abc import Mapping
from typing import Any

def predict(task: Mapping[str, Any]) -> Any:
    # task has task_id, benchmark, question, options, image, and metadata.
    return call_your_model(task)
```

Run it with:

```bash
python -m examples.run_inference \
  --dataset-root data/sentence-OBI \
  --backend my_backend:predict \
  --output .runtime/predictions/my_model.jsonl
```

Return a choice label or text for multiple-choice tasks, a JSON object for T2, and a string for the open T3 subtask. Keep model credentials and local API configuration outside the repository.

</details>

## Evaluation and reporting

The scorer reports per-item results, task and subtask breakdowns, difficulty and image-kind breakdowns, and the benchmark-level scores `item_macro_primary_score` and `balanced_task_primary_score`. The recommended headline score for this toolkit is `balanced_task_primary_score`, the unweighted mean of the T1, T2, and T3 task means.

These are the weighted metrics shipped with the provided archive. Running this scorer alone does **not** claim to reproduce an accuracy table from the ICIG 2026 paper: reproduction also requires the same model outputs, preprocessing, prompts, and evaluation conditions. Report all three task scores with the aggregate, and state whether any items were omitted.

## Reproducibility and data terms

Keep the archive version and checksum, model name and revision, image preprocessing, prompt, decoding settings, prediction file, and scorer output with every reported result. A missing prediction receives zero for that item; inspect the per-item CSV before publishing results.

The repository's MIT license applies to the code. The supplied archive has no separate license statement, so the data license is currently **unspecified** and must not be inferred from the code license. Use and redistribute the archive only as permitted by the rights holders; read [`data/README.md`](data/README.md) before making a derivative dataset.

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

## Repository map

| Path | Purpose |
| --- | --- |
| `evaluation/` | Scoring protocol and scorer |
| `examples/` | Model-agnostic prediction examples |
| `scripts/` | Local data and prediction utilities |
| `src/sobi/` | Reusable dataset utilities |
| `data/README.md` | Archive instructions and data terms |
| `docs/dataset.md` | Detailed schema and task accounting |

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.
