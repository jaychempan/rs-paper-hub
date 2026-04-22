#!/usr/bin/env python3
"""
Import papers from saved arXiv search result HTML pages in html_inbox/.

Usage:
    python html_inbox_import.py                # Import and merge into papers.json
    python html_inbox_import.py --pipeline     # Import then run full pipeline
    python html_inbox_import.py --dry-run      # Parse only, don't write
"""

import os
import re
import json
import shutil
import argparse
import logging
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from config import CATEGORY_NAMES
from parser import extract_abbreviation, extract_publication

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

INBOX_DIR = "html_inbox"
OUTPUT_JSON = "output/papers.json"
DONE_DIR = os.path.join(INBOX_DIR, "done")

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _strip_version(link: str) -> str:
    return re.sub(r"v\d+$", "", link) if link else link


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _generate_bibtex(arxiv_id: str, title: str, authors: str, year: int) -> str:
    author_list = [a.strip() for a in authors.split(",")]
    if author_list:
        first_last = author_list[0].split()[-1].lower()
        first_last = re.sub(r"[^a-z]", "", first_last)
    else:
        first_last = "unknown"

    title_word = re.sub(r"[^a-z]", "", title.split()[0].lower()) if title else "untitled"
    cite_key = f"{first_last}{year}{title_word}"

    author_str = " and ".join(author_list)
    entry_id = f"http://arxiv.org/abs/{arxiv_id}"

    return (
        f"@article{{{cite_key},\n"
        f"  title={{{title}}},\n"
        f"  author={{{author_str}}},\n"
        f"  journal={{arXiv preprint arXiv:{arxiv_id}}},\n"
        f"  year={{{year}}},\n"
        f"  url={{{entry_id}}}\n"
        f"}}"
    )


def _extract_code_from_text(text: str) -> str:
    match = re.search(r"(https?://github\.com/[^\s,;)]+)", text)
    return match.group(1).rstrip(".") if match else ""


