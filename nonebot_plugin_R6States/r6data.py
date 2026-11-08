"""Arenyze API calls used by this plugin.

Full stats follows the web API documentation; replay uploads follow r6-data.js.
"""

from __future__ import annotations
from typing import Any, Optional, Mapping
from pathlib import Path
import asyncio
import httpx

#: 本移植对标的 r6-data.js 版本
BASED_ON_VERSION = "3.3.1"
BASED_ON_COMMIT = "544eff7536bb89acbf0ca1e9a654191120ccdcf9"

#: API 地址
BASE_URL = "https://public-api.arenyze.com/r6/api"
SITE_BASE_URL = "https://r6.arenyze.com/api"

VALID_FULL_STATS_MODES = ("ranked", "standard", "casual", "all")

# fullstats 支持的平台。
PLATFORM_TYPES = ("uplay", "psn", "xbl")

__all__ = [
    "R6Client",
    "Players",
    "MatchReplay",
    "SITE_BASE_URL",
    "BASED_ON_COMMIT",
    "R6APIError",
    "BASED_ON_VERSION",
    "BASE_URL",
]


# ──────────────────────────────────────────────────────────────────────────
# 错误类型
# ──────────────────────────────────────────────────────────────────────────

class R6APIError(Exception):
    """非 2xx 响应抛出。``status`` / ``data`` 携带服务端返回内容。"""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 data: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.data = data


def _clean_params(params: Mapping[str, Any]) -> dict[str, str]:
    """丢弃 None/空串,其余转字符串 —— 对应原库 buildUrlAndParams。"""
    out: dict[str, str] = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = str(value)
    return out


# ──────────────────────────────────────────────────────────────────────────
# 资源:Players
# ──────────────────────────────────────────────────────────────────────────

class Players:
    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def get_full_stats(self, name_on_platform: str, platform_type: str,
                             season_year: Optional[str] = None,
                             modes: Optional[str] = None) -> Any:
        """文档中的 V2 完整快照，返回原始 player / filters / fullStats 响应。

        fullStats 包含 operators、platform_families_full_profiles、data
        和 totalsHoursPlayed。上游 JS SDK 尚未封装此接口。
        modes: ranked|standard|casual|all；season_year: 赛季代码或 all。
        """
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        if platform_type not in PLATFORM_TYPES:
            raise ValueError("Invalid platform_type. Must be one of: " + ", ".join(PLATFORM_TYPES))
        if modes and modes not in VALID_FULL_STATS_MODES:
            raise ValueError("Invalid modes. Must be one of: " + ", ".join(VALID_FULL_STATS_MODES))
        params = {
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        }
        if season_year:
            params["seasonYear"] = season_year
        if modes:
            params["modes"] = modes
        return await self._client._get("/v2/fullstats", params)


class MatchReplay:
    """Website replay API; preserves match payloads and plan quota responses."""

    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def upload_replays(self, files: Any) -> Any:
        """Upload 1–20 .rec files from paths, bytes, or {path/name/data} mappings."""
        entries = list(files) if isinstance(files, (list, tuple)) else [files]
        if not entries or entries == [None]:
            raise ValueError("At least one .rec file is required")
        if len(entries) > 20:
            raise ValueError("A maximum of 20 .rec files can be uploaded per request")
        uploads = []
        for entry in entries:
            name = None
            if isinstance(entry, Mapping):
                name = entry.get("name")
                entry = entry.get("path") or entry.get("data")
            if isinstance(entry, (str, Path)):
                path = Path(entry)
                name = name or path.name
                entry = await asyncio.to_thread(path.read_bytes)
            name = name or "replay.rec"
            if not isinstance(entry, (bytes, bytearray, memoryview)):
                raise ValueError("Invalid replay entry: expected path, bytes, or mapping")
            if not isinstance(name, str) or Path(name).suffix.lower() != ".rec":
                raise ValueError("Only .rec replay files are allowed")
            uploads.append(("replayFiles", (name, bytes(entry), "application/octet-stream")))
        return await self._client._request(
            "POST", "/replays/api/upload", site=True, files=uploads)


class R6Client:
    """
    用法::

        r6 = R6Client(api_key="...")
        try:
            data = await r6.players.get_full_stats("Name", "uplay")
        finally:
            await r6.aclose()

    也可作为异步上下文管理器::

        async with R6Client(api_key="...") as r6:
            ...
    """

    def __init__(self, api_key: str, *, base_url: str = BASE_URL,
                 timeout: float = 15.0,
                 site_base_url: str = SITE_BASE_URL,
                 client: Optional[httpx.AsyncClient] = None) -> None:
        if not api_key:
            raise ValueError("Missing required config parameter: api_key")
        self.api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._site_base_url = site_base_url.rstrip("/")
        # 允许外部注入共享的 AsyncClient(例如复用 NoneBot 的);否则自建。
        self._http = client or httpx.AsyncClient(timeout=timeout)
        self._owns_http = client is None

        self.players = Players(self)
        self.match_replay = MatchReplay(self)

    async def __aenter__(self) -> "R6Client":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """关闭内部创建的 httpx client(注入的不会被关闭)。"""
        if self._owns_http:
            await self._http.aclose()

    async def _get(self, path: str, params: Mapping[str, Any]) -> Any:
        return await self._request("GET", path, params=_clean_params(params))

    async def _request(self, method: str, path: str, *, site: bool = False,
                       **kwargs: Any) -> Any:
        base = self._site_base_url if site else self._base_url
        url = f"{base}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": f"r6data.py (port of r6-data.js@{BASED_ON_VERSION})",
            "api-key": self.api_key,
        }
        resp = await self._http.request(method, url, headers=headers, **kwargs)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        text = resp.text
        data: Any = None
        if text:
            try:
                data = resp.json()
            except ValueError:
                data = text
        if resp.is_success:
            return data
        if resp.status_code == 401:
            raise R6APIError("Authentication error", status=401, data=data)
        raise R6APIError(
            f"Request failed with status code {resp.status_code}",
            status=resp.status_code, data=data,
        )
