<div align="center">

<img src="asset/logo.png" alt="RS-Paper-Hub" width="100">

# RS-Paper-Hub

**A curated collection of Remote Sensing papers from arXiv, with automated scraping, cleaning, and VLM filtering.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/source-arXiv-b31b1b.svg)](https://arxiv.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## Overview

RS-Paper-Hub automatically scrapes remote sensing papers from arXiv (2020–present), extracts structured metadata, and provides a one-click pipeline for data cleaning, VLM-related paper filtering, and classification.

### Key Features

- **Automated Scraping** — Fetch papers via arXiv API with rate limiting and retry
- **Incremental by Default** — Only new papers are fetched; duplicates auto-removed
- **Resumable** — Progress tracked in `progress.json`; interrupted runs pick up where they left off
- **One-Click Pipeline** — `pipeline.py` runs cleaning, deduplication, filtering, and classification in one command
- **Data Cleaning** — Extract code repo URLs from abstracts into the `code` field
- **Auto-Deduplication** — Pipeline removes duplicate papers by `Paper_link` automatically
- **Classification** — Auto-label all papers as `Method`, `Dataset`, `Survey`, `Application`, `Dataset+Method`, etc.
- **VLM Filtering** — Keyword-based filtering for Vision-Language Model related papers
- **Interactive Web Viewer** — Search with relevance ranking, multi-dimensional chart filtering, year range selection, BibTeX export, and mobile-friendly collapsible UI
- **PDF Download** — Batch download with deduplication, organized by year

---

## Quick Start

```bash
pip install -r requirements.txt

# Scrape all papers
python main.py

# One-click: clean + filter + classify
python pipeline.py
```

---

## Daily Workflow

```bash
# 1. Grab latest papers (last 7 days, incremental by default)
python main.py --update

# 2. Run full pipeline (deduplicate → clean → classify → filter → export)
python pipeline.py
```

That's it. All output files (`papers.csv/json`, `papers_vlm.csv/json`) are updated in place.

> **Note:** `--incremental` is enabled by default — existing papers are always skipped. Use `--no-incremental` to force a full re-fetch.

---

## Usage

### Scraping

```bash
# Full scrape (2020–present)
python main.py

# Custom year range
python main.py --start-year 2023 --end-year 2025

# Limit results (for testing)
python main.py --max-results 100

# Incremental (skip existing)
python main.py --incremental

# Quick update (latest 7 days)
python main.py --update

# Check progress
python main.py --status
```

### Pipeline (Recommended)

```bash
# One-click: clean + VLM filter + classify all outputs
python pipeline.py

# Custom input
python pipeline.py --input output/papers.json
```

`pipeline.py` runs the following steps automatically:

1. **Load & Deduplicate** — Remove duplicate papers by `Paper_link`
2. **Clean** — Extract code URLs from abstracts, fill `code` field
3. **Classify All** — Label every paper as Method / Dataset / Survey / Application / Other
4. **Save** — Write cleaned `papers.csv` + `papers.json`
5. **Filter VLM** — Select VLM-related papers by keyword matching
6. **Classify VLM** — Refine categories for VLM subset
7. **Export** — Write `papers_vlm.csv/json` and `papers_vlm_annotated.json`

### Individual Tools

You can also run each step separately:

```bash
# Clean only
python clean.py --inplace

# VLM filter only
python filter_vlm.py --input output/papers.json

# Backfill exact dates for existing papers (if needed)
python backfill_dates_noneed.py
```

### PDF Download

```bash
# Scrape + download
python main.py --download

# Download only (from existing data)
python main.py --download-only
```

---

## CLI Reference

### `main.py`

| Flag | Description | Default |
|------|-------------|---------|
| `--start-year` | Start year | 2020 |
| `--end-year` | End year | 2026 |
| `--max-results` | Max papers to fetch | unlimited |
| `--output-dir` | Output directory | `output` |
| `--update` | Quick update (latest 7 days) | off |
| `--no-incremental` | Disable incremental, re-fetch all | off |
| `--incremental` | Skip existing papers | **on** |
| `--download` | Download PDFs | off |
| `--download-only` | Download PDFs only (skip scraping) | off |
| `--with-code` | Query Papers With Code for repos | off |
| `--status` | Show progress and exit | — |
| `-v, --verbose` | Verbose logging | off |

### `pipeline.py`

| Flag | Description | Default |
|------|-------------|---------|
| `--input` | Input JSON file | `output/papers.json` |
| `--output-dir` | Output directory | `output` |

---

## Output Schema

All outputs are available in both **CSV** and **JSON** format.

| Field | Description | Example |
|-------|-------------|---------|
| `Category` | Paper category (VLM output only) | Method, Dataset, Survey |
| `Type` | arXiv primary category | Computer Vision |
| `Subtype` | Secondary categories | Image and Video Processing |
| `Date` | Exact publication date | 2024-03-15 |
| `Month` | Publication month | 3 |
| `Year` | Publication year | 2024 |
| `Institute` | First author affiliation | (limited by arXiv data) |
| `Title` | Paper title | Hybrid Attention Network for... |
| `abbr.` | Abbreviation from title | HMANet |
| `Paper_link` | arXiv URL | http://arxiv.org/abs/2301.12345 |
| `Abstract` | Full abstract | ... |
| `code` | Code repository URL | https://github.com/... |
| `Publication` | Venue (journal/conference) | CVPR 2024 |
| `BibTex` | BibTeX citation | @article{...} |
| `Authors` | Author list | Alice, Bob, Charlie |

---

## Project Structure

```
rs-paper-hub/
├── main.py              # Scraper CLI entry point
├── pipeline.py          # One-click: clean + filter + classify
├── config.py            # Search configuration
├── scraper.py           # arXiv API scraper
├── parser.py            # Metadata parser & BibTeX generation
├── downloader.py        # PDF downloader with resume support
├── progress.py          # Progress tracker
├── clean.py             # Standalone data cleaning
├── filter_vlm.py        # Standalone VLM filter & classifier
├── backfill_dates.py    # Date backfill tool
├── pwc_client.py        # Papers With Code client
├── cleaning/
│   ├── abstract_cleaner.py   # Abstract URL extraction
│   ├── classifier.py         # Paper classifier (Method/Dataset/Survey/...)
│   └── filter/
│       └── vlm_filter.py     # VLM keyword rules
├── requirements.txt
└── output/
    ├── papers.csv/json            # All papers (cleaned)
    ├── papers_vlm.csv/json        # VLM subset with categories
    ├── papers_vlm_annotated.json  # Full list with VLM flags
    └── progress.json              # Scraping progress
```

---

## Search Scope

Papers are fetched from **all arXiv categories** where the title or abstract contains `"remote sensing"`. To customize, edit `SEARCH_QUERY` in [`config.py`](config.py):

```python
# Restrict to cs.CV only
SEARCH_QUERY = '(ti:"remote sensing" OR abs:"remote sensing") AND cat:cs.CV'
```

---

## Rate Limits

| Operation | Rate | Note |
|-----------|------|------|
| Metadata query | ~3s / request | Returns up to 100 results per request |
| PDF download | ~3s / file | Respect arXiv rate limits |

**Recommended workflow**: scrape metadata first (`python main.py`), then download PDFs separately (`python main.py --download-only`).

---

## Web Viewer

```bash
python3 -m http.server 8080
```

Open http://localhost:8080 — features include:

- **Relevance-ranked search** — Title matches prioritized over abstract matches
- **Multi-dimensional chart filtering** — Click year/type/category bars to filter, multi-select supported
- **Year range selection** — Single year or custom range via dropdown
- **Paper classification** — All papers auto-labeled (Method, Dataset, Survey, Application, etc.)
- **Today's new papers badge** — Shows `+N` count on the stats bar
- **Mobile-friendly** — Collapsible filter panel with responsive layout
- **BibTeX export** — One-click copy with modal preview
- **LaTeX rendering** — Math formulas rendered via KaTeX

---

## Notes

- `Institute` depends on arXiv affiliation data, which is often unavailable
- Downloaded PDFs and scraped months are tracked — no duplicates on re-run
- `progress.json` uses atomic writes — safe against interruption

---

## License

MIT
