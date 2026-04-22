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
from datetime import datetime, timedelta

import pandas as pd

from config import OUTPUT_DIR, CSV_FILENAME, JSON_FILENAME
from web_scraper import fetch_papers_web


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _strip_version(link: str) -> str:
    return re.sub(r'v\d+$', '', link) if link else link


def load_existing(output_dir: str) -> set:
    csv_path = os.path.join(output_dir, CSV_FILENAME)
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            return set(_strip_version(link) for link in df["Paper_link"].dropna())
        except Exception:
            pass
    return set()


def save_results(papers: list, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    columns = [
        "Type", "Subtype", "Date", "Month", "Year", "Institute",
        "Title", "abbr.", "Paper_link", "Abstract",
        "code", "Publication", "BibTex", "Authors", "_added_date",
    ]
    df = pd.DataFrame(papers, columns=columns)
    csv_path = os.path.join(output_dir, CSV_FILENAME)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"Saved {len(papers)} papers to {csv_path}")

    json_path = os.path.join(output_dir, JSON_FILENAME)
    clean_papers = [{k: v for k, v in p.items() if k in columns} for p in papers]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_papers, f, ensure_ascii=False, indent=2)
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
        "--incremental", action="store_true", default=True,
        help="Skip papers already in output CSV (default: on)"
    )
    parser.add_argument(
        "--no-incremental", action="store_false", dest="incremental",
        help="Disable incremental mode"
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
        args.incremental = True
        logger.info(
            f"Update mode: scraping {date_from.strftime('%Y-%m-%d')} "
            f"to {date_to.strftime('%Y-%m-%d')}"
        )

    # Step 1: Fetch via web scraping
    logger.info("Fetching papers via arXiv web scraper...")
    papers = fetch_papers_web(
        max_results=args.max_results,
        date_from=date_from,
        date_to=date_to,
    )
    logger.info(f"Fetched {len(papers)} papers from arXiv web")

    if not papers:
        logger.warning("No papers found.")
        return

    # Step 2: Incremental — filter out existing, track version updates
    updated_links = {}
    if args.incremental:
        existing = load_existing(args.output_dir)
        before = len(papers)
        new_papers = []
        for p in papers:
            base = _strip_version(p["Paper_link"])
            if base not in existing:
                new_papers.append(p)
            else:
                updated_links[base] = p
        papers = new_papers
        logger.info(
            f"Incremental: {before - len(papers)} existing skipped, "
            f"{len(papers)} new"
        )
        if updated_links:
            logger.info(f"  {len(updated_links)} papers have version updates")

    if not papers and not updated_links:
        logger.info("No new papers to process.")
        return

    # Step 3: Enrich with code links (opt-in)
    if args.with_code:
        from tqdm import tqdm
        from pwc_client import PapersWithCodeClient
        logger.info("Querying Papers With Code for code repos...")
        pwc = PapersWithCodeClient()
        pbar = tqdm(total=len(papers), desc="Fetching code links")
        pwc.enrich_papers(papers, progress_callback=lambda i, t: pbar.update(1))
        pbar.close()
        code_count = sum(1 for p in papers if p.get("code"))
        logger.info(f"Found code repos for {code_count}/{len(papers)} papers")

    # Step 4: Save results
    if args.incremental:
        csv_path = os.path.join(args.output_dir, CSV_FILENAME)
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            if updated_links:
                def _apply_update(row):
                    base = _strip_version(str(row.get("Paper_link", "")))
                    if base in updated_links:
                        upd = updated_links[base]
                        row["Paper_link"] = upd["Paper_link"]
                        row["Title"] = upd.get("Title", row["Title"])
                    return row
                existing_df = existing_df.apply(_apply_update, axis=1)
            new_df = pd.DataFrame(papers)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            papers = combined.to_dict("records")

    save_results(papers, args.output_dir)
    logger.info("Done!")


if __name__ == "__main__":
    main()
