"""离线战绩卡片：数据整理与绘图分离，所有坐标采用逻辑像素。"""
from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

from .formatter import fetched_label, rank_name

_ASSETS = Path(__file__).parent / "assets"
_MONA = str(_ASSETS / "MonaSans.ttf")
_NOTO = str(_ASSETS / "NotoSansSC.ttf")

_BG = (16, 20, 29)
_SURFACE = (25, 31, 43)
_INSET = (20, 26, 37)
_WHITE = (241, 245, 251)
_BODY = (208, 217, 231)
_GRAY = (153, 169, 191)
_DIM = (119, 138, 162)
_LINE = (43, 55, 74)
_ACCENT = (244, 187, 80)
_ATK = (243, 142, 112)
_DEF = (113, 182, 245)

_SCALE = 2
_WIDTH = 760
_PAD = 28
_CONTENT = _WIDTH - 2 * _PAD
_PER_SIDE = 4
_BOARD_HEIGHT = 112
_ROW_HEIGHT = 38
_BOARD_NAMES = {
    "ranked": "排位", "casual": "休闲", "standard": "标准",
    "unranked": "非排位", "quick-match": "快速比赛",
    "event": "活动", "warmup": "热身",
}
_font_cache: dict[tuple[str, int, Optional[int]], ImageFont.FreeTypeFont] = {}


def _font(path: str, size: int, weight: Optional[int] = None) -> ImageFont.FreeTypeFont:
    key = (path, size * _SCALE, weight)
    if key not in _font_cache:
        font = ImageFont.truetype(path, size * _SCALE)
        if weight is not None:
            try:
                values = []
                for axis in font.get_variation_axes():
                    name = axis.get("name", b"")
                    name = name.decode() if isinstance(name, bytes) else name
                    values.append(weight if name.lower() == "weight" else axis.get("default", 0))
                font.set_variation_by_axes(values)
            except Exception:  # noqa: BLE001 - 静态字体无需设置可变轴
                pass
        _font_cache[key] = font
    return _font_cache[key]


def _runs(text: str) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for char in text:
        cjk = "一" <= char <= "鿿" or "　" <= char <= "〿" or "＀" <= char <= "￯"
        if out and out[-1][1] == cjk:
            out[-1] = (out[-1][0] + char, cjk)
        else:
            out.append((char, cjk))
    return out


def _measure(text: str, size: int, weight: Optional[int] = None) -> float:
    return sum(_font(_NOTO if cjk else _MONA, size, weight).getlength(run)
               for run, cjk in _runs(text)) / _SCALE


def _number(value: Any) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _count(value: Any) -> str:
    return f"{int(_number(value)):,}"


def _ratio(kills: float, deaths: float) -> float:
    # 与文本版本保持一致：无死亡时直接显示击杀数。
    return kills / deaths if deaths else kills


@dataclass(frozen=True)
class _Board:
    mode: str
    profile: dict[str, Any]

    def value(self, key: str) -> float:
        return _number(self.profile.get(key))

    @property
    def ranked(self) -> bool:
        return self.mode == "ranked"


def _boards(data: dict[str, Any]) -> list[_Board]:
    """沿用旧版规则：每个平台的每种模式取最新赛季档案。"""
    result = []
    for family in data.get("platform_families_full_profiles") or []:
        for board in family.get("board_ids_full_profiles") or []:
            profiles = board.get("full_profiles") or []
            if profiles:
                latest = max(profiles, key=lambda item: _number(item.get("season_id")))
                result.append(_Board(board.get("board_id") or "未知模式", latest.get("profile") or {}))
    return sorted(result, key=lambda item: not item.ranked)


