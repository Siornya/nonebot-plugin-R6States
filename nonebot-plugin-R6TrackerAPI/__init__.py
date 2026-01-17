from nonebot import on_command, on_shell_command, logger
from nonebot.rule import ArgumentParser
from nonebot.adapters import Message
from nonebot.params import ShellCommandArgs, CommandArg

from .config import *
from .parser import parse_overview
from .formatter import format_overview

parser = ArgumentParser("R6")
parser.add_argument("-g", "--group", action="store_true")
parser.add_argument("ids", nargs="*")
parser.add_argument("-m", "--map")
parser.add_argument("-f", "--full", action="store_true")

R6 = on_shell_command("R6", aliases={"r6"}, parser=parser, priority=10, block=False)
R6_setting = on_command("R6 setting", aliases={"r6 setting"}, priority=2, block=True)
R6_help = on_command("R6 help", aliases={"r6 help"}, priority=2, block=True)


async def query_player_overview(player_id: str, full_mode: bool) -> str:
    try:
        message = format_overview(await parse_overview(player_id), full_mode)
        return f"🎯 {player_id} 的所有 section:\n{message}"
    except Exception as e:
        logger.error(f"查询玩家 {player_id} 出错: {type(e).__name__}: {e}")
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
    global R6_ANALYSE

    text = args.extract_plain_text().strip().lower()
    parts = text.split()

    if len(parts) != 2:
        await R6_setting.finish(
            "用法：\n"
            "/R6 setting [key] [value]"
            "key: [output | analyse]\n"
            "value for output: [text | image]\n"
            "value for analyse: [true | false]\n\n"
        )

    key, value = parts

    if key == "output":
        if value == "text":
            R6_OUTPUT_MODE = OutputMode.TEXT
        elif value == "image":
            R6_OUTPUT_MODE = OutputMode.IMAGE
        else:
            await R6_setting.finish("output 可选：text / image")
        await R6_setting.finish(f"✅ R6 返回模式已设置为：{R6_OUTPUT_MODE.name}")

    elif key == "analyse":
        if value == "true":
            R6_ANALYSE = True
        elif value == "false":
            R6_ANALYSE = False
        else:
            await R6_setting.finish("analyse 可选：true / false")
        await R6_setting.finish(f"✅ R6 分析模式已设置为：{R6_ANALYSE}")

    else:
        await R6_setting.finish(
            "用法：\n"
            "/R6 setting [key] [value]"
            "key: [output | analyse]\n"
            "value for output: [text | image]\n"
            "value for analyse: [true | false]\n\n"
        )


@R6_help.handle()
async def handle_function():
    await R6_help.finish(
        "/R6 [options] <id1> <id2> ... <idN>\n"
        "-g, --group    开启组队模式，可查询多个ID（最多5个）\n"
        "-m, --map      额外获取指定地图数据\n"
        "-f, --full     查看完整数据\n"
        "/R6 setting <text|image>    设置R6返回模式为文本或图片\n")
