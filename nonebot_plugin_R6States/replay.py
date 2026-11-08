"""Same-message replay attachments and concise Arenyze match summaries."""
from __future__ import annotations

from pathlib import PurePath
from typing import Any

import httpx

USAGE = ("用法：/r6 analyze，并在同一条消息中附上 1–20 个同一场比赛的 .rec 文件"
         "（不读取回复或后续消息）")


def replay_attachments(event: Any) -> list[dict[str, Any]]:
    files = [dict(segment.data) for segment in event.message if segment.type == "file"]
    if not 1 <= len(files) <= 20:
        raise ValueError(USAGE)
    for file in files:
        name = file.get("name") or file.get("filename") or ""
        if not isinstance(name, str) or PurePath(name).suffix.lower() != ".rec":
            raise ValueError("附件必须全部是 .rec 录像文件。" + USAGE)
        file["name"] = PurePath(name).name
    return files


def _http_url(result: Any) -> str:
    if isinstance(result, dict):
        url = result.get("url")
        if isinstance(url, str) and url.startswith(("https://", "http://")):
            return url
        return _http_url(result.get("data"))
    return ""


async def attachment_url(bot: Any, event: Any, file: dict[str, Any]) -> str:
    if url := _http_url(file):
        return url
    file_id = file.get("file_id") or file.get("id") or file.get("file")
    if not file_id:
        raise ValueError("附件缺少下载地址和文件 ID，请检查 OneBot 文件消息支持。")
    if getattr(event, "group_id", None) is not None:
        params = {"group_id": event.group_id, "file_id": file_id}
        if file.get("busid") is not None:
            params["busid"] = file["busid"]
        attempts = [("get_group_file_url", params)]
    else:
        attempts = [("get_private_file_url", {"file_id": file_id})]
    attempts.append(("get_file", {"file_id": file_id}))
    for api, params in attempts:
        try:
            result = await bot.call_api(api, **params)
        except Exception:
            continue
        if url := _http_url(result):
            return url
    raise ValueError("OneBot 未提供附件的 HTTP 下载地址，请检查文件接口支持。")


async def download_replays(bot: Any, event: Any, files: list[dict[str, Any]],
                           *, max_bytes: int) -> list[dict[str, Any]]:
    uploads = []
    total = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
        for file in files:
            url = await attachment_url(bot, event, file)
            async with http.stream("GET", url) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        limit_mb = max_bytes // (1024 * 1024)
                        raise ValueError(f"录像附件总大小不能超过 {limit_mb} MB")
                    content.extend(chunk)
            if not content:
                raise ValueError("录像附件为空，请重新上传。")
            uploads.append({"name": file["name"], "data": bytes(content)})
    return uploads


def format_replay(result: Any) -> str:
    if not isinstance(result, dict) or not isinstance(result.get("match"), dict):
        raise ValueError("API 返回格式异常：缺少录像比赛摘要")
    match = result["match"]
    lines = ["🎮 录像分析完成"]
    for key, label in (("map", "地图"), ("mode", "模式"), ("match_type", "比赛类型"),
                       ("rounds_count", "回合数"), ("players_count", "玩家数"),
                       ("total_kills", "总击杀")):
        if match.get(key) is not None:
            lines.append(f"{label}：{match[key]}")
    if match.get("blue_score") is not None and match.get("orange_score") is not None:
        lines.append(f"比分：蓝队 {match['blue_score']} : {match['orange_score']} 橙队")
    if match_id := result.get("matchID"):
        lines.append(f"比赛 ID：{match_id}")
    quota = result.get("quota")
    if isinstance(quota, dict) and quota.get("remaining") is not None:
        lines.append(f"录像存储剩余额度：{quota['remaining']}")
    return "\n".join(lines)
