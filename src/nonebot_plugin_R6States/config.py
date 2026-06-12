from __future__ import annotations

from pydantic import BaseModel


class Config(BaseModel):
    """插件配置占位。

    api-key 走按群/按人的本地文件（见 config_mannger），不从环境读，
    所以这里暂时没有字段。后续若加全局开关（如默认平台、文本/图片输出）再补。
    """
