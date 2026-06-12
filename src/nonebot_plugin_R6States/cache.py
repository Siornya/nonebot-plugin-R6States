"""轻量本地缓存：单 JSON 文件 + 每条目独立 TTL + 异步锁 + 原子写。

设计动机（对比旧的 players.yaml）：
- 旧实现按**整文件** mtime 判 TTL，一次写入会重置所有条目的有效期，过期还整包丢弃。
- 这里每条目自带写入时间戳，**各自过期**；TTL 由调用方按 endpoint 指定。
- 写入走 "临时文件 + os.replace" 原子替换，配异步锁，避免并发下半写/相互覆盖。
"""
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
            # 缓存损坏不应影响主流程：当作空缓存重建。
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

    async def get(self, key: str, ttl: float) -> Optional[Any]:
        """命中且未超过 ttl（秒）则返回缓存值，否则返回 None。"""
        async with self._lock:
            entry = self._load().get(key)
        if not entry:
            return None
        if time.time() - entry.get("ts", 0) > ttl:
            return None
        return entry.get("value")

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            data = self._load()
            data[key] = {"ts": time.time(), "value": value}
            self._atomic_write(data)
