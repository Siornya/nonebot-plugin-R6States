import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

spec = importlib.util.spec_from_file_location(
    "r6_replay", Path(__file__).parents[1] / "nonebot_plugin_R6States/replay.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def file(name="round.rec", **data):
    return SimpleNamespace(type="file", data={"name": name, **data})


def test_same_message_only():
    event = SimpleNamespace(
        message=[file("current.rec")],
        reply=SimpleNamespace(message=[file("replied.rec")]),
    )
    assert replay.replay_attachments(event) == [{"name": "current.rec"}]


@pytest.mark.parametrize("group", [True, False])
def test_resolve_file_url(group):
    bot = SimpleNamespace(call_api=AsyncMock(return_value={"url": "https://files.test/replay"}))
    event = SimpleNamespace(group_id=123) if group else SimpleNamespace()
    result = asyncio.run(replay.attachment_url(bot, event, {"file_id": "abc", "busid": 3}))
    assert result == "https://files.test/replay"
    expected = {"file_id": "abc", "group_id": 123, "busid": 3} if group else {"file_id": "abc"}
    bot.call_api.assert_awaited_once_with("get_group_file_url" if group else "get_private_file_url", **expected)


def test_download_contents(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(replay.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, content=b"replay")), **kwargs))
    bot = SimpleNamespace()
    files = [{"name": "round.rec", "url": "https://files.test/rec"}]
    result = asyncio.run(replay.download_replays(bot, SimpleNamespace(), files, max_bytes=6))
    assert result == [{"name": "round.rec", "data": b"replay"}]


def test_summary():
    result = replay.format_replay({"matchID": "123", "match": {"map": "Bank", "rounds_count": 9,
        "blue_score": 5, "orange_score": 4, "total_kills": 0}, "quota": {"remaining": 0}})
    assert "Bank" in result
    assert "蓝队 5 : 4 橙队" in result
    assert "总击杀：0" in result
    assert "剩余额度：0" in result


def test_nonebot_analyze_dispatch(monkeypatch):
    import nonebot

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    from nonebot.adapters.onebot.v11 import Message, MessageSegment, PrivateMessageEvent
    from nonebot.exception import FinishedException

    try:
        nonebot.get_driver()
    except ValueError:
        nonebot.init(log_level="WARNING")
    plugin = nonebot.load_plugin("nonebot_plugin_R6States")
    assert plugin is not None
    module = plugin.module
    event = PrivateMessageEvent.model_validate({
        "time": 0, "self_id": 999, "post_type": "message", "message_type": "private",
        "sub_type": "friend", "message_id": 123, "user_id": 456,
        "message": Message([MessageSegment.text("/r6 analyze"),
                            MessageSegment("file", {"name": "round.rec", "url": "https://files.test/rec"})]),
        "raw_message": "/r6 analyze", "font": 0, "sender": {"user_id": 456},
    })
    upload = AsyncMock(return_value="比赛摘要")
    stats = AsyncMock()
    finish = AsyncMock(side_effect=FinishedException)
    monkeypatch.setattr(module, "analyze_replay", upload)
    monkeypatch.setattr(module, "get_full_stats", stats)
    monkeypatch.setattr(module.r6, "finish", finish)
    bot = SimpleNamespace()
    with pytest.raises(FinishedException):
        asyncio.run(module._(bot, event, Message("analyze")))
    upload.assert_awaited_once_with(bot, event, ["456"], max_bytes=128 * 1024 * 1024)
    stats.assert_not_awaited()
    assert finish.await_args.args[0].data["text"] == "比赛摘要"
