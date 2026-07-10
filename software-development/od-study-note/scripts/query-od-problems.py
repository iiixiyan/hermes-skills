#!/usr/bin/env python3
"""
查询OD真题数据库 (complete-data.json) 的辅助脚本。

用法：
  python3 /path/to/query-od-problems.py [标签关键词...] [选项]

示例：
  python3 query-od-problems.py 二分
  python3 query-od-problems.py 排序 区间合并
  python3 query-od-problems.py --list-tags
  python3 query-od-problems.py --list-sources
  python3 query-od-problems.py 二分 --markdown --limit 10
  python3 query-od-problems.py --title 日志 --source "双机位"

数据文件路径：/tmp/huawei-od-new-system/complete-data.json
"""

import json
import sys
import os
from collections import Counter

DATA_PATH = "/tmp/huawei-od-new-system/complete-data.json"

def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"数据文件不存在: {DATA_PATH}")
        print("请先克隆仓库: git clone ... huawei-od-new-system-questions")
        sys.exit(1)
    with open(DATA_PATH) as f:
        return json.load(f)

def list_tags(data):
    tags = set()
    for cat, problems in data.items():
        for p in problems:
            t = p.get('topics', [])
            if isinstance(t, str):
                tags.add(t)
            elif isinstance(t, list):
                tags.update(t)
    print("可用标签:")
    for tag in sorted(tags):
        count = sum(1 for c, ps in data.items() for p in ps
                    if isinstance(p.get('topics', []), str) and p['topics'] == tag
                    or isinstance(p.get('topics', []), list) and tag in p['topics'])
        print(f"  {tag} ({count}道题)")

def list_sources(data):
    print("数据来源分类:")
    for cat in data:
        print(f"  {cat} ({len(data[cat])}道题)")

def query(data, keywords, title_filter=None, source_filter=None):
    results = []
    for cat, problems in data.items():
        if source_filter and source_filter not in cat:
            continue
        for p in problems:
            title = p.get('title', '')
            if title_filter and title_filter not in title:
                continue
            tags = p.get('topics', [])
            if isinstance(tags, str):
                tags = [tags]
            tag_str = ' '.join(tags)
            if any(kw in tag_str or kw in title for kw in keywords):
                results.append((cat, title, tags))
    return results

def deduplicate(results):
    seen = {}
    for cat, title, tags in results:
        core = title.split(' - ')[-1] if ' - ' in title else title
        priority = 0
        if '新系统' in cat: priority = 4
        elif '双机位' in cat: priority = 3
        elif '2025' in cat or 'E卷' in cat: priority = 2
        else: priority = 1
        if core not in seen or priority > seen[core][0]:
            seen[core] = (priority, cat, title, tags)
    return list(seen.values())

def show_table(results, limit=None):
    deduped = deduplicate(results)
    if limit:
        deduped = deduped[:limit]
    print("| 来源 | 题名 | 标签 |")
    print("|------|------|------|")
    for _, cat, title, tags in deduped:
        tag_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
        print(f"| {cat} | {title} | {tag_str} |")
    print(f"\n*共 {len(deduped)} 道题（去重后）*")

def show_detail(results, limit=None):
    deduped = deduplicate(results)
    if limit:
        deduped = deduped[:limit]
    for _, cat, title, tags in deduped:
        print(f"[{cat}] {title}")
        print(f"  标签: {tags}")
    print(f"\n共 {len(deduped)} 道题（去重后）")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    data = load_data()

    if '--list-tags' in args:
        list_tags(data)
        return
    if '--list-sources' in args:
        list_sources(data)
        return

    markdown = '--markdown' in args
    args = [a for a in args if a not in ('--markdown',)]

    title_filter = None
    if '--title' in args:
        idx = args.index('--title')
        title_filter = args[idx + 1]
        args = args[:idx] + args[idx+2:]

    source_filter = None
    if '--source' in args:
        idx = args.index('--source')
        source_filter = args[idx + 1]
        args = args[:idx] + args[idx+2:]

    limit = None
    if '--limit' in args:
        idx = args.index('--limit')
        try:
            limit = int(args[idx + 1])
        except (ValueError, IndexError):
            pass
        args = args[:idx] + args[idx+2:]

    keywords = args

    results = query(data, keywords, title_filter, source_filter)
    if not results:
        print(f"未找到匹配 [{', '.join(keywords)}] 的题目")
        return

    counter = Counter()
    for cat, _, _ in results:
        prefix = cat.split('-')[0] if '-' in cat else cat
        counter[prefix] += 1

    secondary = Counter()
    for _, _, tags in results:
        for t in (tags if isinstance(tags, list) else [tags]):
            secondary[t] += 1

    print(f"找到 {len(results)} 道题（去重前）")
    print(f"来源分布: {dict(counter)}")
    print(f"标签分布: {dict(secondary.most_common(5))}")
    print()

    if markdown:
        show_table(results, limit)
    else:
        show_detail(results, limit)

if __name__ == '__main__':
    main()