def parse_html_file(filepath: str) -> list[dict]:
    """Parse a saved arXiv search results HTML file into paper records."""
    logger.info(f"Parsing {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    papers = []
    for item in soup.select("li.arxiv-result"):
        try:
            paper = _parse_result_item(item)
            if paper:
                papers.append(paper)
        except Exception as e:
            title_el = item.select_one("p.title")
            title_hint = title_el.get_text(strip=True)[:60] if title_el else "?"
            logger.warning(f"Failed to parse entry '{title_hint}': {e}")

    logger.info(f"  Parsed {len(papers)} papers from {os.path.basename(filepath)}")
    return papers


def _parse_result_item(item) -> dict | None:
    # arXiv ID and link
    link_el = item.select_one("p.list-title a")
    if not link_el:
        return None
    href = link_el.get("href", "")
    arxiv_id = href.rstrip("/").split("/")[-1]
    paper_link = f"http://arxiv.org/abs/{arxiv_id}"

    # Categories
    tags = item.select("div.tags span.tag")
    cat_codes = []
    for tag in tags:
        code = tag.get_text(strip=True)
        if code:
            cat_codes.append(code)

    primary_cat = cat_codes[0] if cat_codes else ""
    type_name = CATEGORY_NAMES.get(primary_cat, primary_cat)
    secondary = [c for c in cat_codes[1:] if c != primary_cat]
    subtype = "; ".join(CATEGORY_NAMES.get(c, c) for c in secondary[:3])

    # Title
    title_el = item.select_one("p.title.is-5")
    title = _clean_text(title_el.get_text()) if title_el else ""

    # Authors
    author_els = item.select("p.authors a")
    authors = ", ".join(a.get_text(strip=True) for a in author_els)

    # Abstract (full version, strip "Less" link)
    abstract = ""
    abstract_full = item.select_one("span.abstract-full")
    if abstract_full:
        for link in abstract_full.select("a"):
            link.decompose()
        abstract = _clean_text(abstract_full.get_text())
    else:
        abstract_short = item.select_one("span.abstract-short")
        if abstract_short:
            for link in abstract_short.select("a"):
                link.decompose()
            abstract = _clean_text(abstract_short.get_text())

    # Date: "Submitted DD Month, YYYY"
    date_str, month, year = "", 0, 0
    for p in item.select("p.is-size-7"):
        text = p.get_text()
        m = re.search(r"Submitted\s+(\d{1,2})\s+(\w+),?\s+(\d{4})", text)
        if m:
            day = int(m.group(1))
            month_name = m.group(2).lower()
            year = int(m.group(3))
            month = MONTH_MAP.get(month_name, 0)
            if month:
                try:
                    date_str = datetime(year, month, day).strftime("%Y-%m-%d")
                except ValueError:
                    date_str = f"{year}-{month:02d}-{day:02d}"
            break

    # Comments / Publication
    comment = ""
    comment_el = item.select_one("p.comments span.has-text-grey-dark")
    if comment_el:
        comment = _clean_text(comment_el.get_text())

    publication = extract_publication(comment) if comment else ""

    # Code URL from comment or abstract
    code = _extract_code_from_text(comment) or _extract_code_from_text(abstract)

    return {
        "Type": type_name,
        "Subtype": subtype,
        "Date": date_str,
        "Month": month,
        "Year": year,
        "Institute": "",
        "Title": title,
        "abbr.": extract_abbreviation(title),
        "Paper_link": paper_link,
        "Abstract": abstract,
        "code": code,
        "Publication": publication,
        "BibTex": _generate_bibtex(arxiv_id, title, authors, year),
        "Authors": authors,
        "_added_date": date.today().isoformat(),
        "Category": "",
        "_tasks": "",
    }


def load_existing_papers(path: str) -> tuple[list[dict], set[str]]:
    """Load existing papers and return (papers, set_of_version_stripped_links)."""
    if not os.path.exists(path):
        return [], set()
    with open(path, "r", encoding="utf-8") as f:
        papers = json.load(f)
    links = {_strip_version(p.get("Paper_link", "")) for p in papers}
    return papers, links


def import_from_inbox(inbox_dir: str, output_path: str, dry_run: bool = False, days: int = 3) -> int:
    html_files = sorted(Path(inbox_dir).glob("*.html"))
    if not html_files:
        logger.info(f"No HTML files found in {inbox_dir}/")
        return 0

    # Parse all HTML files
    new_papers = []
    for html_file in html_files:
        new_papers.extend(parse_html_file(str(html_file)))

    if not new_papers:
        logger.info("No papers parsed from HTML files.")
        return 0

    # Filter: only keep papers submitted within recent N days
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    before_filter = len(new_papers)
    new_papers = [p for p in new_papers if p.get("Date", "") >= cutoff]
    skipped = before_filter - len(new_papers)
    if skipped:
        logger.info(f"  Skipped {skipped} papers older than {days} days (before {cutoff})")

    if not new_papers:
        logger.info("No recent papers to import.")
        return 0

    # Deduplicate within the batch
    seen = {}
    for p in new_papers:
        key = _strip_version(p["Paper_link"])
        seen[key] = p
    new_papers = list(seen.values())

    # Load existing and filter duplicates
    existing, existing_links = load_existing_papers(output_path)
    unique = [p for p in new_papers if _strip_version(p["Paper_link"]) not in existing_links]

    logger.info(f"Parsed {len(new_papers)} papers total, {len(unique)} are new")

    if not unique:
        logger.info("All papers already exist in papers.json. Nothing to do.")
        return 0

    if dry_run:
        logger.info("[DRY RUN] Would add these papers:")
        for p in unique:
            logger.info(f"  - {p['Title'][:80]}")
        return len(unique)

    # Merge and save
    combined = existing + unique
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(combined)} papers to {output_path} (+{len(unique)} new)")

    # Move processed HTML files to done/
    os.makedirs(DONE_DIR, exist_ok=True)
    for html_file in html_files:
        dest = os.path.join(DONE_DIR, html_file.name)
        shutil.move(str(html_file), dest)
        logger.info(f"  Moved {html_file.name} -> done/")

    return len(unique)


def main():
    ap = argparse.ArgumentParser(description="Import papers from HTML inbox")
    ap.add_argument("--inbox", default=INBOX_DIR, help="HTML inbox directory")
    ap.add_argument("--output", default=OUTPUT_JSON, help="Output papers.json path")
    ap.add_argument("--days", type=int, default=3, help="Only import papers from recent N days (default: 3)")
    ap.add_argument("--dry-run", action="store_true", help="Parse only, don't write")
    ap.add_argument("--pipeline", action="store_true", help="Run pipeline after import")
    args = ap.parse_args()

    added = import_from_inbox(args.inbox, args.output, dry_run=args.dry_run, days=args.days)

    if added > 0 and args.pipeline and not args.dry_run:
        logger.info("Running pipeline...")
        from pipeline import run
        run(args.output, os.path.dirname(args.output) or "output")
    elif added > 0 and not args.dry_run:
        logger.info("Tip: run `python pipeline.py` to classify and tag the new papers.")


if __name__ == "__main__":
    main()
