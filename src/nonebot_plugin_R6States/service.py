"""数据源（API 为主）+ 缓存层。

对外只暴露 ``get_operator_stats``：先查本地缓存，未命中再打 r6data API，
成功后回写缓存。错误统一转成 ``ServiceError``，由指令层决定怎么回话。
"""
from __future__ import annotations

from typing import Any

from .cache import JSONCache
from .storage import PLAYER_CACHE_FILE
from .r6data import R6Client, R6APIError
from .config_mannger import resolve_apikey

#: 玩家快照属于会变的数据，缓存 30 分钟即可显著降低 API 用量。
FULL_STATS_TTL = 30 * 60

VALID_PLATFORMS = ("uplay", "psn", "xbl")

#: 免费申请 api-key 的入口，附在缺/失效提示里
APIKEY_HELP = "可在 https://r6data.com/ 免费获取 Key，再用 /r6key <key> 绑定"

_cache = JSONCache(PLAYER_CACHE_FILE)


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
) -> dict[str, Any]:
    if platform not in VALID_PLATFORMS:
        raise ServiceError(f"平台无效，可选：{', '.join(VALID_PLATFORMS)}")

    api_key, _ = resolve_apikey(scopes)
    if not api_key:
        raise ServiceError(f"未设置 API Key。{APIKEY_HELP}")

    cache_key = f"fullStats:{platform}:{season_year or 'all'}:{modes or 'all'}:{player_id.lower()}"
    cached = await _cache.get(cache_key, ttl=FULL_STATS_TTL)
    if cached is not None:
        return cached

    try:
        async with R6Client(api_key=api_key) as r6:
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

    await _cache.set(cache_key, data)
    return data
