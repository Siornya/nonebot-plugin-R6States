from typing import Dict, List


def format_overview(sections: Dict[str, List[str]], full_mode: bool) -> str:
    """
    接收解析后的 sections 字典，将每个 section 的内容格式化为字符串。

    参数:
        sections: {section_name: [texts]}

    返回:
        一个字符串，可直接发送给 bot
    """
    contexts = {}

    for section, texts in sections.items():
        new_texts = []
        if section == "Current Season":
            new_texts.append(" ".join(texts[0:4]))  # RP
            new_texts.append(" ".join(texts[i] for i in [4, 5, 7]))  # ELO
            # Playlist KD Win%
            if not full_mode:
                new_texts.append(" ".join(texts[8:11]))
                new_texts.append(" ".join(texts[11:14]))
            else:
                idx = 8
                while idx < len(texts):
                    new_texts.append(" ".join(texts[idx:idx + 3]))
                    idx += 3

        elif section == "Season Peaks":
            idx = 3
            # best
            new_texts.append(" ".join(texts[0:3]))
            while texts[idx] != "SEASON":
                new_texts.append(" ".join(texts[idx:idx + 5]))
                idx += 5
            # season
            new_texts.append(" ".join(texts[idx:idx + 3]))
            idx += 3
            pre5 = min(idx + 25, len(texts))
            while idx < pre5:
                new_texts.append(" ".join(texts[idx:idx + 5]))
                idx += 5

        elif section == "Lifetime Overall":
            fixed_groups = [(0, 2), (2, 4), (6, 8), (8, 10), (10, 12), (20, 22)]
            for start, end in fixed_groups:
                new_texts.append(" ".join(texts[start:end]))
            if full_mode:
                for idx in range(12, 20, 2):
                    new_texts.append(" ".join(texts[idx:idx + 2]))

        elif section in ["Lifetime Ranked", "Lifetime Unranked + Quick Match"]:
            fixed_groups = [(0, 2), (2, 4), (4, 6), (14, 16)]
            for start, end in fixed_groups:
                new_texts.append(" ".join(texts[start:end]))
            if full_mode:
                for idx in range(6, 14, 2):
                    new_texts.append(" ".join(texts[idx:idx + 2]))

        elif section == "All Matches":
            idx = 2
            new_texts.append("".join(texts[idx:]))
            # while texts[idx] != "All Matches":
            #     new_texts.append(" ".join(texts[idx:idx + 2]))

        else:  # season overview
            for start, end in [(0, 1), (1, 3)]:
                new_texts.append(" ".join(texts[start:end]))

            if full_mode:
                for start, end in [(3, 5), (5, 7), (7, 9)]:
                    new_texts.append(" ".join(texts[start:end]))

            for start, end in [(12, 14), (14, 16), (18, 21), (21, 24), (24, 26), (26, 28)]:
                new_texts.append(" ".join(texts[start:end]))

            if full_mode:
                for start, end in [
                    (28, 31), (31, 34), (34, 37), (37, 40), (40, 42), (42, 44), (44, 46), (46, 48), (48, 50), (50, 52)]:
                    new_texts.append(" ".join(texts[start:end]))

        contexts[section] = new_texts

    lines = []

    for section, texts in contexts.items():
        lines.append(f"===== {section} =====")  # section 标题
        lines.extend(texts)  # 内容
        lines.append("")  # 每个 section 之间空一行

    return "\n".join(lines)
