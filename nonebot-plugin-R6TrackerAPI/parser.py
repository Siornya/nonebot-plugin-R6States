from bs4 import BeautifulSoup
from typing import List, Dict

OVERVIEW_SECTION = [
    "Current Season",
    "Season Peaks",
    "Lifetime Overall",
    "Lifetime Ranked",
    "Lifetime Unranked + Quick Match",
    "Y10S4 Overview",
    "All Matches"
]


def parse_overview(html: str) -> Dict[str, List[str]]:
    """
    提取Overview页面中的所有文本，并且划分部分
    :param html: Overview页面html源代码
    :return: 键值对<部分标题，文本数组>
    """
    soup = BeautifulSoup(html, "html.parser")

    texts: List[str] = []
    for t in soup.stripped_strings:
        if t:
            texts.append(t)

    sections: Dict[str, List[str]] = {title: [] for title in OVERVIEW_SECTION}
    current_section: str | None = None
    section_idx = 0

    for t in texts:
        if section_idx < len(OVERVIEW_SECTION) and t == OVERVIEW_SECTION[section_idx]:
            current_section = OVERVIEW_SECTION[section_idx]
            section_idx += 1
            continue

        if current_section is not None:
            sections[current_section].append(t)

    return sections
