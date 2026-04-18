"""Tag papers with RS/VLM task labels based on title and abstract keywords."""

import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Task definitions: abbreviation -> (full name, keyword patterns)
# Each keyword is compiled as a case-insensitive regex matching word boundaries.
TASK_DEFINITIONS: dict[str, tuple[str, list[str]]] = {
    "CLS": ("Classification", [
        r"classification",
        r"scene\s+classification",
        r"land[\s\-]?use\s+classification",
        r"image\s+classification",
        r"land[\s\-]?cover\s+classification",
        r"scene\s+recognition",
    ]),
    "ITR": ("Image-Text Retrieval", [
        r"image[\-\s]text\s+retrieval",
        r"text[\-\s]image\s+retrieval",
        r"cross[\-\s]modal\s+retrieval",
        r"vision[\-\s]language\s+retrieval",
        r"remote\s+sensing\s+retrieval",
        r"image\s+retrieval",
    ]),
    "GeoLoc": ("Geolocation", [
        r"geolocation",
        r"geo[\-\s]?locali[sz]ation",
        r"image\s+geolocation",
        r"place\s+recognition",
        r"geo[\-\s]?tagging",
        r"visual\s+place\s+recognition",
        r"city[\-\s]?scale\s+locali[sz]ation",
    ]),
    "VQA": ("Visual Question Answering", [
        r"\bVQA\b",
        r"visual\s+question\s+answering",
        r"\bRSVQA\b",
        r"remote\s+sensing\s+VQA",
        r"visual\s+dialogue",
        r"visual\s+dialog",
    ]),
    "IC": ("Image Captioning", [
        r"image\s+captioning",
        r"caption\s+generation",
        r"\bcaptioning\b",
        r"remote\s+sensing\s+captioning",
        r"image\s+description\s+generation",
        r"change\s+captioning",
        r"scene\s+description",
    ]),
    "CD": ("Change Detection", [
        r"change\s+detection",
        r"bi[\-\s]?temporal",
        r"multi[\-\s]?temporal\s+change",
        r"change\s+captioning",
        r"temporal\s+change\s+analysis",
    ]),
    "OD": ("Object Detection", [
        r"object\s+detection",
        r"target\s+detection",
        r"vehicle\s+detection",
        r"ship\s+detection",
        r"airplane\s+detection",
        r"aircraft\s+detection",
        r"building\s+detection",
        r"car\s+detection",
        r"oriented\s+object\s+detection",
        r"rotated\s+object\s+detection",
        r"oriented\s+bounding\s+box",
        r"\bOBB\b",
    ]),
    "VG": ("Visual Grounding", [
        r"visual\s+grounding",
        r"\bgrounding\b",
        r"phrase\s+grounding",
        r"referring\s+expression\s+comprehension",
        r"text[\-\s]?guided\s+locali[sz]ation",
    ]),
    "SEG": ("Segmentation", [
        r"referring\s+expression\s+segmentation",
        r"referring\s+segmentation",
        r"semantic\s+segmentation",
        r"instance\s+segmentation",
        r"panoptic\s+segmentation",
        r"land[\s\-]?cover\s+segmentation",
        r"scene\s+segmentation",
        r"pixel[\-\s]?wise\s+classification",
        r"building\s+segmentation",
        r"road\s+segmentation",
    ]),
    "SR": ("Super-Resolution", [
        r"super[\-\s]?resolution",
        r"image\s+enhancement",
        r"spatial\s+resolution\s+enhancement",
        r"image\s+restoration",
        r"image\s+denoising",
    ]),
    "3D": ("3D Reconstruction", [
        r"3D\s+reconstruction",
        r"point\s+cloud",
        r"depth\s+estimation",
        r"stereo\s+matching",
        r"height\s+estimation",
        r"digital\s+elevation\s+model",
        r"\bDEM\b",
        r"\bDSM\b",
        r"surface\s+model",
    ]),
}

# Full name lookup
TASK_NAMES: dict[str, str] = {abbr: name for abbr, (name, _) in TASK_DEFINITIONS.items()}

# Pre-compile all patterns
_COMPILED_TASKS: dict[str, list[re.Pattern]] = {
    abbr: [re.compile(kw, re.IGNORECASE) for kw in keywords]
    for abbr, (_, keywords) in TASK_DEFINITIONS.items()
}


def tag_tasks(title: str, abstract: str) -> list[str]:
    """Match a paper's title+abstract against all task patterns.

    Returns:
        List of matched task abbreviations (e.g. ["CLS", "OD"]).
    """
    text = f"{title} {abstract}"
    matched = []
    for abbr, patterns in _COMPILED_TASKS.items():
        if any(p.search(text) for p in patterns):
            matched.append(abbr)
    return matched


def tag_all_papers(papers: list[dict]) -> None:
    """Annotate each paper in-place with a `_tasks` field (semicolon-separated)."""
    counter: Counter = Counter()
    for p in papers:
        title = str(p.get("Title", ""))
        abstract = str(p.get("Abstract", ""))
        tasks = tag_tasks(title, abstract)
        p["_tasks"] = ";".join(tasks) if tasks else ""
        counter.update(tasks)

    logger.info(f"Task tagging complete: {sum(1 for p in papers if p.get('_tasks'))} / {len(papers)} papers tagged")
    for task, count in counter.most_common():
        logger.info(f"  {task} ({TASK_NAMES[task]}): {count}")
