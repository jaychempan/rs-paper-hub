#!/usr/bin/env python3
"""
Filter UAV-related papers from cleaned data.

Usage:
    python filter_uav.py                          # Default: read papers.json
    python filter_uav.py --input output/x.json    # Custom input
    python filter_uav.py --dry-run                 # Preview without saving
"""

import os
import json
import argparse
import logging

import pandas as pd

from cleaning.filter.uav_filter import filter_uav_papers
from cleaning.classifier import classify_papers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Filter UAV-related papers")
    parser.add_argument(
        "--input", type=str, default="output/papers.json",
        help="Input JSON file (default: output/papers.json)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="output",
        help="Output directory (default: output)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview matches without saving"
    )
    args = parser.parse_args()

    # Load
    logger.info(f"Loading {args.input}...")
    with open(args.input, "r", encoding="utf-8") as f:
        papers = json.load(f)
    logger.info(f"Loaded {len(papers)} papers")

    # Filter
    matched, annotated = filter_uav_papers(papers)
    logger.info(f"UAV-related papers: {len(matched)} / {len(papers)}")

    # Show keyword distribution
    from collections import Counter
    keyword_counter = Counter()
    for p in matched:
        for kw in p["_uav_keywords"].split("; "):
            if kw:
                keyword_counter[kw] += 1
    logger.info("Top matched keywords:")
    for kw, count in keyword_counter.most_common(15):
        logger.info(f"  {kw}: {count}")

    # Year distribution
    year_counter = Counter(p.get("Year", "?") for p in matched)
    logger.info("Year distribution:")
    for year in sorted(year_counter):
        logger.info(f"  {year}: {year_counter[year]}")

    if args.dry_run:
        classify_papers(matched)
        cat_counter = Counter(p.get("Category", "?") for p in matched)
        logger.info("Category distribution:")
        for cat, count in cat_counter.most_common():
            logger.info(f"  {cat}: {count}")
        logger.info("Dry run - showing first 10 matches:")
        for p in matched[:10]:
            logger.info(f"  [{p.get('Year')}] [{p.get('Category')}] {p['Title'][:65]}...")
            logger.info(f"       keywords: {p['_uav_keywords']}")
        return

    # Classify
    logger.info("Classifying papers (Dataset / Method / Survey / ...)...")
    classify_papers(matched)

    cat_counter = Counter(p.get("Category", "?") for p in matched)
    logger.info("Category distribution:")
    for cat, count in cat_counter.most_common():
        logger.info(f"  {cat}: {count}")

    # Save
    os.makedirs(args.output_dir, exist_ok=True)

    columns = [
        "Category", "Type", "Subtype", "Date", "Month", "Year", "Institute",
        "Title", "abbr.", "Paper_link", "Abstract",
        "code", "Publication", "BibTex", "Authors", "_tasks",
    ]

    uav_papers = [{k: v for k, v in p.items() if k in columns} for p in matched]

    csv_path = os.path.join(args.output_dir, "papers_uav.csv")
    df = pd.DataFrame(uav_papers, columns=columns).fillna("")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(uav_papers)} UAV papers to {csv_path}")

    json_path = os.path.join(args.output_dir, "papers_uav.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(uav_papers, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved to {json_path}")

    # Also save annotated full list
    annotated_path = os.path.join(args.output_dir, "papers_uav_annotated.json")
    with open(annotated_path, "w", encoding="utf-8") as f:
        json.dump(annotated, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved annotated full list to {annotated_path}")


if __name__ == "__main__":
    main()
