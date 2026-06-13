from __future__ import annotations

import os
import json
import time
import asyncio
import tempfile
from typing import Any, Optional
from pathlib import Path


class JSONCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _atomic_write(self, data: dict[str, dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._load().get(key)
        if not entry or entry.get("exp", 0) < time.time():
            return None
        return entry.get("value")

    async def set(self, key: str, value: Any, ttl: float) -> None:
        """写入并带上过期时间；顺手剔除已过期条目，避免文件无限增长。"""
        now = time.time()
        async with self._lock:
            data = self._load()
            data[key] = {"exp": now + ttl, "value": value}
            data = {k: v for k, v in data.items() if v.get("exp", 0) > now}
            self._atomic_write(data)
