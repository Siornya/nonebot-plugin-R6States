"""数据源（API 为主）+ 缓存层。

对外暴露 ``get_full_stats``：先查本地缓存，未命中再打 r6data 的 fullStats，
成功后回写缓存。错误统一转成 ``ServiceError``，由指令层决定怎么回话。
复用一个进程级共享的 httpx 客户端（连接池复用），指令层须在 on_shutdown 调 ``aclose``。
"""
from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from .cache import JSONCache
from .storage import PLAYER_CACHE_FILE
from .r6data import R6Client, R6APIError
from .config_mannger import resolve_apikey

VALID_PLATFORMS = ("uplay", "psn", "xbl")

#: 免费申请 api-key 的入口，附在缺/失效提示里
APIKEY_HELP = "可在 https://r6data.com/ 免费获取 Key，再用 /r6key <key> 绑定"

_cache = JSONCache(PLAYER_CACHE_FILE)

#: 进程级共享 httpx 客户端，注入给每个 R6Client，避免每次查询重建连接池/握手。
_http: Optional[httpx.AsyncClient] = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=15.0)
    return _http


async def aclose() -> None:
    """关闭共享 httpx 客户端（在 nonebot on_shutdown 调用）。"""
    global _http
    if _http is not None and not _http.is_closed:
        await _http.aclose()
    _http = None


class ServiceError(Exception):
    def __init__(self, message: str, *, expired: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.expired = expired


async def get_full_stats(
    player_id: str,
    scopes: list[str],
    platform: str = "uplay",
    season_year: str | None = None,
    modes: str | None = None,
    *,
    ttl: float,
) -> dict[str, Any]:
    if platform not in VALID_PLATFORMS:
        raise ServiceError(f"平台无效，可选：{', '.join(VALID_PLATFORMS)}")

    api_key, _ = resolve_apikey(scopes)
    if not api_key:
        raise ServiceError(f"未设置 API Key。{APIKEY_HELP}")

    cache_key = f"fullStats:{platform}:{season_year or 'all'}:{modes or 'all'}:{player_id.lower()}"
    cached = await _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        r6 = R6Client(api_key=api_key, client=_client())
        data = await r6.players.get_full_stats(
            player_id, platform, season_year=season_year, modes=modes
        )
    except R6APIError as e:
        if e.status == 401:
            raise ServiceError(
                f"API Key 鉴权失败，可能已过期（官方有效期约 1 个月）。{APIKEY_HELP}",
                expired=True,
            ) from e
        raise ServiceError(f"API 返回错误（{e.status}）：{e}") from e
    except Exception as e:  # noqa: BLE001 - 网络等异常统一兜底
        raise ServiceError(f"请求失败：{type(e).__name__}") from e

    # 打上实际取数时间，随数据一起缓存（缓存命中时展示的就是这个原始取数时刻）
    if isinstance(data, dict):
        data["_fetched_at"] = time.time()
    await _cache.set(cache_key, data, ttl)
    return data
