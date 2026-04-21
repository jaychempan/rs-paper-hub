"""Filter papers related to SAR (Synthetic Aperture Radar) in Remote Sensing."""

import re

# ============================================================
# Keyword lists
# ============================================================

# 核心概念关键词 — SAR 直接表述（命中即入选）
CORE_KEYWORDS = [
    r"\bSAR\b",
    r"synthetic\s+aperture\s+radar",
    r"\bInSAR\b",
    r"\bDInSAR\b",
    r"\bPolSAR\b",
    r"\bSAR[\-\s]?ADC\b",
    r"\bGBSAR\b",
    r"\bISAR\b",
    r"polarimetric\s+SAR",
    r"multi[\-\s]?polarization\s+SAR",
    r"full[\-\s]?polarimetric",
    r"compact[\-\s]?polarimetric",
    r"\bPolInSAR\b",
    r"interferometric\s+SAR",
    r"differential\s+InSAR",
    r"persistent\s+scatterer",
    r"\bPS[\-\s]?InSAR\b",
    r"\bSBAS[\-\s]?InSAR\b",
    r"radar\s+interferometry",
    r"SAR\s+image",
    r"SAR\s+data",
    r"SAR\s+sensor",
    r"SAR\s+system",
]

# SAR 传感器与卫星平台
SENSOR_KEYWORDS = [
    r"\bSentinel[\-\s]?1\b",
    r"\bTerraSAR[\-\s]?X\b",
    r"\bTanDEM[\-\s]?X\b",
    r"\bRadarsat\b",
    r"\bRADARSAT\b",
    r"\bALOS[\-\s]?PALSAR\b",
    r"\bPALSAR\b",
    r"\bCOSMO[\-\s]?SkyMed\b",
    r"\bERSAR\b",
    r"\bEnvisat\s+ASAR\b",
    r"\bASAR\b",
    r"\bGaoFen[\-\s]?3\b",
    r"\bGF[\-\s]?3\b",
    r"\bCapella\b",
    r"\bICEYE\b",
    r"\bNISAR\b",
    r"\bSIRAS\b",
]

# SAR 相关应用与任务关键词
TASK_KEYWORDS = [
    r"SAR[\-\s](?:based|derived)\s+(?:classification|detection|segmentation|mapping|monitoring)",
    r"SAR\s+(?:change\s+detection|target\s+detection|ship\s+detection|oil\s+spill)",
    r"SAR\s+(?:despeckling|speckle\s+(?:reduction|filtering|noise|suppression))",
    r"speckle\s+(?:noise|filtering|reduction|suppression).{0,30}(?:radar|SAR)",
    r"SAR[\-\s](?:optical|EO)\s+(?:fusion|integration|registration)",
    r"(?:optical|EO)[\-\s]SAR\s+(?:fusion|integration|registration|matching)",
    r"radar\s+backscatter",
    r"radar\s+cross[\-\s]?section",
    r"\bRCS\b.{0,20}(?:radar|SAR|scatter)",
    r"SAR\s+(?:tomography|ATI|GMTI)",
    r"SAR\s+auto[\-\s]?focus",
    r"range[\-\s]Doppler",
    r"azimuth\s+(?:resolution|compression|ambiguity)",
    r"SAR\s+(?:simulation|imaging\s+mode|stripmap|spotlight|ScanSAR|TOPS)",
    r"ground[\-\s]?penetrating\s+radar",
    r"\bGPR\b.{0,20}(?:subsurface|soil|underground)",
    r"coherence\s+(?:map|estimation|analysis).{0,20}(?:InSAR|SAR|radar)",
    r"phase\s+unwrapping",
    r"land\s+subsidence.{0,30}(?:InSAR|SAR|radar)",
    r"(?:InSAR|SAR|radar).{0,30}land\s+subsidence",
    r"(?:InSAR|SAR|radar).{0,30}deformation\s+(?:monitoring|measurement|mapping)",
    r"surface\s+deformation.{0,30}(?:InSAR|SAR|radar)",
]

# 全部合并
ALL_KEYWORDS = CORE_KEYWORDS + SENSOR_KEYWORDS + TASK_KEYWORDS

# 预编译
_PATTERNS = [re.compile(kw, re.IGNORECASE) for kw in ALL_KEYWORDS]


def is_sar_related(title: str, abstract: str) -> tuple[bool, list[str]]:
    """
    Check if a paper is related to SAR in Remote Sensing.

    Returns:
        (is_match, matched_keywords)
    """
    text = f"{title} {abstract}"
    matched = []

    for pattern, keyword in zip(_PATTERNS, ALL_KEYWORDS):
        if pattern.search(text):
            matched.append(keyword)

    return len(matched) > 0, matched


def filter_sar_papers(papers: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Filter papers related to SAR.

    Returns:
        (matched_papers, all_papers_with_sar_flag)
        - matched_papers: only SAR-related papers (with _sar_keywords field)
        - all_papers_with_sar_flag: all papers with _is_sar and _sar_keywords fields
    """
    matched = []
    annotated = []

    for paper in papers:
        title = str(paper.get("Title", ""))
        abstract = str(paper.get("Abstract", ""))
        is_match, keywords = is_sar_related(title, abstract)

        paper_copy = dict(paper)
        paper_copy["_is_sar"] = is_match
        paper_copy["_sar_keywords"] = "; ".join(keywords) if keywords else ""
        annotated.append(paper_copy)

        if is_match:
            matched.append(paper_copy)

    return matched, annotated
