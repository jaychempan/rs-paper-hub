#!/usr/bin/env python3
"""
arXiv Remote Sensing Paper Scraper — Web Fallback

Same pipeline as main.py but fetches papers by scraping arXiv HTML
instead of the arXiv API. Use when the API is unreachable.

Usage:
    python3 main_web.py --update          # same as main.py --update
    python3 main_web.py --max-results 50  # limit fetch count
"""

from __future__ import annotations

import os
import re
import json
import argparse
import logging
from datetime import datetime, timedelta, date

import pandas as pd

from config import OUTPUT_DIR, CSV_FILENAME, JSON_FILENAME
from web_scraper import fetch_papers_web

SAVE_COLUMNS = [
    "Category", "Type", "Subtype", "Date", "Month", "Year", "Institute",
    "Title", "abbr.", "Paper_link", "Abstract",
    "code", "Publication", "BibTex", "Authors", "_tasks", "_added_date",
    "arxiv_id",
]


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _strip_version(link: str) -> str:
    return re.sub(r'v\d+$', '', link) if link else link


def _normalize_paper(paper: dict) -> dict:
    """Ensure all SAVE_COLUMNS exist and no value is NaN/None."""
    out = {}
    for col in SAVE_COLUMNS:
        v = paper.get(col, "")
        if v is None or (isinstance(v, float) and (str(v) == "nan" or pd.isna(v))):
            v = ""
        out[col] = v
    # Preserve extra fields from pipeline (Category, _tasks, etc.)
    for k, v in paper.items():
        if k not in out:
            if v is None or (isinstance(v, float) and (str(v) == "nan" or pd.isna(v))):
                v = ""
            out[k] = v
    return out


def load_existing_papers(output_dir: str) -> list:
    """Load existing papers from JSON (preserves all fields without NaN issues)."""
    json_path = os.path.join(output_dir, JSON_FILENAME)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_results(papers: list, output_dir: str):
    """Save papers to CSV + JSON with no NaN values."""
    os.makedirs(output_dir, exist_ok=True)
    normalized = [_normalize_paper(p) for p in papers]

    # CSV — use all columns that appear in data
    df = pd.DataFrame(normalized)
    # Reorder: SAVE_COLUMNS first, then any extras
    extra_cols = [c for c in df.columns if c not in SAVE_COLUMNS]
    df = df[[c for c in SAVE_COLUMNS if c in df.columns] + extra_cols]
    df = df.fillna("")
    # Ensure no literal "nan" strings
    df = df.replace("nan", "")
    csv_path = os.path.join(output_dir, CSV_FILENAME)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"Saved {len(papers)} papers to {csv_path}")

    # JSON
    json_path = os.path.join(output_dir, JSON_FILENAME)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(papers)} papers to {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape arXiv remote sensing papers (web fallback)"
    )
    parser.add_argument(
        "--max-results", type=int, default=None,
        help="Max papers to fetch (default: all)"
    )
    parser.add_argument(
        "--output-dir", type=str, default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--with-code", action="store_true",
        help="Enable Papers With Code lookup for code repos"
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Quick update: only scrape recent 7 days and append new papers"
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to look back in update mode (default: 7)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose logging"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    os.makedirs(args.output_dir, exist_ok=True)

    date_from = date_to = None
    if args.update:
        date_to = datetime.now()
        date_from = date_to - timedelta(days=args.days)
        logger.info(
            f"Update mode: scraping {date_from.strftime('%Y-%m-%d')} "
            f"to {date_to.strftime('%Y-%m-%d')}"
        )

    # Step 1: Fetch via web scraping
    logger.info("Fetching papers via arXiv web scraper...")
    fetched = fetch_papers_web(
        max_results=args.max_results,
        date_from=date_from,
        date_to=date_to,
    )
    logger.info(f"Fetched {len(fetched)} papers from arXiv web")

    if not fetched:
        logger.warning("No papers found.")
        return

    # Step 2: Load existing papers and build index (by version-stripped link)
    existing_papers = load_existing_papers(args.output_dir)
    existing_index = {}
    for i, p in enumerate(existing_papers):
        base = _strip_version(p.get("Paper_link", ""))
        if base:
            existing_index[base] = i

    # Step 3: Only append truly new papers; do NOT overwrite existing ones
    today_str = date.today().isoformat()
    new_papers = []
    skipped = 0
    for p in fetched:
        base = _strip_version(p["Paper_link"])
        if base in existing_index:
            skipped += 1
            continue
        p["_added_date"] = today_str
        p = _normalize_paper(p)
        new_papers.append(p)

    logger.info(f"Incremental: {skipped} existing skipped, {len(new_papers)} new")

    if not new_papers:
        logger.info("No new papers to process.")
        return

    # Step 4: Enrich with code links (opt-in)
    if args.with_code:
        from tqdm import tqdm
        from pwc_client import PapersWithCodeClient
        logger.info("Querying Papers With Code for code repos...")
        pwc = PapersWithCodeClient()
        pbar = tqdm(total=len(new_papers), desc="Fetching code links")
        pwc.enrich_papers(new_papers, progress_callback=lambda i, t: pbar.update(1))
        pbar.close()
        code_count = sum(1 for p in new_papers if p.get("code"))
        logger.info(f"Found code repos for {code_count}/{len(new_papers)} papers")

    # Step 5: Append new papers to existing (existing papers untouched)
    all_papers = existing_papers + new_papers
    save_results(all_papers, args.output_dir)
    logger.info(f"Done! Added {len(new_papers)} new papers (total: {len(all_papers)})")


if __name__ == "__main__":
    main()
