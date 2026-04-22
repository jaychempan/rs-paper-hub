"""arXiv web scraper fallback — used when the arXiv API is unreachable."""

from __future__ import annotations

import re
import time
import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import CATEGORY_NAMES

logger = logging.getLogger(__name__)

ARXIV_SEARCH_URL = "https://arxiv.org/search/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RS-Paper-Hub/1.0)"}
PAGE_SIZE = 200
REQUEST_DELAY = 3.0
MAX_RETRIES = 3


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(submitted_text: str) -> datetime | None:
    """Parse 'Submitted 21 April, 2026' to datetime."""
    m = re.search(r"Submitted\s+(\d{1,2})\s+(\w+),?\s+(\d{4})", submitted_text)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%d %B %Y")
        except ValueError:
            pass
    return None


def _extract_abbreviation(title: str) -> str:
    matches = re.findall(r"\(([A-Z][A-Za-z0-9\-]{0,9})\)", title)
    return matches[-1] if matches else ""


def _extract_publication(comment: str) -> str:
    if not comment:
        return ""
    venue_patterns = [
        r"(?:accepted|published|appear|to appear)\s+(?:at|in|by)\s+(.+?)(?:\.|,|$)",
        r"((?:CVPR|ICCV|ECCV|NeurIPS|ICML|AAAI|IJCAI|ICLR|ACM MM|WACV|BMVC|"
        r"IEEE\s+\w+|ISPRS|GRSL|TGRS|Remote Sensing|GeoAI|EarthVision)"
        r"[^.,]*\d{4})",
        r"(\d+\s+pages?,?\s*\d*\s*figures?)",
    ]
    for pattern in venue_patterns:
        match = re.search(pattern, comment, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return comment.strip()


def _generate_bibtex(arxiv_id: str, title: str, authors: str, year: int, entry_url: str) -> str:
    author_list = [a.strip() for a in authors.split(",")]
    first_last = re.sub(r"[^a-z]", "", author_list[0].split()[-1].lower()) if author_list else "unknown"
    title_word = re.sub(r"[^a-z]", "", title.split()[0].lower()) if title else "untitled"
    cite_key = f"{first_last}{year}{title_word}"
    author_str = " and ".join(author_list)
    return (
        f"@article{{{cite_key},\n"
        f"  title={{{title}}},\n"
        f"  author={{{author_str}}},\n"
        f"  journal={{arXiv preprint arXiv:{arxiv_id}}},\n"
        f"  year={{{year}}},\n"
        f"  url={{{entry_url}}}\n"
        f"}}"
    )


def _parse_result_item(li) -> dict | None:
    """Parse a single <li class="arxiv-result"> into a paper dict."""
    # arXiv ID & link
    title_p = li.find("p", class_="list-title")
    if not title_p:
        return None
    link_tag = title_p.find("a")
    if not link_tag:
        return None
    entry_url = link_tag["href"]
    if not entry_url.startswith("http"):
        entry_url = "https://arxiv.org" + entry_url
    arxiv_id = entry_url.split("/abs/")[-1]

    # Categories
    tags = li.find_all("span", class_="tag")
    categories = [t.get_text(strip=True) for t in tags]
    primary_cat = categories[0] if categories else ""
    cat_type = CATEGORY_NAMES.get(primary_cat, primary_cat)
    others = categories[1:]
    subtype = "; ".join(CATEGORY_NAMES.get(c, c) for c in others[:3]) if others else ""

    # Title
    title_tag = li.find("p", class_="title")
    title = _clean_text(title_tag.get_text()) if title_tag else ""

    # Authors
    authors_p = li.find("p", class_="authors")
    if authors_p:
        author_links = authors_p.find_all("a")
        authors = ", ".join(a.get_text(strip=True) for a in author_links)
    else:
        authors = ""

    # Abstract (full version)
    abstract = ""
    abstract_full = li.find("span", class_="abstract-full")
    if abstract_full:
        for a_tag in abstract_full.find_all("a"):
            a_tag.decompose()
        abstract = _clean_text(abstract_full.get_text())
    else:
        abstract_short = li.find("span", class_="abstract-short")
        if abstract_short:
            for a_tag in abstract_short.find_all("a"):
                a_tag.decompose()
            abstract = _clean_text(abstract_short.get_text())

    # Submitted date
    date_obj = None
    for p in li.find_all("p", class_="is-size-7"):
        text = p.get_text()
        if "Submitted" in text:
            date_obj = _parse_date(text)
            break

    if not date_obj:
        date_obj = datetime.now()

    # Comments
    comment = ""
    comments_p = li.find("p", class_="comments")
    if comments_p:
        spans = comments_p.find_all("span", class_="has-text-grey-dark")
        if spans:
            comment = _clean_text(spans[0].get_text())

    return {
        "Type": cat_type,
        "Subtype": subtype,
        "Date": date_obj.strftime("%Y-%m-%d"),
        "Month": date_obj.month,
        "Year": date_obj.year,
        "Institute": "",
        "Title": title,
        "abbr.": _extract_abbreviation(title),
        "Paper_link": entry_url,
        "Abstract": abstract,
        "code": "",
        "Publication": _extract_publication(comment),
        "BibTex": _generate_bibtex(arxiv_id, title, authors, date_obj.year, entry_url),
        "arxiv_id": arxiv_id,
        "Authors": authors,
    }


def fetch_papers_web(
    max_results: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    """
    Scrape arXiv search results via HTML.
    Returns paper dicts in the same format as parse_results() from parser.py.

    Uses the same search terms as config.SEARCH_QUERY but via the web interface.
    """
    all_papers = []
    start = 0
    queries = ['"remote sensing"', '"earth observation"']

    for query_term in queries:
        start = 0
        seen_ids = {p["arxiv_id"] for p in all_papers}

        while True:
            params = {
                "query": query_term,
                "searchtype": "all",
                "abstracts": "show",
                "order": "-announced_date_first",
                "size": str(PAGE_SIZE),
                "start": str(start),
            }

            retry = 0
            response = None
            while retry <= MAX_RETRIES:
                try:
                    response = requests.get(
                        ARXIV_SEARCH_URL, params=params, headers=HEADERS, timeout=60
                    )
                    response.raise_for_status()
                    break
                except Exception as e:
                    retry += 1
                    if retry > MAX_RETRIES:
                        logger.error(f"Failed after {MAX_RETRIES} retries: {e}")
                        return all_papers
                    wait = REQUEST_DELAY * (2 ** retry)
                    logger.warning(f"Retry {retry}, waiting {wait}s: {e}")
                    time.sleep(wait)

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("li", class_="arxiv-result")

            if not items:
                break

            page_new = 0
            stop_early = False
            for li in items:
                paper = _parse_result_item(li)
                if not paper:
                    continue

                # Date filtering
                if date_from or date_to:
                    paper_date = datetime.strptime(paper["Date"], "%Y-%m-%d")
                    if date_from and paper_date < date_from:
                        stop_early = True
                        break
                    if date_to and paper_date > date_to:
                        continue

                if paper["arxiv_id"] not in seen_ids:
                    seen_ids.add(paper["arxiv_id"])
                    all_papers.append(paper)
                    page_new += 1

                if max_results and len(all_papers) >= max_results:
                    stop_early = True
                    break

            logger.info(
                f"  [{query_term}] page {start // PAGE_SIZE + 1}: "
                f"{len(items)} items, {page_new} new (total: {len(all_papers)})"
            )

            if stop_early:
                break
            if len(items) < PAGE_SIZE:
                break

            start += PAGE_SIZE
            time.sleep(REQUEST_DELAY)

    logger.info(f"Web scraper: total {len(all_papers)} papers fetched")
    return all_papers
