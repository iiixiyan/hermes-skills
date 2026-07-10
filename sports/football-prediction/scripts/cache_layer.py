#!/usr/bin/env python3
"""
通用缓存模块 v1.0 (2026-06-21)
为所有数据源增加本地缓存，避免重复请求。
支持: 新浪API、59itou API、网页数据、计算中间结果。

用法:
  from cache_layer import cache_get, cache_set, cache_clear

  # API数据缓存15分钟
  data = cache_get('sina_odds_3625106', category='sina_api')
  if data is None:
      data = fetch_from_api()
      cache_set('sina_odds_3625106', data, category='sina_api')

  # 网页数据缓存30分钟
  html = cache_get('titan007_12345', category='webpage')

缓存有效期:
  sina_api: 900秒 (15分钟)
  fiftynine_api: 900秒 (15分钟)
  webpage: 1800秒 (30分钟)
  computed: 3600秒 (60分钟)

文件存储: ~/.hermes/cache/{category}/{hash_key}.json
  每个缓存文件包含: {timestamp, value}
  自动创建目录，线程安全

函数:
  cache_get(key, category='webpage') -> any  # None=未命中
  cache_set(key, value, category='webpage')  # 写入缓存
  cache_clear(category=None)  # 清除指定类别或全部
  cache_stats() -> dict  # 各类别缓存统计(文件数/总大小/命中率)
"""

import json
import os
import hashlib
import threading
import time
from collections import defaultdict

# ============ 配置 ============
CACHE_BASE = os.path.expanduser("~/.hermes/cache")

# 各类别缓存有效期(秒)
CACHE_TTL = {
    'sina_api': 900,       # 15分钟
    'fiftynine_api': 900,  # 15分钟
    'webpage': 1800,       # 30分钟
    'computed': 3600,      # 60分钟
}

# 默认类别
DEFAULT_CATEGORY = 'webpage'

# 线程锁 (文件写入安全)
_lock = threading.Lock()

# 命中率统计 (线程安全)
_hit_count = defaultdict(int)     # {category: hits}
_miss_count = defaultdict(int)    # {category: misses}


def _hash_key(key: str) -> str:
    """将字符串key转为短哈希文件名"""
    return hashlib.md5(key.encode('utf-8')).hexdigest()[:16]


def _ensure_category_dir(category: str) -> str:
    """确保缓存目录存在，返回路径"""
    cat_dir = os.path.join(CACHE_BASE, category)
    os.makedirs(cat_dir, exist_ok=True)
    return cat_dir


def _cache_filepath(key: str, category: str) -> str:
    """获取缓存文件路径"""
    hkey = _hash_key(key)
    cat_dir = _ensure_category_dir(category)
    return os.path.join(cat_dir, f"{hkey}.json")


def cache_get(key: str, category: str = DEFAULT_CATEGORY):
    """
    读取缓存。
    返回缓存值 (可能为任意类型)，若未命中或已过期返回 None。
    """
    fpath = _cache_filepath(key, category)

    try:
        with _lock:
            if not os.path.exists(fpath):
                _miss_count[category] += 1
                return None

            with open(fpath, 'r', encoding='utf-8') as f:
                record = json.load(f)

        timestamp = record.get('timestamp', 0)
        ttl = CACHE_TTL.get(category, 900)

        if time.time() - timestamp > ttl:
            # 过期了，删除并返回 None
            with _lock:
                try:
                    os.remove(fpath)
                except OSError:
                    pass
            _miss_count[category] += 1
            return None

        _hit_count[category] += 1
        return record.get('value')

    except Exception:
        # 任何异常视为未命中
        _miss_count[category] += 1
        return None


def cache_set(key: str, value, category: str = DEFAULT_CATEGORY):
    """
    写入缓存。
    将 value 序列化为 JSON 存入文件。
    """
    fpath = _cache_filepath(key, category)
    record = {
        'timestamp': time.time(),
        'value': value,
    }

    with _lock:
        try:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 写入失败不阻塞调用方
            print(f"⚠️ 缓存写入失败 [{category}:{key}]: {e}")