class _Canvas:
    """封装缩放、字体回退、宽度限制与常用卡片组件。"""

    def __init__(self, height: int) -> None:
        self.image = Image.new("RGB", (_WIDTH * _SCALE, height * _SCALE), _BG)
        self.draw = ImageDraw.Draw(self.image)

    def rect(self, box: tuple[float, float, float, float], color: tuple[int, int, int],
             radius: int = 0, outline: Optional[tuple[int, int, int]] = None) -> None:
        coords = tuple(round(value * _SCALE) for value in box)
        self.draw.rounded_rectangle(coords, radius=radius * _SCALE,
                                    fill=color, outline=outline, width=_SCALE)

    def line(self, x: float, y: float, width: float, color: tuple[int, int, int] = _LINE) -> None:
        self.draw.line(((round(x * _SCALE), round(y * _SCALE)),
                        (round((x + width) * _SCALE), round(y * _SCALE))),
                       fill=color, width=_SCALE)

    def text(self, x: float, baseline: float, text: Any, size: int = 16,
             color: tuple[int, int, int] = _BODY, weight: Optional[int] = 400,
             width: Optional[float] = None, align: str = "left") -> None:
        text = str(text)
        if width is not None:
            min_size = max(10, size - 4)
            while size > min_size and _measure(text, size, weight) > width:
                size -= 1
            if _measure(text, size, weight) > width:
                while text and _measure(text + "…", size, weight) > width:
                    text = text[:-1]
                text += "…"
        if align == "right":
            x -= _measure(text, size, weight)
        elif align == "center":
            x -= _measure(text, size, weight) / 2
        pen = x * _SCALE
        for run, cjk in _runs(text):
            font = _font(_NOTO if cjk else _MONA, size, weight)
            self.draw.text((round(pen), round(baseline * _SCALE)), run,
                           font=font, fill=color, anchor="ls")
            pen += font.getlength(run)

    def panel(self, x: int, y: int, width: int, height: int) -> None:
        self.rect((x, y + 3, x + width, y + height + 3), (11, 15, 23), radius=14)
        self.rect((x, y, x + width, y + height), _SURFACE, radius=14, outline=_LINE)

    def pill(self, right: int, top: int, text: str, color: tuple[int, int, int] = _GRAY) -> int:
        width = math.ceil(_measure(text, 13, 600)) + 22
        left = right - width
        self.rect((left, top, right, top + 26), _INSET, radius=7, outline=_LINE)
        self.text(left + 11, top + 18, text, 13, color, weight=600)
        return left - 8

    def png(self) -> bytes:
        output = BytesIO()
        self.image.save(output, format="PNG")
        return output.getvalue()


def _header(canvas: _Canvas, player_id: str, data: dict[str, Any]) -> None:
    info = data.get("data") or {}
    handle = (info.get("platformInfo") or {}).get("platformUserHandle") or player_id
    metadata = info.get("metadata") or {}
    # 抽象斜切背景与小型 R6 标志均由本地几何图形绘制。
    canvas.draw.polygon([(point[0] * _SCALE, point[1] * _SCALE)
                         for point in ((_WIDTH - 170, 0), (_WIDTH, 0),
                                       (_WIDTH, 93), (_WIDTH - 240, 93))],
                        fill=(22, 28, 40))
    canvas.rect((_PAD, 0, _PAD + 88, 3), _ACCENT)
    canvas.rect((_PAD, 33, _PAD + 40, 73), _ACCENT, radius=10)
    canvas.text(_PAD + 20, 60, "R6", 21, _BG, weight=800, align="center")
    left = _PAD + 56
    canvas.text(left, 29, "PLAYER REPORT", 11, _ACCENT, weight=700)
    right = _WIDTH - _PAD
    for key, prefix in (("battlepassLevel", "BP"), ("clearanceLevel", "LV")):
        if metadata.get(key) is not None:
            right = canvas.pill(right, 38, f"{prefix} {_count(metadata[key])}")
    canvas.text(left, 63, handle, 31, _WHITE, weight=700, width=right - left - 12)


def _section(canvas: _Canvas, y: int, title: str, detail: str) -> None:
    canvas.rect((_PAD, y + 5, _PAD + 3, y + 22), _ACCENT, radius=1)
    canvas.text(_PAD + 12, y + 21, title, 18, _WHITE, weight=700)
    canvas.text(_WIDTH - _PAD, y + 20, detail, 12, _DIM, align="right", width=440)


