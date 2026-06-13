from __future__ import annotations

from pydantic import BaseModel


class Config(BaseModel):
    #: 当前赛季代码（如 "Y10S4"）。查询默认按此赛季过滤；填 "all" 则不过滤、查生涯。
    #: 在 .env 里用 CURRENT_SEASON=Y10S4 覆盖；每赛季更新一次即可。
    current_season: str = "Y11S2"

    #: 查询结果是否渲染成图片（失败时自动回退文本）。.env 用 R6_OUTPUT_IMAGE=false 关闭。
    r6_output_image: bool = True
