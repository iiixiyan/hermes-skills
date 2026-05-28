#!/usr/bin/env python3
"""
竞足数据采集器（ingest.py）v1.0
Level 3 可运行采集器 — 封装59itou数据采集+缓存+重试+降级

用法:
  python3 ingest.py --date 2026-05-28           # 采集指定日期
  python3 ingest.py --date today                  # 采集今天
  python3 ingest.py --matchid 12345               # 采集单场
  python3 ingest.py --list                        # 列出当日比赛

输出: JSON格式，按日期+联赛缓存到 ~/.hermes/skills/sports/db/cache/
"""

import asyncio, json, os, re, sys, argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ============================================================
# 配置
# ============================================================
CACHE_DIR = Path.home() / ".hermes" / "skills" / "sports" / "db" / "cache"
CACHE_TTL = 600  # 同一场次10分钟内不重复采集（秒）

# 竞足前缀（详情页可能变化）
PREFIXES = ["379", "37", "175", "378", "456"]

# 详情页Tab顺序
TABS = ["阵容", "战绩", "欧指", "亚指", "排名", "盈亏"]

# ============================================================
# 缓存层
# ============================================================

def _cache_path(match_id: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{match_id}.json"

def cache_get(match_id: str) -> dict | None:
    p = _cache_path(match_id)
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    age = (datetime.now() - datetime.fromisoformat(data["_cached_at"])).total_seconds()
    if age > CACHE_TTL:
        p.unlink(missing_ok=True)
        return None
    return data

def cache_set(match_id: str, data: dict):
    data["_cached_at"] = datetime.now().isoformat()
    _cache_path(match_id).write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ============================================================
# 采集核心
# ============================================================

async def fetch_list_page(page) -> list[dict]:
    """获取竞足列表页（含matchID、队名、赔率、让球数）"""
    list_urls = [
        "https://kt.59itou.com/627/jingcai/",
        "https://kt.59itou.com/192/jingcai/",
        "https://kt.59itou.com/54/jingcai/",
    ]
    for url in list_urls:
        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(1)
            # 检查是否渲染成功
            text = await page.evaluate("document.body.innerText")
            if "竞彩足球" in text and len(text) > 300:
                # 移除新手引导弹窗
                await page.evaluate("document.querySelector('.layer_jcbet_guide')?.remove()")
                break
        except Exception:
            continue
    else:
        return []  # 所有URL都失败

    # 提取比赛列表
    raw = await page.evaluate("document.body.innerText")
    matches = []
    # 模式：联赛 + 编号 + 主队(+N) + 赔率 + 客队(+N)
    # 示例：解放者杯  周三001  水晶宫(-1) 1.89 3.15 3.78 巴列卡诺(+1)
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 匹配场次号（如"周三001"）
        m = re.match(r'(周[一二三四五六日]\d+)', line)
        if m:
            match_num = m.group(1)
            # 下一行或本行剩余部分
            j = i + 1
            while j < len(lines) and j < i + 8:
                chunk = " ".join(lines[i:j+1])
                # 提取让球数
                handicap_m = re.search(r'\(([+-]?\d+)\)', chunk)
                handicap = int(handicap_m.group(1)) if handicap_m else 0
                # 提取三赔
                odds = re.findall(r'\d+\.\d+', chunk)
                matches.append({
                    "match_num": match_num,
                    "handicap": handicap,
                    "odds_preview": odds[:3] if len(odds) >= 3 else [],
                    "raw_text": chunk[:200],
                })
                break
        i += 1

    return matches

async def fetch_match_detail(page, match_id: str) -> dict:
    """采集单场详情页6Tab数据"""
    # 检查缓存
    cached = cache_get(match_id)
    if cached:
        return cached

    data = {"match_id": match_id, "tabs": {}}

    for prefix in PREFIXES:
        url = f"https://kt.59itou.com/{prefix}/match3/?matchid={match_id}&lotteryId=90&lottery_style=jczq"
        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(1)
            text = await page.evaluate("document.body.innerText")
            if len(text) > 500:
                data["prefix"] = prefix
                break
        except Exception:
            continue
    else:
        data["error"] = "所有前缀均失败"
        return data

    # 逐Tab采集
    for tab_name in TABS:
        try:
            await page.evaluate(f"""
            document.querySelectorAll(".van-tab").forEach(function(t){{
                if (t.textContent.includes("{tab_name}")) t.click();
            }})
            """)
            await asyncio.sleep(0.5)

            # 条件等待
            wait_for = {
                "欧指": "概率转换",
                "亚指": "盘位水位升降",
                "盈亏": "交易",
            }
            keyword = wait_for.get(tab_name, "")
            if keyword:
                try:
                    await page.wait_for_function(
                        f'() => document.body.innerText.includes("{keyword}")',
                        timeout=5000
                    )
                except Exception:
                    await asyncio.sleep(1.5)
            else:
                await asyncio.sleep(1)

            text = await page.evaluate("document.body.innerText")
            data["tabs"][tab_name] = text
        except Exception as e:
            data["tabs"][tab_name] = f"<采集失败: {e}>"

    # 写缓存
    cache_set(match_id, data)
    return data

def extract_odds_changes(text: str) -> dict:
    """从欧指Tab提取指数变化"""
    idx = text.find("指数变化")
    if idx < 0:
        return {}
    nums = re.findall(r"(\d+)家", text[idx:idx+200])
    if len(nums) >= 6:
        return {
            "上升": [int(n) for n in nums[:3]],
            "降低": [int(n) for n in nums[3:6]],
        }
    return {}

def extract_baijia(text: str) -> dict:
    """提取百家平均"""
    idx = text.find("百家平均")
    if idx < 0:
        return {}
    nums = re.findall(r"\d+\.\d+", text[idx:idx+400])
    if len(nums) >= 6:
        return {"初赔": nums[:3], "即赔": nums[3:6]}
    return {}

def extract_h2h(text: str) -> list:
    """提取H2H历史比分"""
    idx = text.find("两队交锋")
    if idx < 0:
        return []
    section = text[idx:idx+500]
    scores = re.findall(r"\b(\d+)-(\d+)\b", section)
    from collections import Counter
    counter = Counter()
    for h, a in scores:
        if int(h) + int(a) <= 7:
            counter[f"{h}-{a}"] += 1
    return [s for s, _ in counter.most_common(3)]

# ============================================================
# CLI入口
# ============================================================

async def main_async():
    parser = argparse.ArgumentParser(description="竞足数据采集器")
    parser.add_argument("--date", help="日期 (YYYY-MM-DD 或 'today')", default="today")
    parser.add_argument("--matchid", help="采集单场matchID")
    parser.add_argument("--list", action="store_true", help="列出当日比赛")
    parser.add_argument("--all", action="store_true", help="采集全部比赛（自动遍历）")
    args = parser.parse_args()

    target_date = date.today() if args.date == "today" else date.fromisoformat(args.date)
    print(f"📅 目标日期: {target_date}")

    if not HAS_PLAYWRIGHT:
        print("❌ 需要 playwright: pip install playwright && playwright install chromium")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium-browser"
        )
        page = await browser.new_page()

        if args.matchid:
            # 采集单场
            data = await fetch_match_detail(page, args.matchid)
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        elif args.list or args.all:
            # 获取列表
            matches = await fetch_list_page(page)
            print(f"📋 共 {len(matches)} 场比赛\n")
            for m in matches:
                print(f"  {m['match_num']} | 让球{m['handicap']:+d} | {m['odds_preview']}")

            if args.all and matches:
                # 需要在北单列表获取matchID
                await page.goto("https://kt.59itou.com/883/danchang/", wait_until="networkidle")
                await asyncio.sleep(1)
                print("\n🔍 请手动输入matchID（或用北单列表自动匹配）")
                # 此处简化：仅打印列表
        else:
            matches = await fetch_list_page(page)
            print(f"📋 共 {len(matches)} 场比赛")
            for m in matches[:5]:
                print(f"  {m['match_num']}")

        await browser.close()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
