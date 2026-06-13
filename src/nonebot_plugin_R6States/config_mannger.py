"""按群/按人管理 r6data api-key。

落盘格式（带设置时间戳，用于过期提醒；key 官方有效期约 1 个月）::

    {"apikeys": {"<id>": {"key": "...", "set_at": 1712345678.0}}}
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from .storage import API_KEY_FILE

#: 官方 key 有效期约 30 天，超过这个天数就在查询时给个提醒。
KEY_TTL_DAYS = 30


def load_config() -> dict[str, Any]:
    if not API_KEY_FILE.exists():
        return {"apikeys": {}}
    try:
        with API_KEY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"apikeys": {}}
    data.setdefault("apikeys", {})
    return data


def save_config(data: dict[str, Any]) -> None:
    API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with API_KEY_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def set_apikey(target_id: str, key: str) -> None:
    data = load_config()
    data["apikeys"][target_id] = {"key": key, "set_at": time.time()}
    save_config(data)


def _entry(target_id: str) -> Optional[dict[str, Any]]:
    raw = load_config()["apikeys"].get(target_id)
    if raw is None:
        return None
    return raw


def get_apikey(target_id: str) -> Optional[str]:
    entry = _entry(target_id)
    return entry["key"] if entry else None


def resolve_apikey(scopes: list[str]) -> tuple[Optional[str], Optional[str]]:
    """按候选顺序找第一个有 key 的归属，返回 (key, 命中的 scope)。

    群聊传 [群号, 用户号]：群没设 key 时回退到个人 key。
    """
    for scope in scopes:
        key = get_apikey(scope)
        if key:
            return key, scope
    return None, None


def get_apikey_age_days(target_id: str) -> Optional[float]:
    """key 已设置的天数；旧格式/未设置返回 None。"""
    entry = _entry(target_id)
    if not entry:
        return None
    return (time.time() - entry["set_at"]) / 86400
