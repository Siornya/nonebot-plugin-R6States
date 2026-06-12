"""数据源（API 为主）+ 缓存层。

对外只暴露 ``get_operator_stats``：先查本地缓存，未命中再打 r6data API，
成功后回写缓存。错误统一转成 ``ServiceError``，由指令层决定怎么回话。
"""
from __future__ import annotations

from typing import Any

from .cache import JSONCache
from .storage import CACHE_FILE
from .r6data import R6Client, R6APIError
from .config_mannger import get_apikey

#: 干员战绩属于会变的玩家数据，缓存 30 分钟即可显著降低 API 用量。
OPERATOR_STATS_TTL = 30 * 60

VALID_PLATFORMS = ("uplay", "psn", "xbl")

_cache = JSONCache(CACHE_FILE)


class ServiceError(Exception):
    """带一个面向用户的中文提示。``expired`` 标记疑似 key 过期。"""

    def __init__(self, message: str, *, expired: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.expired = expired


async def get_operator_stats(
    player_id: str, chat_id: str, platform: str = "uplay"
) -> dict[str, Any]:
    if platform not in VALID_PLATFORMS:
        raise ServiceError(f"平台无效，可选：{', '.join(VALID_PLATFORMS)}")

    api_key = get_apikey(chat_id)
    if not api_key:
        raise ServiceError("未设置 API Key，请使用 /r6key <key> 设置")

    cache_key = f"operatorStats:{platform}:{player_id.lower()}"
    cached = await _cache.get(cache_key, ttl=OPERATOR_STATS_TTL)
    if cached is not None:
        return cached

    try:
        async with R6Client(api_key=api_key) as r6:
            data = await r6.players.get_operator_stats(player_id, platform)
    except R6APIError as e:
        if e.status == 401:
            raise ServiceError(
                "API Key 鉴权失败，可能已过期（官方有效期约 1 个月），"
                "请用 /r6key <key> 重新设置",
                expired=True,
            ) from e
        raise ServiceError(f"API 返回错误（{e.status}）：{e}") from e
    except Exception as e:  # noqa: BLE001 - 网络等异常统一兜底
        raise ServiceError(f"请求失败：{type(e).__name__}") from e

    await _cache.set(cache_key, data)
    return data
