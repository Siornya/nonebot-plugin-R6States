"""把 fullStats 渲染成图片（PNG 字节）。

- 双字体：拉丁/数字用 Mona Sans，汉字用 Noto Sans CJK，按字符分段、基线对齐。
- 2x 超采样：按 SCALE 倍分辨率绘制，避免客户端放大时发虚。
- 干员区为对齐表格，数字右对齐；攻/防用不同颜色。
内容提取复用 formatter 的 _format_boards（档案行）；干员直接读结构化字段以便排版。
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Optional
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .formatter import _format_boards

_ASSETS = Path(__file__).parent / "assets"
_MONA = str(_ASSETS / "MonaSans.ttf")
_NOTO = str(_ASSETS / "NotoSansSC.ttf")

# 配色
_BG = (24, 27, 33)
_WHITE = (240, 242, 245)
_GRAY = (140, 146, 156)
_DIM = (96, 102, 112)
_ACCENT = (240, 165, 0)
_BODY = (210, 214, 220)
_LINE = (44, 49, 58)
_ATK = (236, 122, 80)   # 攻
_DEF = (94, 160, 232)   # 防

_SCALE = 2              # 超采样倍率
_W = 760 * _SCALE
_PAD = 36 * _SCALE

_font_cache: dict[tuple[str, int, Optional[int]], ImageFont.FreeTypeFont] = {}


def _font(path: str, size: int, weight: Optional[int] = None) -> ImageFont.FreeTypeFont:
    """按字号取字体；weight 给定时尝试调可变字重（失败则忽略）。"""
    key = (path, size * _SCALE, weight)
    if key in _font_cache:
        return _font_cache[key]
    f = ImageFont.truetype(path, size * _SCALE)
    if weight is not None:
        try:
            vals = []
            for ax in f.get_variation_axes():
                name = ax.get("name", b"")
                name = name.decode() if isinstance(name, bytes) else name
                vals.append(weight if name.lower() == "weight" else ax.get("default", 0))
            f.set_variation_by_axes(vals)
        except Exception:  # noqa: BLE001 - 非可变字体或轴缺失时退回默认实例
            pass
    _font_cache[key] = f
    return f


def _is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "　" <= ch <= "〿" or "＀" <= ch <= "￯"


def _runs(text: str) -> list[tuple[str, bool]]:
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


def _measure(text: str, size: int, weight: Optional[int] = None) -> int:
    return sum(
        int(_font(_NOTO if cjk else _MONA, size, weight).getlength(run))
        for run, cjk in _runs(text)
    )


def _draw(draw: ImageDraw.ImageDraw, x: int, baseline: int, text: str,
          size: int, fill: tuple[int, int, int], weight: Optional[int] = None) -> int:
    for run, cjk in _runs(text):
        f = _font(_NOTO if cjk else _MONA, size, weight)
        draw.text((x, baseline), run, font=f, fill=fill, anchor="ls")
        x += int(f.getlength(run))
    return x


def _draw_right(draw: ImageDraw.ImageDraw, right_x: int, baseline: int, text: str,
                size: int, fill: tuple[int, int, int], weight: Optional[int] = None) -> None:
    _draw(draw, right_x - _measure(text, size, weight), baseline, text, size, fill, weight)


def _ascent(size: int) -> int:
    return _font(_NOTO, size).getmetrics()[0]


def render_full_stats(player_id: str, data: dict[str, Any], top_n: int = 8) -> bytes:
    info = data.get("data") or {}
    handle = (info.get("platformInfo") or {}).get("platformUserHandle") or player_id
    meta = info.get("metadata") or {}

    # 画在足够高的画布上，最后按实际内容裁剪
    img = Image.new("RGB", (_W, 1600 * _SCALE), _BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (_W, 6 * _SCALE)], fill=_ACCENT)

    p = _PAD
    rcol = _W - _PAD
    y = _PAD + 8 * _SCALE

    # ── 头部：玩家名 + 等级/通行证 ──
    y += _ascent(38)
    _draw(draw, p, y, handle, 38, _WHITE, weight=700)
    bits = []
    if meta.get("clearanceLevel") is not None:
        bits.append(f"Lv {meta['clearanceLevel']}")
    if meta.get("battlepassLevel") is not None:
        bits.append(f"BP {meta['battlepassLevel']}")
    if bits:
        _draw_right(draw, rcol, y, "  ".join(bits), 20, _GRAY)
    y += _font(_NOTO, 38).getmetrics()[1] + 14 * _SCALE

    def section(title: str) -> None:
        nonlocal y
        y += 16 * _SCALE
        draw.line([(p, y), (rcol, y)], fill=_LINE, width=1 * _SCALE)
        y += 14 * _SCALE + _ascent(22)
        _draw(draw, p, y, title, 22, _ACCENT, weight=700)
        y += _font(_NOTO, 22).getmetrics()[1] + 10 * _SCALE

    # ── 档案 ──
    boards = _format_boards(data.get("platform_families_full_profiles") or [])
    if boards:
        section("档案")
        for line in boards:
            y += _ascent(21)
            _draw(draw, p, y, line, 21, _BODY)
            y += _font(_NOTO, 21).getmetrics()[1] + 8 * _SCALE

    # ── 干员：攻/防双列，各取出场前 4 ──
    operators = data.get("operators") or []
    if operators:
        section("干员 Top")
        by_rounds = lambda o: o.get("roundsPlayed", 0)  # noqa: E731
        atks = sorted((o for o in operators if o.get("side") == "Attacker"),
                      key=by_rounds, reverse=True)[:4]
        defs = sorted((o for o in operators if o.get("side") == "Defender"),
                      key=by_rounds, reverse=True)[:4]

        gap = 48 * _SCALE
        col_w = (_W - 2 * _PAD - gap) // 2
        lx, rx = p, p + col_w + gap

        # 列头：攻 / 防
        y += _ascent(19)
        _draw(draw, lx, y, "攻", 19, _ATK, weight=700)
        _draw(draw, rx, y, "防", 19, _DEF, weight=700)
        y += _font(_NOTO, 19).getmetrics()[1] + 12 * _SCALE

        def _cell(cx: int, base: int, op: dict[str, Any]) -> None:
            r = cx + col_w
            nx = _draw(draw, cx, base, op.get("operator", "?"), 21, _BODY, weight=600)
            _draw(draw, nx + 6 * _SCALE, base, f"·{op.get('roundsPlayed', 0)}", 15, _DIM)
            _draw_right(draw, r, base, f"{op.get('kd', 0)}", 21, _WHITE, weight=700)
            _draw_right(draw, r - 78 * _SCALE, base, f"{op.get('winPercent', 0)}%", 17, _BODY)

        for i in range(max(len(atks), len(defs))):
            base = y + _ascent(21)
            if i < len(atks):
                _cell(lx, base, atks[i])
            if i < len(defs):
                _cell(rx, base, defs[i])
            y = base + _font(_NOTO, 21).getmetrics()[1] + 11 * _SCALE

        # 合计（全部干员）
        kills = sum(o.get("kills", 0) for o in operators)
        deaths = sum(o.get("deaths", 0) for o in operators)
        rounds = sum(o.get("roundsPlayed", 0) for o in operators)
        kd = kills / deaths if deaths else float(kills)
        y += 6 * _SCALE
        draw.line([(p, y), (rcol, y)], fill=_LINE, width=1 * _SCALE)
        y += 12 * _SCALE + _ascent(19)
        _draw(draw, p, y, f"合计 {len(operators)} 干员 · 场{rounds}", 19, _GRAY)
        _draw_right(draw, rcol, y, f"KD {kd:.2f}", 19, _GRAY)
        y += _font(_NOTO, 19).getmetrics()[1]

    if not boards and not operators:
        y += _ascent(22)
        _draw(draw, p, y, "没有查询到数据", 22, _GRAY)
        y += _font(_NOTO, 22).getmetrics()[1]

    img = img.crop((0, 0, _W, y + _PAD))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
