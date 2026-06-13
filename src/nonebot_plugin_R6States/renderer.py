"""把 fullStats 渲染成图片（PNG 字节）。

双字体拼接：拉丁/数字用 Mona Sans，汉字用 Noto Sans CJK。
PIL 不会自动 fallback，所以按字符分段、各用对应字体绘制，并以基线对齐。
内容提取复用 formatter 里的 _format_boards / _format_operators，保持单一来源。
"""
from __future__ import annotations

from io import BytesIO
from typing import Any
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .formatter import _format_boards, _format_operators

_ASSETS = Path(__file__).parent / "assets"
_MONA = str(_ASSETS / "MonaSans.ttf")
_NOTO = str(_ASSETS / "NotoSansSC.ttf")

# 配色（深色卡片 + R6 橙）
_BG = (26, 29, 35)
_PANEL = (33, 37, 45)
_WHITE = (240, 242, 245)
_GRAY = (139, 144, 153)
_ACCENT = (240, 165, 0)
_BODY = (213, 216, 221)

_WIDTH = 760
_PAD = 36

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def _is_cjk(ch: str) -> bool:
    return (
        "一" <= ch <= "鿿"      # CJK 统一表意
        or "　" <= ch <= "〿"   # CJK 标点
        or "＀" <= ch <= "￯"   # 全角符号
    )


def _runs(text: str) -> list[tuple[str, bool]]:
    """把字符串切成连续的 (片段, 是否CJK)。"""
    out: list[tuple[str, bool]] = []
    cur, cur_cjk = "", None
    for ch in text:
        c = _is_cjk(ch)
        if cur and c != cur_cjk:
            out.append((cur, cur_cjk))  # type: ignore[arg-type]
            cur = ""
        cur, cur_cjk = cur + ch, c
    if cur:
        out.append((cur, cur_cjk))  # type: ignore[arg-type]
    return out


def _draw_mixed(draw: ImageDraw.ImageDraw, x: int, baseline: int,
                text: str, size: int, fill: tuple[int, int, int]) -> None:
    for run, cjk in _runs(text):
        f = _font(_NOTO if cjk else _MONA, size)
        draw.text((x, baseline), run, font=f, fill=fill, anchor="ls")
        x += int(f.getlength(run))


def render_full_stats(player_id: str, data: dict[str, Any], top_n: int = 8) -> bytes:
    info = data.get("data") or {}
    handle = (info.get("platformInfo") or {}).get("platformUserHandle") or player_id
    meta = info.get("metadata") or {}

    # ── 组织行：(文本, 字号, 颜色, 行前额外间距) ──
    rows: list[tuple[str, int, tuple[int, int, int], int]] = []
    rows.append((handle, 40, _WHITE, 0))

    head_bits = []
    if meta.get("clearanceLevel") is not None:
        head_bits.append(f"等级 {meta['clearanceLevel']}")
    if meta.get("battlepassLevel") is not None:
        head_bits.append(f"通行证 {meta['battlepassLevel']}")
    if head_bits:
        rows.append(("　".join(head_bits), 20, _GRAY, 4))

    boards = _format_boards(data.get("platform_families_full_profiles") or [])
    if boards:
        rows.append(("档案", 24, _ACCENT, 18))
        for line in boards:
            rows.append((line, 22, _BODY, 2))

    operators = data.get("operators") or []
    if operators:
        rows.append(("干员 Top", 24, _ACCENT, 18))
        for line in _format_operators(operators, top_n):
            rows.append((line, 22, _BODY, 2))

    # ── 计算高度 ──
    y = _PAD
    laid: list[tuple[str, int, tuple[int, int, int], int]] = []
    for text, size, color, gap in rows:
        asc, desc = _font(_NOTO, size).getmetrics()
        y += gap
        baseline = y + asc
        laid.append((text, size, color, baseline))
        y += asc + desc + 6
    height = y + _PAD

    # ── 绘制 ──
    img = Image.new("RGB", (_WIDTH, height), _BG)
    draw = ImageDraw.Draw(img)
    # 顶部橙色条
    draw.rectangle([(0, 0), (_WIDTH, 6)], fill=_ACCENT)
    for text, size, color, baseline in laid:
        _draw_mixed(draw, _PAD, baseline, text, size, color)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
