"""把 operatorStats 返回（顶层 ``operators`` 数组）格式化成可发送文本。

返回结构示例（每个干员一条）::

    {"operator": "Bandit", "side": "Defender", "roundsPlayed": 1451,
     "winPercent": 53.14, "kd": 0.86, "headshotPercent": 38.53,
     "wins": 771, "losses": 680, "kills": 911, "deaths": 1065, ...}
"""
from __future__ import annotations

from typing import Any

#: 默认展示出场最多的前 N 个干员
TOP_N = 8

_SIDE_CN = {"Attacker": "攻", "Defender": "防"}


def format_operator_stats(player_id: str, data: dict[str, Any], top_n: int = TOP_N) -> str:
    operators = data.get("operators") if isinstance(data, dict) else None
    if not operators:
        return f"🎯 {player_id}：没有查询到干员数据"

    ranked = sorted(operators, key=lambda o: o.get("roundsPlayed", 0), reverse=True)

    lines = [f"🎯 {player_id} 干员数据（按出场排序 Top {min(top_n, len(ranked))}）："]
    for op in ranked[:top_n]:
        side = _SIDE_CN.get(op.get("side", ""), op.get("side", "?"))
        lines.append(
            f"{op.get('operator', '?')}({side}) "
            f"场{op.get('roundsPlayed', 0)} "
            f"胜{op.get('winPercent', 0)}% "
            f"KD{op.get('kd', 0)} "
            f"爆头{op.get('headshotPercent', 0)}%"
        )

    # 聚合：用总量重算，避免对各干员的百分比直接做无权平均。
    rounds = sum(o.get("roundsPlayed", 0) for o in operators)
    wins = sum(o.get("wins", 0) for o in operators)
    losses = sum(o.get("losses", 0) for o in operators)
    kills = sum(o.get("kills", 0) for o in operators)
    deaths = sum(o.get("deaths", 0) for o in operators)
    headshots = sum(o.get("headshots", 0) for o in operators)

    win_rate = wins / (wins + losses) * 100 if (wins + losses) else 0
    kd = kills / deaths if deaths else float(kills)
    hs = headshots / kills * 100 if kills else 0

    lines.append(
        f"— 合计 {len(operators)} 干员：场{rounds} "
        f"胜率{win_rate:.1f}% KD{kd:.2f} 爆头{hs:.1f}%"
    )
    return "\n".join(lines)
