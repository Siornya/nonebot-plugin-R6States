from nonebot import on_command, on_shell_command
from nonebot.rule import ArgumentParser
from nonebot.adapters import Message
from nonebot.params import ShellCommandArgs, CommandArg

from .config import *
from .fetcher import fetch_overview
from .parser import parse_overview
from .formatter import format_overview

parser = ArgumentParser("R6", add_help=True)
parser.add_argument("-g", "--group", action="store_true", help="是否为队伍模式")
parser.add_argument("ids", nargs="*", help="玩家ID")
parser.add_argument("-m", "--map", help="额外查看特定地图的数据")
parser.add_argument("-f", "--full", action="store_true", help="查看完整数据")

R6 = on_shell_command("R6", aliases={"r6"}, parser=parser, priority=10, block=True)
R6_setting = on_command("R6 setting", aliases={"r6 setting"}, priority=2, block=True)


async def query_player_overview(player_id: str, full_mode: bool) -> str:
    try:
        message = format_overview(parse_overview(await fetch_overview(player_id)), full_mode)
        return f"🎯 {player_id} 的所有 section:\n{message}"
    except Exception:
        return f"❌ 查询玩家 {player_id} 失败，可能是由于ID错误或网络延迟"


@R6.handle()
async def handle_function(args=ShellCommandArgs()):
    ids = args.ids
    is_group = args.group
    full_mode = args.full

    if not ids:
        await R6.finish("一个id都不给是想让我开开你双亲的骨灰盒吗？")

    if is_group:
        if len(ids) > 5:
            await R6.finish("一次开那么多是把双亲的棺材本拿来给我当网费吗？")
    else:
        if len(ids) != 1:
            await R6.finish("首先你想开盒别人就不对。")

    if is_group:
        for id in ids:
            await R6.send(await query_player_overview(id, full_mode))
        await R6.finish("全开了喵！")
    else:
        await R6.finish(await query_player_overview(ids[0], full_mode))


@R6_setting.handle()
async def handle_function(args: Message = CommandArg()):
    global R6_OUTPUT_MODE

    mode = args.extract_plain_text().strip().lower()

    if mode == "text":
        R6_OUTPUT_MODE = OutputMode.TEXT
    elif mode == "image":
        R6_OUTPUT_MODE = OutputMode.IMAGE
    else:
        await R6_setting.finish(
            "用法：\n"
            "/R6 setting text\n"
            "/R6 setting image"
        )

    await R6_setting.finish(f"✅ R6 返回模式已设置为：{R6_OUTPUT_MODE.name}")
