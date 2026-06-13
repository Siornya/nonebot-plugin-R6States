from nonebot import on_command, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata, get_plugin_config
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, GroupMessageEvent

from .config import Config
from .service import VALID_PLATFORMS, ServiceError, get_full_stats
from .formatter import format_full_stats
from .renderer import render_full_stats
from .config_mannger import (
    KEY_TTL_DAYS,
    set_apikey,
    resolve_apikey,
    get_apikey_age_days,
)

__plugin_meta__ = PluginMetadata(
    name="彩六数据查询",
    description="查询指定玩家的数据",
    usage="/r6 <id> [平台]　/r6key <key>　/r6help",
    homepage="https://github.com/Siornya/nonebot-plugin-R6States",
    type="application",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

plugin_config = get_plugin_config(Config)

r6 = on_command("r6", aliases={"R6"}, priority=10, block=True)
r6_key = on_command("r6key", aliases={"R6key", "R6DAPI", "r6dapi"}, priority=5, block=True)
r6_help = on_command("r6help", aliases={"R6help"}, priority=5, block=True)

HELP_TEXT = (
    "彩六数据查询\n"
    "/r6 <id> [平台]   查询玩家数据（平台默认 uplay，可选 psn/xbl）\n"
    "/r6key <key>      设置本群/本人的 r6data API Key\n"
    "/r6help           显示本帮助\n"
    "Key 可在 https://r6data.com/ 免费获取；优先用你的个人 Key，没有则用群 Key"
)


def _scope_id(event: MessageEvent) -> str:
    """设置 key 的归属：群聊按群、私聊按人。"""
    if isinstance(event, GroupMessageEvent):
        return str(event.group_id)
    return str(event.user_id)


def _lookup_scopes(event: MessageEvent) -> list[str]:
    """查询时的 key 候选顺序：个人优先，个人没设则回退到群。"""
    if isinstance(event, GroupMessageEvent):
        return [str(event.user_id), str(event.group_id)]
    return [str(event.user_id)]


@r6_help.handle()
async def _():
    await r6_help.finish(HELP_TEXT)


@r6_key.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    key = args.extract_plain_text().strip()
    if not key:
        await r6_key.finish(
            "请在命令后输入 API Key，例如：/r6key abcdef...\n"
            "没有的话可在 https://r6data.com/ 免费获取"
        )

    scope = _scope_id(event)
    set_apikey(scope, key)
    where = "本群" if isinstance(event, GroupMessageEvent) else "个人"
    await r6_key.finish(f"✅ 已设置{where} API Key（官方有效期约 {KEY_TTL_DAYS} 天）")


@r6.handle()
async def _(event: MessageEvent, args: Message = CommandArg()):
    tokens = args.extract_plain_text().split()
    if not tokens:
        await r6.finish("用法：/r6 <id> [平台]，详见 /r6help")

    # 末尾 token 若是平台名则作为平台，其余都当作玩家 id。
    platform = "uplay"
    if len(tokens) > 1 and tokens[-1].lower() in VALID_PLATFORMS:
        platform = tokens[-1].lower()
        tokens = tokens[:-1]

    if len(tokens) > 5:
        await r6.finish("一次最多查询 5 个 id")

    scopes = _lookup_scopes(event)

    # key 临近过期的轻提醒（针对实际命中的那个 key，不阻断查询）。
    _, matched = resolve_apikey(scopes)
    age = get_apikey_age_days(matched) if matched else None
    if age is not None and age >= KEY_TTL_DAYS:
        await r6.send(f"⚠️ 当前 API Key 已设置 {age:.0f} 天，可能已过期，如查询失败请 /r6key 重设")

    for player_id in tokens:
        try:
            data = await get_full_stats(
                player_id, scopes, platform, season_year=plugin_config.current_season
            )
            if plugin_config.r6_output_image:
                try:
                    png = render_full_stats(player_id, data)
                    await r6.send(MessageSegment.image(png))
                    continue
                except Exception as e:  # noqa: BLE001 - 渲染失败回退文本
                    logger.warning(f"图片渲染失败，回退文本: {type(e).__name__}: {e}")
            await r6.send(format_full_stats(player_id, data))
        except ServiceError as e:
            await r6.send(f"❌ {player_id}：{e.message}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"查询 {player_id} 出错: {type(e).__name__}: {e}")
            await r6.send(f"❌ {player_id}：查询失败")
