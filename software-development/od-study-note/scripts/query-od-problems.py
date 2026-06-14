#!/usr/bin/env python3
"""
查询 complete-data.json 中的 OD 真题数据。

用途：20天计划 Day 文件优化时，按标签（tag）过滤出相关 OD 真题，
     查看来源分布和题目详情，决定每篇文档选用哪些题目。

用法：
  # 按标签查询（返回所有匹配题目的详情 + 按来源统计）
  python3 /path/to/query-od-problems.py 排序

  # 多标签查询（任意标签包含即可）
  python3 /path/to/query-od-problems.py 排序 区间合并

  # 按标题关键词查询（模糊匹配）
  python3 /path/to/query-od-problems.py --title 日志

  # 只看新系统真题
  python3 /path/to/query-od-problems.py 排序 --source "新系统"

  # 查看所有可用标签
  python3 /path/to/query-od-problems.py --list-tags

  # 显示所有题目来源分类
  python3 /path/to/query-od-problems.py --list-sources

  # 限制返回数量
  python3 /path/to/query-od-problems.py 排序 --limit 30

数据文件路径：/tmp/huawei-od-new-system/complete-data.json
"""

import json
import sys
import argparse
from collections import Counter

DATA_PATH = "/tmp/huawei-od-new-system/complete-data.json"


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def list_tags(data):
    """列出所有可用标签及其出现次数"""
    tag_counter = Counter()
    for cat, problems in data.items():
        for p in problems:
            topics = p.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            tag_counter.update(topics)
    # 按次数降序排列
    for tag, count in tag_counter.most_common():
        print(f"  {tag:12s}  {count:>4d} 次")


def list_sources(data):
    """列出所有来源分类及其题目数量"""
    for cat, problems in data.items():
        print(f"  {cat:30s}  {len(problems):>4d} 道题")


def query_by_tag(data, tags):
    """按标签过滤，返回匹配的题目列表"""
    results = []
    for cat, problems in data.items():
        for p in problems:
            topics = p.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            topic_str = " ".join(topics).lower()
            # 检查任意一个标签是否匹配
            for tag in tags:
                if tag.lower() in topic_str:
                    results.append((cat, p))
                    break
    return results


def query_by_title(data, keyword):
    """按标题关键词过滤"""
    results = []
    for cat, problems in data.items():
        for p in problems:
            title = p.get("title", "")
            if keyword.lower() in title.lower():
                results.append((cat, p))
    return results


def filter_by_source(results, source_keyword):
    """按来源关键词进一步筛选"""
    return [(cat, p) for cat, p in results if source_keyword.lower() in cat.lower()]


def print_results(results, limit=None):
    """格式化输出查询结果"""
    source_counter = Counter()
    score_counter = Counter()
    difficulty_counter = Counter()

    if limit:
        results = results[:limit]

    for cat, p in results:
        title = p.get("title", "")
        topics = p.get("topics", [])
        difficulty = p.get("difficulty", "")
        score = p.get("score", "")

        if isinstance(topics, list):
            topics_str = ", ".join(topics)
        else:
            topics_str = str(topics) if topics else ""

        score_info = f" [score={score}]" if score else ""
        diff_info = f" [{difficulty}]" if difficulty else ""
        print(f"  [{cat}]{diff_info}{score_info}")
        print(f"    {title}")
        print(f"    标签: {topics_str}")
        print()

        source_counter[cat] += 1
        if score:
            score_counter[score] += 1
        if difficulty:
            difficulty_counter[difficulty] += 1

    print(f"--- 共 {len(results)} 道题 ---")
    print()
    print("按来源分布:")
    for src, count in source_counter.most_common():
        pct = count / len(results) * 100 if results else 0
        print(f"  {src:35s}  {count:>3d} 道 ({pct:5.1f}%)")


def print_markdown_section(results):
    """以 Markdown 格式输出（适合直接粘贴到 Day 文件中）"""
    print("| # | 题目 | 来源 | 标签 |")
    print("|---|------|------|------|")
    for i, (cat, p) in enumerate(results, 1):
        title = p.get("title", "").replace("|", "\\|")
        topics = p.get("topics", [])
        if isinstance(topics, list):
            topics_str = ", ".join(topics)
        else:
            topics_str = str(topics) if topics else ""
        cat_short = cat.split("-")[0] if "-" in cat else cat[:12]
        print(f"| {i} | {title} | {cat_short} | {topics_str} |")


def main():
    parser = argparse.ArgumentParser(
        description="查询 OD 真题数据，按标签/标题过滤"
    )
    parser.add_argument("keywords", nargs="*", help="标签关键词（空格分隔，任意匹配）")
    parser.add_argument("--title", help="按标题关键词查询")
    parser.add_argument("--source", help="按来源关键词过滤")
    parser.add_argument("--limit", type=int, default=None, help="结果数量上限")
    parser.add_argument("--list-tags", action="store_true", help="列出所有可用标签")
    parser.add_argument("--list-sources", action="store_true", help="列出所有来源分类")
    parser.add_argument("--markdown", action="store_true", help="以 Markdown 表格输出")

    args = parser.parse_args()

    data = load_data()

    if args.list_tags:
        list_tags(data)
        return

    if args.list_sources:
        list_sources(data)
        return

    results = []

    if args.title:
        results = query_by_title(data, args.title)
    elif args.keywords:
        results = query_by_tag(data, args.keywords)
    else:
        print("错误: 请指定标签关键词或使用 --list-tags / --list-sources")
        parser.print_help()
        sys.exit(1)

    if args.source:
        results = filter_by_source(results, args.source)

    if not results:
        print("未找到匹配的题目")
        return

    if args.markdown:
        print_markdown_section(results)
    else:
        # 标准化输出
        print_results(results, args.limit)


if __name__ == "__main__":
    main()
