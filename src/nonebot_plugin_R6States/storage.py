"""集中管理本地落盘路径。

数据放在 CWD 下的 ``data/r6states/``（与 ``LOCALSTORE_USE_CWD=true`` 的部署习惯一致）。
"""
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data") / "r6states"
DATA_DIR.mkdir(parents=True, exist_ok=True)

#: 各群/各人的 api-key（含设置时间戳）
API_KEY_FILE = DATA_DIR / "api_keys.json"

#: API 响应缓存（按条目 TTL）
CACHE_FILE = DATA_DIR / "cache.json"
