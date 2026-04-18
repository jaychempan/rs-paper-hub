<div align="center">

<img src="asset/logo.png" alt="RS-Paper-Hub" width="100">

# RS-Paper-Hub

**arXiv 遥感论文自动采集、清洗与视觉语言模型（VLM）筛选工具**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/source-arXiv-b31b1b.svg)](https://arxiv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## 概述

RS-Paper-Hub 自动从 arXiv 采集 2020 年至今的遥感论文，提取结构化元数据，并提供一键式数据清洗、VLM 论文筛选和自动分类功能。

### 核心功能

- **自动采集** — 通过 arXiv API 抓取论文，内置限流与重试
- **默认增量** — 自动跳过已有论文，`--update` 抓取最近 7 天新论文
- **断点续传** — 进度保存在 `progress.json`，中断后自动恢复
- **一键处理** — `pipeline.py` 一条命令完成去重、清洗、分类、筛选
- **自动去重** — Pipeline 按 `Paper_link` 自动去除重复论文
- **数据清洗** — 从摘要提取代码仓库链接，自动填充 `code` 字段
- **全量分类** — 所有论文自动标记为 `Method`、`Dataset`、`Survey`、`Application`、`Dataset+Method` 等
- **VLM 筛选** — 基于关键词规则筛选视觉语言模型相关论文
- **交互式网页** — 相关度搜索、多维图表筛选、年份范围选择、BibTeX 导出、移动端适配
- **PDF 下载** — 批量下载，自动去重，按年份归档

---

## 快速开始

```bash
pip install -r requirements.txt

# 采集全部论文
python main.py

# 一键处理：清洗 + 筛选 + 分类
python pipeline.py
```

---

## 日常更新

```bash
# 1. 抓取最新论文（最近 7 天，默认增量）
python main.py --update

# 2. 一键处理（去重 → 清洗 → 分类 → 筛选 → 导出）
python pipeline.py
```

两条命令搞定。所有输出文件（`papers.csv/json`、`papers_vlm.csv/json`）自动更新。

> **注意：** `--incremental` 默认开启，已有论文会自动跳过。如需全量重新采集，请使用 `--no-incremental`。

---

## 使用说明

### 论文采集

```bash
# 全量采集（2020 至今）
python main.py

# 自定义年份范围
python main.py --start-year 2023 --end-year 2025

# 限制数量（测试用）
python main.py --max-results 100

# 增量模式（跳过已有论文）
python main.py --incremental

# 快速更新（最近 7 天）
python main.py --update

# 查看进度
python main.py --status
```

### 一键处理（推荐）

```bash
# 一键：清洗 + VLM 筛选 + 分类
python pipeline.py

# 自定义输入
python pipeline.py --input output/papers.json
```

`pipeline.py` 自动执行以下步骤：

1. **加载与去重** — 按 `Paper_link` 去除重复论文
2. **清洗** — 从摘要提取代码链接，填充 `code` 字段
3. **全量分类** — 为所有论文标记 Method / Dataset / Survey / Application / Other
4. **保存** — 写入清洗后的 `papers.csv` + `papers.json`
5. **VLM 筛选** — 按关键词匹配 VLM 相关论文
6. **VLM 分类** — 细化 VLM 子集分类
7. **导出** — 写入 `papers_vlm.csv/json` 和 `papers_vlm_annotated.json`

### 单独工具

也可以分步执行：

```bash
# 仅清洗
python clean.py --inplace

# 仅 VLM 筛选
python filter_vlm.py --input output/papers.json

# 为已有论文补全精确发布日期（按需）
python backfill_dates_noneed.py
```

### PDF 下载

```bash
# 采集并下载 PDF
python main.py --download

# 仅下载 PDF（基于已有数据，不重新采集）
python main.py --download-only
```

---

## 命令参数

### `main.py`

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--start-year` | 起始年份 | 2020 |
| `--end-year` | 结束年份 | 2026 |
| `--max-results` | 最大论文数量 | 无限制 |
| `--output-dir` | 输出目录 | `output` |
| `--update` | 快速更新（仅最近 7 天） | 关 |
| `--incremental` | 跳过已有论文 | **开** |
| `--no-incremental` | 禁用增量，全量重抓 | 关 |
| `--download` | 下载 PDF | 关 |
| `--download-only` | 仅下载 PDF（跳过采集） | 关 |
| `--with-code` | 查询 Papers With Code 代码链接 | 关 |
| `--status` | 显示进度并退出 | — |
| `-v, --verbose` | 详细日志 | 关 |

### `pipeline.py`

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 输入 JSON 文件 | `output/papers.json` |
| `--output-dir` | 输出目录 | `output` |

---

## 输出字段

所有输出同时提供 **CSV** 和 **JSON** 两种格式。

| 字段 | 说明 | 示例 |
|------|------|------|
| `Category` | 论文类别 | Method, Dataset, Survey |
| `Type` | arXiv 主分类 | Computer Vision |
| `Subtype` | 其他分类 | Image and Video Processing |
| `Date` | 精确发布日期 | 2024-03-15 |
| `Month` | 发布月份 | 3 |
| `Year` | 发布年份 | 2024 |
| `Institute` | 第一作者机构 | （arXiv 数据有限，可能为空） |
| `Title` | 论文标题 | Hybrid Attention Network for... |
| `abbr.` | 标题中的缩写 | HMANet |
| `Paper_link` | arXiv 链接 | http://arxiv.org/abs/2301.12345 |
| `Abstract` | 摘要 | ... |
| `code` | 代码仓库链接 | https://github.com/... |
| `Publication` | 发表期刊/会议 | CVPR 2024 |
| `BibTex` | BibTeX 引用 | @article{...} |
| `Authors` | 作者列表 | Alice, Bob, Charlie |

---

## 项目结构

```
rs-paper-hub/
├── main.py              # 采集器命令行入口
├── pipeline.py          # 一键处理：清洗 + 筛选 + 分类
├── config.py            # 搜索配置
├── scraper.py           # arXiv API 采集器
├── parser.py            # 元数据解析与 BibTeX 生成
├── downloader.py        # PDF 下载器（断点续传）
├── progress.py          # 进度追踪器
├── clean.py             # 单独数据清洗
├── filter_vlm.py        # 单独 VLM 筛选与分类
├── backfill_dates.py    # 日期补全工具
├── pwc_client.py        # Papers With Code 客户端
├── cleaning/
│   ├── abstract_cleaner.py   # 摘要链接提取
│   ├── classifier.py         # 论文分类器（Method/Dataset/Survey/...）
│   └── filter/
│       └── vlm_filter.py     # VLM 关键词规则
├── requirements.txt
└── output/
    ├── papers.csv/json            # 全部论文（已清洗）
    ├── papers_vlm.csv/json        # VLM 子集（含分类标签）
    ├── papers_vlm_annotated.json  # 完整列表（带 VLM 标注）
    └── progress.json              # 采集进度
```

---

## 搜索范围

当前搜索 arXiv **所有分类**中标题或摘要包含 `"remote sensing"` 的论文。如需调整，编辑 [`config.py`](config.py) 中的 `SEARCH_QUERY`：

```python
# 仅限 cs.CV
SEARCH_QUERY = '(ti:"remote sensing" OR abs:"remote sensing") AND cat:cs.CV'
```

---

## 速率限制

| 操作 | 速率 | 说明 |
|------|------|------|
| 元数据查询 | ~3 秒/请求 | 每次返回最多 100 条 |
| PDF 下载 | ~3 秒/文件 | 遵守 arXiv 限制 |

**建议工作流**：先采集元数据（`python main.py`），确认无误后再单独下载 PDF（`python main.py --download-only`）。

---

## 网页可视化

```bash
python3 -m http.server 8080
```

打开 http://localhost:8080 即可查看，功能包括：

- **相关度搜索** — 标题匹配优先于摘要匹配
- **多维图表筛选** — 点击年份/类型/分类柱状图即可筛选，支持多选
- **年份范围选择** — 单年或自定义范围
- **论文自动分类** — 所有论文自动标记（Method、Dataset、Survey、Application 等）
- **今日新增标记** — 统计栏显示 `+N` 新增数量
- **移动端适配** — 可折叠筛选面板，响应式布局
- **BibTeX 导出** — 一键复制，弹窗预览
- **LaTeX 渲染** — KaTeX 数学公式渲染

---

## 注意事项

- `Institute` 字段依赖 arXiv 的 affiliation 信息，大部分论文未提供
- 已下载的 PDF 和已采集的月份会被记录，重复运行不会重复处理
- `progress.json` 采用原子写入，中断不会损坏进度文件

---

## 引用

如果 RS-Paper-Hub 对您的研究或工作有所帮助，请考虑引用本仓库：

```bibtex
@software{rs_paper_hub,
  author       = {ML4Sustain},
  title        = {RS-Paper-Hub: A Curated Collection of Remote Sensing Papers from arXiv},
  year         = {2025},
  url          = {https://github.com/ML4Sustain/rs-paper-hub},
  note         = {Automated scraping, cleaning, classification, and VLM filtering pipeline for remote sensing papers}
}
```

---

## License

MIT