def _board_card(canvas: _Canvas, y: int, board: _Board) -> None:
    canvas.panel(_PAD, y, _CONTENT, _BOARD_HEIGHT)
    left, right = _PAD + 18, _WIDTH - _PAD - 18
    color = _ACCENT if board.ranked else _DEF
    canvas.rect((left, y + 15, left + 6, y + 21), color, radius=3)
    title = _BOARD_NAMES.get(board.mode, board.mode)
    canvas.text(left + 14, y + 26, title, 16, color, weight=700, width=200)
    if board.ranked:
        canvas.text(right, y + 26, rank_name(int(board.value("rank_points"))),
                    16, _WHITE, weight=600, align="right", width=260)
    canvas.line(left, y + 36, right - left)

    wins, losses = board.value("wins"), board.value("losses")
    matches = wins + losses
    kd = _ratio(board.value("kills"), board.value("deaths"))
    rate = wins / matches * 100 if matches else 0
    metrics = [
        ("RP" if board.ranked else "击杀", _count(board.value("rank_points" if board.ranked else "kills"))),
        ("KD", f"{kd:.2f}"), ("胜率", f"{rate:.1f}%"), ("胜负场次", _count(matches)),
    ]
    cell_width = (right - left) / len(metrics)
    for index, (label, value) in enumerate(metrics):
        x = left + index * cell_width
        canvas.text(x, y + 53, label, 11, _GRAY)
        canvas.text(x, y + 79, value, 25, color if index == 0 else _WHITE,
                    weight=700, width=cell_width - 16)
        if index:
            canvas.draw.line(((round((x - 12) * _SCALE), (y + 46) * _SCALE),
                              (round((x - 12) * _SCALE), (y + 79) * _SCALE)),
                             fill=_LINE, width=_SCALE)
    details = f"胜 {_count(wins)}  /  负 {_count(losses)}"
    if board.ranked:
        details += f"    ·    最高 RP {_count(board.value('max_rank_points'))}"
    details += (f"    ·    K/D {_count(board.value('kills'))}/{_count(board.value('deaths'))}"
                f"    ·    掉线 {_count(board.value('abandon'))}")
    canvas.text(left, y + 101, details, 11, _DIM, width=right - left)


def _operator_card(canvas: _Canvas, x: int, y: int, width: int, height: int,
                   title: str, operators: list[dict[str, Any]], color: tuple[int, int, int]) -> None:
    canvas.panel(x, y, width, height)
    left, right = x + 16, x + width - 16
    canvas.text(left, y + 27, title, 16, color, weight=700)
    canvas.text(right, y + 26, "TOP 4", 10, _DIM, weight=600, align="right")
    canvas.line(left, y + 38, right - left)
    rounds_x, win_x = right - 123, right - 56
    canvas.text(left, y + 56, "干员", 11, _DIM)
    for column, label in ((rounds_x, "回合"), (win_x, "胜率"), (right, "KD")):
        canvas.text(column, y + 56, label, 11, _DIM, align="right")

    top = sorted(operators, key=lambda item: _number(item.get("roundsPlayed")), reverse=True)[:_PER_SIDE]
    peak = max((_number(item.get("roundsPlayed")) for item in top), default=0)
    name_width = rounds_x - left - 40
    for index, operator in enumerate(top):
        baseline = y + 82 + index * _ROW_HEIGHT
        canvas.text(left, baseline, operator.get("operator") or "?", 16, _BODY,
                    weight=600, width=name_width)
        canvas.text(rounds_x, baseline, _count(operator.get("roundsPlayed")),
                    13, _GRAY, align="right", width=36)
        canvas.text(win_x, baseline, f"{_number(operator.get('winPercent')):.1f}%",
                    13, _BODY, align="right", width=59)
        canvas.text(right, baseline, f"{_number(operator.get('kd')):.2f}",
                    17, _WHITE, weight=700, align="right", width=49)
        # 出场比例条只反映本侧 Top 4 的相对出场次数，不作为胜率。
        canvas.rect((left, baseline + 9, left + name_width, baseline + 11), _LINE, radius=1)
        share = min(1.0, max(0.0, _number(operator.get("roundsPlayed")) / peak)) if peak else 0
        if share:
            canvas.rect((left, baseline + 9, left + name_width * share, baseline + 11), color, radius=1)
    if not top:
        canvas.text(x + width / 2, y + 82, "暂无干员数据", 14, _DIM, align="center")

    kills = sum(_number(item.get("kills")) for item in operators)
    deaths = sum(_number(item.get("deaths")) for item in operators)
    rounds = sum(_number(item.get("roundsPlayed")) for item in operators)
    canvas.line(left, y + height - 34, right - left)
    canvas.text(left, y + height - 15, f"总回合 {_count(rounds)}", 11, _DIM, width=width - 145)
    canvas.text(right, y + height - 15, f"KD {_ratio(kills, deaths):.2f}",
                12, color, weight=600, align="right", width=110)


