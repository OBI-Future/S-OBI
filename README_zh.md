# S-OBI：句子级甲骨文理解评测基准

[English](README.md) · [中文](README_zh.md)

**Beyond Single Character: Evaluating MLLMs for Sentence-Level Oracle Bone Inscription Understanding**

S-OBI 是一个面向多模态大语言模型（MLLM）的句子级甲骨文理解评测基准，配套论文发表于 ICIG 2026。作者为 Ziqi Li、Zijian Chen、Tingzhu Chen 和 Guangtao Zhai。

该基准考察模型能否把甲骨文图像与句子含义、语义结构、顺序、标点和上下文联系起来。数据以单个 Release 附件发布；Git 仓库只包含评测工具和文档，不提交数据集内容。

## 基准概览

| 部分 | 评测内容 | 题目数 |
| --- | --- | ---: |
| T1 | 句子含义与翻译顺序 | 190 |
| T2 | 基础图与随机替换图的语义槽抽取 | 350 |
| T3 | 顺序敏感理解：网格分句与遮挡字符上下文 | 155 |
| **合计** | **三项任务** | **695** |

数据包基于 95 条基础铭文，包含 95 张原始 JPG 图像和 505 张 PNG 基准图像。S-OBI 没有官方 train/validation/test 划分。来源元数据中出现的 `train` 等标记不构成 S-OBI 的数据划分。

## 任务

- **T1：句子含义与顺序。** 包含 95 道含义题和 95 道翻译顺序题。选择题使用选项准确率，顺序题还评估单元位置、相邻单元和单元集合。
- **T2：语义槽。** 包含 95 道基础题和 255 道随机替换题。模型输出 JSON 对象，字段包括 `subject`、`action`、`object_or_target`、`time`、`outcome`、`preface` 和 `charge` 等。
- **T3：顺序敏感理解。** 包含 95 道 `ordered_grid_segmentation_open` 和 60 道 `mask30_context_char_mcq`。前者要求从有序网格恢复标点，后者要求根据上下文恢复被遮挡字符。

任务文件和 gold 标注均在 Release 数据包中，刻意不提交到本代码仓库。

## 下载数据

请从 [v1.0.0 GitHub Release](https://github.com/OBI-Future/S-OBI/releases/tag/v1.0.0) 下载 `sentence-OBI.zip`。本仓库只分发这一份数据包。安装工具包后，推荐运行：

```bash
python scripts/download_data.py
```

下载脚本会校验 [`data/SHA256SUMS`](data/SHA256SUMS) 中的 SHA-256 值，忽略 macOS `__MACOSX/` 元数据，并安全解压到 `data/sentence-OBI/`。如果已有本地 ZIP，可传入 `--archive /path/to/sentence-OBI.zip`。

数据条款和已知限制见 [`data/README.md`](data/README.md) 与 [`docs/dataset.md`](docs/dataset.md)。

## 快速开始

工具要求 Python 3.10 或更高版本，只使用 Python 标准库，不会下载模型或调用外部 API。从全新仓库开始：

```bash
git clone https://github.com/OBI-Future/S-OBI.git
cd S-OBI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/download_data.py
```

下载脚本会校验 Release 附件并安全解压到 `data/sentence-OBI/`。如果已有用户提供的 ZIP，可运行 `python scripts/download_data.py --archive /path/to/sentence-OBI.zip`。

校验正式任务文件并查看模型可见输入：

```bash
python -m sobi.validate --dataset-root data/sentence-OBI
python -m sobi.inspect --dataset-root data/sentence-OBI --task T1 --limit 3
```

生成预测模板：

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --write-template
```

默认模板写入 `.runtime/evaluation/prediction_template.jsonl`。填写每行的 `prediction` 字段后进行评测：

```bash
python evaluation/score_benchmark.py \
  --dataset-root data/sentence-OBI \
  --predictions path/to/predictions.jsonl \
  --output-dir .runtime/evaluation/results/my_model
```

评测器也接受包含 `task_id,prediction` 列的 CSV。公开的预测格式见 [`evaluation/README.md`](evaluation/README.md)，数据字段说明见 [`docs/dataset.md`](docs/dataset.md)。

如果不接入模型，可使用确定性的 mock 后端进行端到端冒烟检查，再评测生成的 5 条预测：

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

该 mock 后端仅用于检查流程，不是 benchmark baseline。

接入自己的 MLLM 时，提供一个形如 `module:function` 的 Python 函数：

```python
# my_backend.py
from collections.abc import Mapping
from typing import Any

def predict(task: Mapping[str, Any]) -> Any:
    # task 包含 task_id、benchmark、question、options、image 和 metadata。
    # 如需凭据或配置，请从本地环境读取。
    return call_your_model(task)
```

运行：

```bash
python -m examples.run_inference \
  --dataset-root data/sentence-OBI \
  --backend my_backend:predict \
  --output .runtime/predictions/my_model.jsonl
```

后端接收不含 gold 答案的 `Task.model_input()`，并且必须返回可 JSON 序列化的预测。选择题返回选项标签或文本，T2 返回 JSON 对象，T3 开放题返回字符串。模型凭据和本地 API 配置应放在仓库之外。

## 评测与结果报告

评测器输出逐题结果、按任务和子任务统计的结果，以及按难度和图像类型统计的结果，并给出 `item_macro_primary_score` 和 `balanced_task_primary_score`。推荐将 `balanced_task_primary_score` 作为工具包的总分，即 T1、T2、T3 三个任务均值的算术平均。

这些指标是随数据包提供的加权评测协议。本仓库不宣称仅运行该评测器即可复现 ICIG 2026 论文中的 accuracy 表格；复现还需要相同的模型输出、预处理和评测条件。不要比较格式或任务子集不同的结果。

## 可复现性与合理使用

每次报告结果时请保留数据包版本和校验值、模型名称与版本、图像预处理、提示词、解码参数、预测文件以及评测输出。请同时报告三个任务分数并说明是否省略题目。缺失预测按该题 0 分处理，应在发布结果前检查逐题 CSV。

请在权利人允许的范围内使用数据包和标注。仓库的 MIT 许可证适用于仓库代码；提供的数据包没有单独的许可证声明，因此不能从代码许可证推断数据许可证。重新分发或制作衍生数据集前，请阅读 [`data/README.md`](data/README.md)。

## 引用

使用 S-OBI 时请引用 ICIG 2026 论文：

```bibtex
@inproceedings{li2026sobi,
  title     = {Beyond Single Character: Evaluating MLLMs for Sentence-Level Oracle Bone Inscription Understanding},
  author    = {Li, Ziqi and Chen, Zijian and Chen, Tingzhu and Zhai, Guangtao},
  booktitle = {Proceedings of the International Conference on Image and Graphics (ICIG)},
  year      = {2026}
}
```

机器可读的引用信息见 [`CITATION.cff`](CITATION.cff)。在正式书目信息可核实前，本文档不填写 DOI 或页码。

## 仓库结构

```text
evaluation/             评测协议和评测器
examples/               与模型无关的预测示例
scripts/                本地数据和预测工具
src/sobi/               可复用的数据工具
data/README.md          数据包说明和数据条款
data/SHA256SUMS         Release 附件校验值
docs/dataset.md         详细字段和任务统计
```

版本变更见 [`CHANGELOG.md`](CHANGELOG.md)。
