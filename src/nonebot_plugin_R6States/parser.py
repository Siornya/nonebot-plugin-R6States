import datetime
import yaml
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict

from nonebot import get_plugin_config

from .config import Config
from .fetcher import fetch_overview

plugin_config = get_plugin_config(Config)

OVERVIEW_SECTION = [
    "Current Season",
    "Season Peaks",
    "Lifetime Overall",
    "Lifetime Ranked",
    "Lifetime Unranked + Quick Match",
    "Y10S4 Overview",
    "All Matches"
]


def load_players() -> Dict[str, Dict[str, List[str]]]:
    file_path = plugin_config.PLAYERS_FILE

    if not file_path.exists():
        return {}

    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    if datetime.now() - mtime > datetime.timedelta(days=1):
        return {}

    with plugin_config.PLAYERS_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_players(players: Dict[str, Dict[str, List[str]]]):
    """保存所有玩家数据到 YAML 文件"""
    with open(plugin_config.PLAYERS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(players, f, allow_unicode=True)


async def parse_overview(player_id: str) -> Dict[str, List[str]]:
    """
    提取Overview页面中的所有文本，并且划分部分
    :param player_id: 玩家id
    :return: 键值对<部分标题，文本数组>
    """
    players = load_players()

    if player_id in players:
        return players[player_id]

    html = await fetch_overview(player_id)
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

    players[player_id] = sections
    save_players(players)

    return sections
