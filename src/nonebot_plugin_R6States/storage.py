from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data") / "r6states"
DATA_DIR.mkdir(parents=True, exist_ok=True)

API_KEY_FILE = DATA_DIR / "api_keys.json"
PLAYER_CACHE_FILE = DATA_DIR / "cache.json"
