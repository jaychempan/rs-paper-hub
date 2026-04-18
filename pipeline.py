#!/usr/bin/env python3
"""
One-click pipeline: clean all data + filter VLM + classify.

Usage:
    python pipeline.py                # Process output/papers.json
    python pipeline.py --input x.json # Custom input
"""

import os
import json
import argparse
import logging
from collections import Counter

import pandas as pd

from cleaning.abstract_cleaner import clean_abstract
from cleaning.filter.vlm_filter import filter_vlm_papers
from cleaning.classifier import classify_papers
from cleaning.task_tagger import tag_all_papers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# All output columns
ALL_COLUMNS = [
    "Category", "Type", "Subtype", "Date", "Month", "Year", "Institute",
    "Title", "abbr.", "Paper_link", "Abstract",
    "code", "Publication", "BibTex", "Authors", "_tasks",
]

VLM_COLUMNS = ["Category"] + ALL_COLUMNS


def save(papers: list[dict], csv_path: str, json_path: str, columns: list[str]):
    """Save papers to CSV + JSON, NaN replaced with empty string."""
    df = pd.DataFrame(papers, columns=columns).fillna("")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    clean = [
        {k: ("" if pd.isna(v) else v) for k, v in p.items() if k in columns}
        for p in papers
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    logger.info(f"  -> {csv_path} ({len(papers)} rows)")
    logger.info(f"  -> {json_path}")


def run(input_path: str, output_dir: str):
    # ── Load ──────────────────────────────────────────────
    logger.info(f"Loading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        papers = json.load(f)
    logger.info(f"Loaded {len(papers)} papers")

    # ── Deduplicate by Paper_link (keep last occurrence) ──
    before = len(papers)
    seen = {}
    for p in papers:
        link = p.get("Paper_link", "")
        seen[link if link else id(p)] = p
    papers = list(seen.values())
    if len(papers) < before:
        logger.info(f"  Deduplicated: {before} -> {len(papers)} ({before - len(papers)} duplicates removed)")

    # ── Step 1: Clean abstracts → fill code field ─────────
    logger.info("[1/4] Cleaning abstracts & extracting code URLs...")
    code_filled = 0
    for p in papers:
        old_code = p.get("code", "")
        clean_abstract(p)
        if (not old_code or str(old_code) in ("", "nan")) and p.get("code") and str(p["code"]) not in ("", "nan"):
            code_filled += 1
    logger.info(f"  Code field filled from abstract: {code_filled}")

    # ── Step 2: Classify all papers ────────────────────────
    logger.info("[2/6] Classifying all papers...")
    classify_papers(papers)

    # ── Step 2.5: Tag tasks ───────────────────────────────
    logger.info("[3/6] Tagging tasks from title & abstract...")
    tag_all_papers(papers)


    all_cat_counter = Counter(p.get("Category", "Other") for p in papers)
    for cat, count in all_cat_counter.most_common():
        logger.info(f"  {cat}: {count}")

    # ── Step 3: Save cleaned full dataset ─────────────────
    logger.info("[4/6] Saving cleaned dataset...")
    save(
        papers,
        os.path.join(output_dir, "papers.csv"),
        os.path.join(output_dir, "papers.json"),
        ALL_COLUMNS,
    )

    # ── Step 4: Filter VLM papers ─────────────────────────
    logger.info("[5/6] Filtering VLM-related papers...")
    matched, annotated = filter_vlm_papers(papers)
    logger.info(f"  VLM-related: {len(matched)} / {len(papers)}")

    # ── Step 5: Classify VLM papers ───────────────────────
    logger.info("[6/6] Classifying VLM papers...")
    classify_papers(matched)


    cat_counter = Counter(p.get("Category", "Other") for p in matched)
    for cat, count in cat_counter.most_common():
        logger.info(f"  {cat}: {count}")

    year_counter = Counter(p.get("Year", "?") for p in matched)
    logger.info("  Year distribution:")
    for year in sorted(year_counter):
        logger.info(f"    {year}: {year_counter[year]}")

    # ── Save VLM outputs ──────────────────────────────────
    logger.info("Saving VLM outputs...")
    save(
        matched,
        os.path.join(output_dir, "papers_vlm.csv"),
        os.path.join(output_dir, "papers_vlm.json"),
        VLM_COLUMNS,
    )

    # Annotated full list
    annotated_path = os.path.join(output_dir, "papers_vlm_annotated.json")
    with open(annotated_path, "w", encoding="utf-8") as f:
        json.dump(annotated, f, ensure_ascii=False, indent=2)
    logger.info(f"  -> {annotated_path}")

    # ── Summary ───────────────────────────────────────────
    logger.info("=" * 50)
    logger.info(f"Done! Total: {len(papers)} | VLM: {len(matched)}")
    logger.info(f"  papers.csv/json        - all {len(papers)} papers (cleaned)")
    logger.info(f"  papers_vlm.csv/json    - {len(matched)} VLM papers (with Category)")
    logger.info(f"  papers_vlm_annotated.json - full list with VLM flags")


def main():
    parser = argparse.ArgumentParser(description="One-click: clean + filter + classify")
    parser.add_argument(
        "--input", type=str, default="output/papers.json",
        help="Input JSON file (default: output/papers.json)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Output directory (default: output)"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    run(args.input, args.output_dir)


if __name__ == "__main__":
    main()
