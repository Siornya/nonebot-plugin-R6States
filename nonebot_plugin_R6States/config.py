from __future__ import annotations

from pydantic import BaseModel


class Config(BaseModel):
    # 当前赛季代码，查询默认按此赛季过滤。填 "all" 则不过滤、查生涯。
    # 在 .env 里用 CURRENT_SEASON 覆盖
    current_season: str = "Y11S2"

    # 查询结果渲染成图片，失败时自动回退文本
    # 在 .env 用 R6_OUTPUT_IMAGE 覆盖
    r6_output_image: bool = True

    # 玩家数据本地缓存时长（分钟）。越大越省 API 用量，但数据越旧。
    # 在 .env 用 R6_CACHE_MINUTES 覆盖
    r6_cache_minutes: int = 45
