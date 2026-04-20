"""Filter papers related to UAV (Unmanned Aerial Vehicles) in Remote Sensing."""

import re

# ============================================================
# Keyword lists
# ============================================================

# 核心概念关键词 — UAV 直接表述（命中即入选）
CORE_KEYWORDS = [
    r"\bUAV\b",
    r"\bUAVs\b",
    r"\bdrone\b",
    r"\bdrones\b",
    r"unmanned\s+aerial\s+vehicle",
    r"unmanned\s+aerial\s+system",
    r"\bUAS\b",
    r"\bsUAS\b",
    r"quadcopter\b",
    r"quadrotor\b",
    r"multicopter\b",
    r"multirotor\b",
    r"rotorcraft\b",
    r"micro[\-\s]?aerial\s+vehicle",
    r"\bMAV\b",
]

# UAV 相关应用与场景关键词 — 需要结合遥感/地理上下文
TASK_KEYWORDS = [
    # UAV-based remote sensing applications
    r"UAV[\-\s]based\s+(?:remote\s+sensing|mapping|monitoring|classification|detection|imaging|survey)",
    r"drone[\-\s]based\s+(?:remote\s+sensing|mapping|monitoring|classification|detection|imaging|survey)",
    r"aerial\s+(?:photogrammetry|mapping|survey|monitoring)",
    r"(?:UAV|drone|aerial).{0,30}precision\s+agriculture",
    r"precision\s+agriculture.{0,30}(?:UAV|drone|aerial)",
    r"(?:UAV|drone|aerial).{0,30}crop\s+monitoring",
    r"(?:UAV|drone|aerial).{0,30}vegetation\s+(?:mapping|monitoring|index)",
    r"(?:UAV|drone|aerial).{0,30}forest\s+(?:monitoring|inventory|mapping)",
    # UAV photogrammetry and 3D
    r"(?:UAV|drone|aerial).{0,30}(?:structure[\-\s]from[\-\s]motion|SfM)",
    r"(?:UAV|drone|aerial).{0,30}ortho[\-\s]?mosaic",
    r"(?:UAV|drone|aerial).{0,30}point\s+cloud",
    r"(?:UAV|drone|aerial).{0,30}3D\s+reconstruction",
    r"(?:UAV|drone|aerial).{0,30}digital\s+(?:elevation|surface|terrain)\s+model",
    r"(?:UAV|drone|aerial).{0,30}(?:DEM|DSM|DTM)\b",
    # UAV navigation and planning
    r"(?:UAV|drone).{0,30}path[\-\s]?planning",
    r"(?:UAV|drone).{0,30}coverage\s+planning",
    r"(?:UAV|drone).{0,30}(?:obstacle|collision)\s+(?:avoidance|detection)",
    r"(?:UAV|drone).{0,30}(?:navigation|localization|SLAM)",
    r"(?:UAV|drone).{0,30}(?:autonomous|self[\-\s]?driving|autopilot)",
    # Low-altitude remote sensing
    r"low[\-\s]?altitude\s+(?:remote\s+sensing|aerial|imaging|platform)",
]

# 全部合并
ALL_KEYWORDS = CORE_KEYWORDS + TASK_KEYWORDS

# 预编译
_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in ALL_KEYWORDS]


def is_uav_related(title: str, abstract: str) -> tuple[bool, list[str]]:
    """
    Check if a paper is related to UAVs in Remote Sensing.

    Returns:
        (is_match, matched_keywords)
    """
    text = f"{title} {abstract}"
    matched = []

    for pattern, keyword in zip(_PATTERNS, ALL_KEYWORDS):
        if pattern.search(text):
            matched.append(keyword)

    return len(matched) > 0, matched


def filter_uav_papers(papers: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter papers related to UAVs.

    Returns:
        (matched_papers, all_papers_with_uav_flag)
        - matched_papers: only UAV-related papers (with _uav_keywords field)
        - all_papers_with_uav_flag: all papers with _is_uav and _uav_keywords fields
    """
    matched = []
    annotated = []

    for paper in papers:
        title = str(paper.get("Title", ""))
        abstract = str(paper.get("Abstract", ""))
        is_match, keywords = is_uav_related(title, abstract)

        paper_copy = dict(paper)
        paper_copy["_is_uav"] = is_match
        paper_copy["_uav_keywords"] = "; ".join(keywords) if keywords else ""
        annotated.append(paper_copy)

        if is_match:
            matched.append(paper_copy)

    return matched, annotated
