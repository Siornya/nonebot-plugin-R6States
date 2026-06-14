"""把 fullStats 返回格式化成可发送文本。

fullStats 顶层有三块：
- ``operators``：干员明细（operator/side/roundsPlayed/winPercent/kd/headshotPercent...）
- ``platform_families_full_profiles``：各 board(ranked/casual/...)的完整档案
- ``data``：tracker 风格的 platformInfo / metadata(等级、通行证) / segments
"""
from __future__ import annotations

from typing import Any, Optional
from datetime import timezone, datetime, timedelta

#: 默认展示出场最多的前 N 个干员
TOP_N = 8

#: 展示时间用东八区（CN bot）
_CST = timezone(timedelta(hours=8))


def fetched_label(data: dict[str, Any]) -> Optional[str]:
    """数据实际取回时刻（随缓存保存），格式 '更新 06-14 17:30'；无则返回 None。"""
    ts = data.get("_fetched_at")
    if not ts:
        return None
    return "更新 " + datetime.fromtimestamp(ts, _CST).strftime("%m-%d %H:%M")

_SIDE_CN = {"Attacker": "攻", "Defender": "防"}
_BOARD_CN = {
    "ranked": "排位", "casual": "休闲", "standard": "标准",
    "event": "活动", "warmup": "热身",
}

#: 1000 起每档 100 分、每大段 5 小级；<1000 未定级，>=4500 冠军。
_RANK_TIERS = ("紫铜", "青铜", "白银", "黄金", "铂金", "翡翠", "钻石")


def rank_name(mmr: int) -> str:
    if mmr < 1000:
        return "未定级"
    if mmr >= 4500:
        return "冠军"
    idx = (mmr - 1000) // 100
    return f"{_RANK_TIERS[idx // 5]}{5 - idx % 5}"


def _format_boards(profiles: list[dict[str, Any]]) -> list[str]:
    """各 board 取最新赛季档案，输出概览行；排位行补段位名。"""
    out: list[str] = []
    for fam in profiles:
        for board in fam.get("board_ids_full_profiles") or []:
            fps = board.get("full_profiles") or []
            if not fps:
                continue
            fp = max(fps, key=lambda f: f.get("season_id", 0))
            p = fp.get("profile") or {}
            wins, losses = p.get("wins", 0), p.get("losses", 0)
            kills, deaths = p.get("kills", 0), p.get("deaths", 0)
            wr = wins / (wins + losses) * 100 if (wins + losses) else 0
            kd = kills / deaths if deaths else float(kills)
            bid = board.get("board_id", "")
            name = _BOARD_CN.get(bid, bid or "?")
            rp = p.get("rank_points", 0)
            rank_str = f"{rank_name(rp)} " if bid == "ranked" else ""
            out.append(
                f"{name} {rank_str}RP{rp}({p.get('max_rank_points', 0)}) "
                f"胜负{wins}/{losses}({wr:.0f}%) KD{kd:.2f} 掉线{p.get('abandon', 0)}"
            )
    return out


def _format_operators(operators: list[dict[str, Any]], top_n: int) -> list[str]:
    ranked = sorted(operators, key=lambda o: o.get("roundsPlayed", 0), reverse=True)
    out: list[str] = []
    for op in ranked[:top_n]:
        side = _SIDE_CN.get(op.get("side", ""), op.get("side", "?"))
        out.append(
            f"{op.get('operator', '?')}({side}) "
            f"场{op.get('roundsPlayed', 0)} "
            f"胜{op.get('winPercent', 0)}% "
            f"KD{op.get('kd', 0)}"
        )
    # 聚合：用总量重算，避免对各干员百分比做无权平均
    kills = sum(o.get("kills", 0) for o in operators)
    deaths = sum(o.get("deaths", 0) for o in operators)
    rounds = sum(o.get("roundsPlayed", 0) for o in operators)
    kd = kills / deaths if deaths else float(kills)
    out.append(f"— 合计 {len(operators)} 干员 场{rounds} KD{kd:.2f}")
    return out


def format_full_stats(player_id: str, data: dict[str, Any], top_n: int = TOP_N) -> str:
    info = data.get("data") or {}
    handle = (info.get("platformInfo") or {}).get("platformUserHandle") or player_id
    meta = info.get("metadata") or {}

    lines = [f"🎯 {handle} 数据快照"]

    head_bits = []
    if meta.get("clearanceLevel") is not None:
        head_bits.append(f"等级{meta['clearanceLevel']}")
    if meta.get("battlepassLevel") is not None:
        head_bits.append(f"通行证{meta['battlepassLevel']}")
    if head_bits:
        lines.append("　".join(head_bits))

    board_lines = _format_boards(data.get("platform_families_full_profiles") or [])
    if board_lines:
        lines.append("— 档案 —")
        lines.extend(board_lines)

    operators = data.get("operators") or []
    if operators:
        lines.append("— 干员 Top —")
        lines.extend(_format_operators(operators, top_n))

    if not board_lines and not operators:
        return f"🎯 {handle}：没有查询到数据"

    label = fetched_label(data)
    if label:
        lines.append(label)
    return "\n".join(lines)