def cache_clear(category: str | None = None):
    """
    清除缓存。
    - category=None: 清除所有类别
    - category='sina_api': 仅清除该类
    """
    with _lock:
        if category is None:
            # 清除全部
            for cat in CACHE_TTL:
                cat_dir = os.path.join(CACHE_BASE, cat)
                if os.path.isdir(cat_dir):
                    for fname in os.listdir(cat_dir):
                        if fname.endswith('.json'):
                            try:
                                os.remove(os.path.join(cat_dir, fname))
                            except OSError:
                                pass
            # 重置统计
            _hit_count.clear()
            _miss_count.clear()
            print("🧹 所有缓存已清除")
        else:
            cat_dir = os.path.join(CACHE_BASE, category)
            if os.path.isdir(cat_dir):
                removed = 0
                for fname in os.listdir(cat_dir):
                    if fname.endswith('.json'):
                        try:
                            os.remove(os.path.join(cat_dir, fname))
                            removed += 1
                        except OSError:
                            pass
                _hit_count[category] = 0
                _miss_count[category] = 0
                print(f"🧹 缓存 [{category}] 已清除 ({removed} 文件)")
            else:
                print(f"ℹ️ 缓存类别 [{category}] 不存在")


def cache_stats() -> dict:
    """
    获取各类别缓存统计。
    返回: {
        'categories': {
            'sina_api': {'files': N, 'size_bytes': N, 'hits': N, 'misses': N, 'hit_rate': 0.x},
            ...
        },
        'total_files': N,
        'total_size_bytes': N,
    }
    """
    stats = {
        'categories': {},
        'total_files': 0,
        'total_size_bytes': 0,
    }

    for cat in CACHE_TTL:
        cat_dir = os.path.join(CACHE_BASE, cat)
        files = 0
        size = 0
        if os.path.isdir(cat_dir):
            for fname in os.listdir(cat_dir):
                if fname.endswith('.json'):
                    fpath = os.path.join(cat_dir, fname)
                    files += 1
                    try:
                        size += os.path.getsize(fpath)
                    except OSError:
                        pass

        hits = _hit_count.get(cat, 0)
        misses = _miss_count.get(cat, 0)
        total_req = hits + misses
        hit_rate = round(hits / total_req, 4) if total_req > 0 else 0.0

        stats['categories'][cat] = {
            'files': files,
            'size_bytes': size,
            'hits': hits,
            'misses': misses,
            'hit_rate': hit_rate,
        }
        stats['total_files'] += files
        stats['total_size_bytes'] += size

    return stats


def cache_get_or_set(key: str, func, category: str = DEFAULT_CATEGORY, *args, **kwargs):
    """
    便捷方法: 先尝试读取缓存，未命中则调用 func() 后写入缓存。
    用法:
        data = cache_get_or_set('my_key', fetch_data, 'sina_api')
    """
    cached = cache_get(key, category)
    if cached is not None:
        return cached

    value = func(*args, **kwargs)
    if value is not None:
        cache_set(key, value, category)
    return value


# ============ 命令行入口 ============
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="缓存管理工具")
    parser.add_argument("action", choices=["stats", "clear"], help="操作")
    parser.add_argument("--category", type=str, help="缓存类别，不指定则全部")

    args = parser.parse_args()

    if args.action == "stats":
        s = cache_stats()
        print(f"📊 缓存统计")
        print(f"{'类别':<15} {'文件数':>8} {'大小':>10} {'命中率':>8}")
        print("-" * 45)
        for cat, info in s['categories'].items():
            size_kb = info['size_bytes'] / 1024
            hr = f"{info['hit_rate']*100:.1f}%"
            print(f"{cat:<15} {info['files']:>8} {size_kb:>8.1f}KB {hr:>8}")
        total_kb = s['total_size_bytes'] / 1024
        print("-" * 45)
        print(f"{'总计':<15} {s['total_files']:>8} {total_kb:>8.1f}KB")
    elif args.action == "clear":
        cache_clear(args.category)