def render_full_stats(player_id: str, data: dict[str, Any]) -> bytes:
    boards = _boards(data)
    operators = data.get("operators") or []
    sides = [
        ("进攻方", [item for item in operators if item.get("side") == "Attacker"], _ATK),
        ("防守方", [item for item in operators if item.get("side") == "Defender"], _DEF),
    ]
    row_count = max((min(len(items), _PER_SIDE) for _, items, _ in sides), default=0)
    operator_height = 96 + max(1, row_count) * _ROW_HEIGHT

    # 先计算实际布局高度，再创建画布；不依赖固定高度或事后裁剪。
    y = 88
    board_title = y
    board_positions = []
    if boards:
        y += 34
        for board in boards:
            board_positions.append((y, board))
            y += _BOARD_HEIGHT + 10
        y += 4
    operator_title = y
    operator_y = y + 34
    if operators:
        y = operator_y + operator_height + 18
    empty_y = y
    if not boards and not operators:
        y += 120
    footer_y = y
    canvas = _Canvas(footer_y + 48)
    _header(canvas, player_id, data)

    season = str(data.get("_season_year") or data.get("seasonYear") or "未知")
    if boards:
        detail = "各模式最新赛季档案" if season.lower() == "all" else "按模式展示战绩"
        _section(canvas, board_title, "战绩概览", detail)
        for top, board in board_positions:
            _board_card(canvas, top, board)
    if operators:
        kills = sum(_number(item.get("kills")) for item in operators)
        deaths = sum(_number(item.get("deaths")) for item in operators)
        _section(canvas, operator_title, "干员表现",
                 f"出场排序 · 全部 {len(operators)} 干员 · KD {_ratio(kills, deaths):.2f}")
        gap = 16
        width = (_CONTENT - gap) // 2
        for index, (title, items, color) in enumerate(sides):
            _operator_card(canvas, _PAD + index * (width + gap), operator_y,
                           width, operator_height, title, items, color)
    if not boards and not operators:
        canvas.panel(_PAD, empty_y, _CONTENT, 100)
        canvas.text(_WIDTH / 2, empty_y + 42, "暂时没有战绩数据", 22,
                    _WHITE, weight=600, align="center")
        canvas.text(_WIDTH / 2, empty_y + 70, "请确认玩家名、平台和查询赛季", 14, _GRAY, align="center")

    # 页脚共用一行，左侧真实取数时间，右侧实际查询的赛季过滤条件。
    canvas.line(_PAD, footer_y, _CONTENT)
    canvas.text(_PAD, footer_y + 28, fetched_label(data) or "尚无更新时间", 12, _DIM, width=350)
    label = "全部赛季" if season.lower() == "all" else f"赛季 {season}"
    canvas.pill(_WIDTH - _PAD, footer_y + 10, label)
    return canvas.png()
