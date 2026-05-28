#!/usr/bin/env python3
"""
H2H历史常见比分提取工具 — 从59itou详情页innerText中提取H2H高频比分。

用途：在竞足/北单异常比分预测中，用H2H历史真实比分验证/丰富异常比分推荐。
输出格式支持四级标注：H2H确认 / H2H补充 / H2H高度吻合 / 无标注。

用法：
  python3 extract_h2h_scores.py < inner_text.txt
  # 或作为模块导入
  from extract_h2h_scores import extract_h2h_common_scores, enrich_abnormal_scores_with_h2h
"""

import re
import sys
from collections import Counter

# A型爆冷允许的低比分（总进球 ≤ 2）
A_TYPE_SCORES = {"0-0", "1-0", "0-1", "1-1", "2-0", "0-2"}

# B型大比分允许的高比分（总进球 ≥ 3，但≤7防止异常值）
B_TYPE_SCORES = {"2-1", "1-2", "2-2", "3-1", "1-3", "3-2", "2-3"}


def extract_h2h_common_scores(inner_text: str, top_n: int = 3) -> list[str]:
    """
    从59itou详情页innerText的"两队交锋"段中提取H2H历史比分频次。

    Args:
        inner_text: 详情页document.body.innerText
        top_n: 返回频次最高的前N个比分

    Returns:
        频次降序的比分列表，如 ["1-1", "0-1", "2-0"]
    """
    idx = inner_text.find("两队交锋")
    if idx < 0:
        # 尝试其他可能的H2H标题
        for keyword in ["交锋记录", "历史交锋", "H2H", "两队近期交锋"]:
            idx = inner_text.find(keyword)
            if idx >= 0:
                break
    if idx < 0:
        return []

    # 截取H2H段落（通常500字内）
    h2h_section = inner_text[idx:idx + 500]

    # 提取所有比分（数字-数字格式）
    scores = re.findall(r'\b(\d+)-(\d+)\b', h2h_section)

    score_counter = Counter()
    for (home_goals, away_goals) in scores:
        h, a = int(home_goals), int(away_goals)
        if h + a <= 7:  # 过滤明显异常比分（如5-0, 6-1等）
            score = f"{h}-{a}"
            score_counter[score] += 1

    return [s for s, _ in score_counter.most_common(top_n)]


def is_a_type_score(score: str) -> bool:
    """判断比分是否属于A型爆冷范围（低比分）"""
    return score in A_TYPE_SCORES


def is_b_type_score(score: str) -> bool:
    """判断比分是否属于B型大比分范围（高比分）"""
    return score in B_TYPE_SCORES


def enrich_abnormal_scores_with_h2h(
    abnormal_scores: list[str],
    h2h_common: list[str],
    ab_type: str,  # "A" for 爆冷 or "B" for 大比分
) -> dict:
    """
    用H2H常见比分丰富异常比分推荐。

    Args:
        abnormal_scores: 异常路径模板推荐的比分列表
        h2h_common: extract_h2h_common_scores() 返回的高频比分列表
        ab_type: 异常类型 "A"=爆冷 "B"=大比分

    Returns:
        包含标注信息的 dict:
        {
            "scores": [{"score": "0-1", "label": "H2H确认 ✅"}, ...],
            "h2h_extra": ["0-0"],  # H2H补充比分（不在模板中）
            "overall": "H2H高度吻合 🎯"  # 整体标注
        }
    """
    result = {"scores": [], "h2h_extra": [], "overall": ""}

    # 判断H2H高频比分中哪些在异常模板中
    h2h_set = set(h2h_common[:2])  # top2
    template_set = set(abnormal_scores)

    # 标注每个推荐比分
    matches_found = 0
    for s in abnormal_scores:
        if s in h2h_set:
            result["scores"].append({"score": s, "label": "H2H确认 ✅"})
            matches_found += 1
        else:
            result["scores"].append({"score": s, "label": ""})

    # H2H补充：top2中不在模板且类型不矛盾
    allowed = A_TYPE_SCORES if ab_type == "A" else B_TYPE_SCORES
    for s in h2h_common[:2]:
        if s not in template_set and s in allowed:
            result["h2h_extra"].append(s)

    # 整体标注
    if matches_found >= 2:
        result["overall"] = "H2H高度吻合 🎯"
    elif matches_found >= 1:
        result["overall"] = "H2H历史印证 ✅"
    elif result["h2h_extra"]:
        result["overall"] = ""
    else:
        result["overall"] = ""

    return result


def format_abnormal_output(
    enriched: dict,
    ab_type_label: str,  # e.g. "A1·赔率反转"
    trigger_note: str,  # e.g. "主胜30升0降"
) -> str:
    """
    生成最终的异常比分输出行。

    Args:
        enriched: enrich_abnormal_scores_with_h2h 的返回值
        ab_type_label: 异常类型标签
        trigger_note: 触发条件说明（≤30字）

    Returns:
        格式化的输出字符串
    """
    scores_part = []
    for s in enriched["scores"]:
        if s["label"]:
            scores_part.append(s["score"])
        else:
            scores_part.append(s["score"])

    # 追加H2H补充比分
    for extra in enriched["h2h_extra"]:
        scores_part.append(f"📖{extra}")

    scores_str = "/".join(scores_part)
    h2h_note = enriched["overall"]
    h2h_suffix = f" {h2h_note}" if h2h_note else ""

    return f"🎯 异常比分：{scores_str} 🏷️ {ab_type_label}{h2h_suffix}"


if __name__ == "__main__":
    # CLI模式：从stdin读innerText
    text = sys.stdin.read()
    top_scores = extract_h2h_common_scores(text)
    print("H2H高频比分:", top_scores if top_scores else "无数据")

    if top_scores:
        # 示例：假设A型爆冷模板 [0-1, 1-1]
        enriched = enrich_abnormal_scores_with_h2h(
            ["0-1", "1-1"], top_scores, "A"
        )
        output = format_abnormal_output(enriched, "A1·赔率反转", "主胜30升0降")
        print(output)
