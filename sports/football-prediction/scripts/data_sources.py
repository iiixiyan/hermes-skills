"""
免费足彩数据源聚合模块 v1.0
整合: OpenLigaDB(API) + 500.com + 雷速 + Transfermarkt + Soccerway

⚡ 铁律: 所有数据源采集必须是原始完整内容, 一字不改。
   禁止任何总结/归纳/格式化/省略/简化。
"""

import re, json, gzip, urllib.request
from typing import Optional


# ═══════════════════════════════════════════════
# 源1: OpenLigaDB — 免费德甲/德乙API
# ═══════════════════════════════════════════════

OPENLIGA_LEAGUES = {
    'bl1': '德甲', 'bl2': '德乙', 'bl3': '德丙',
}

def fetch_openliga(league='bl1', season=2025):
    """获取德甲完整赛季数据"""
    url = f"https://www.openligadb.de/api/getmatchdata/{league}/{season}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        matches = []
        for m in data:
            if m.get('matchResults'):
                r = m['matchResults'][0]
                matches.append({
                    'home': m['team1']['teamName'],
                    'away': m['team2']['teamName'],
                    'home_goals': r.get('pointsTeam1', 0),
                    'away_goals': r.get('pointsTeam2', 0),
                    'date': m['matchDateTime'][:10],
                    'league': OPENLIGA_LEAGUES.get(league, league),
                })
        return {'source': 'openligadb', 'count': len(matches), 'matches': matches[:10], 'sample': matches[:3]}
    except Exception as e:
        return {'source': 'openligadb', 'error': str(e)}


# ═══════════════════════════════════════════════
# 源2: 500.com — 竞彩赔率+历史数据
# ═══════════════════════════════════════════════

def fetch_500_odds(match_id: str):
    """
    从500.com获取单场赔率分析
    示例: match_id='1093428'
    页面: https://odds.500.com/fenxi/shuju-{match_id}.shtml
    ⚠️ 需要Playwright (JS渲染)
    """
    return {
        'source': '500.com',
        'url': f'https://odds.500.com/fenxi/shuju-{match_id}.shtml',
        'note': '需Playwright浏览器渲染',
        'features': ['百家赔率走势', '凯利指数', '历史同赔', '亚盘变化'],
    }


# ═══════════════════════════════════════════════
# 源3: 搜达足球/雷速 — 国内最全竞彩数据
# ═══════════════════════════════════════════════

LEISU_URLS = {
    'jc_list': 'https://www.leisu.com/jingcai/',           # 竞彩列表
    'bd_list': 'https://www.leisu.com/danchang/',           # 北单列表
    'match_detail': 'https://www.leisu.com/analysis/{mid}/',  # 比赛详情
    'odds_history': 'https://www.leisu.com/odds/{mid}/',    # 赔率历史
}

def get_leisu_url(match_id: str, data_type='match_detail'):
    """获取雷速对应页面URL"""
    url_template = LEISU_URLS.get(data_type, LEISU_URLS['match_detail'])
    return url_template.format(mid=match_id)


# ═══════════════════════════════════════════════
# 源4: 竞彩官网API
# ═══════════════════════════════════════════════

def fetch_sporttery_odds(date: str = None):
    """从竞彩官网获取当日开售比赛"""
    from datetime import date as dt
    target = date or dt.today().strftime('%Y-%m-%d')
    urls = [
        f'https://www.sporttery.cn/jc/jsks/zqspf/json/index.json?pageNo=1',
        'https://webapi.sporttery.cn/gateway/jc/football/getMatchListV2.qry',
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.sporttery.cn/',
            })
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return {'source': 'sporttery', 'url': url, 'status': 'ok', 'sample': str(data)[:200]}
        except Exception as e:
            continue
    return {'source': 'sporttery', 'error': 'all endpoints failed'}


# ═══════════════════════════════════════════════
# 源5: Transfermarkt — 身价数据
# ═══════════════════════════════════════════════

TM_LEAGUES = {
    '日职联': ('https://www.transfermarkt.com/j1-league/startseite/wettbewerb/JAP1', 'JAP1'),
    '英超': ('https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1', 'GB1'),
    '西甲': ('https://www.transfermarkt.com/laliga/startseite/wettbewerb/ES1', 'ES1'),
    '意甲': ('https://www.transfermarkt.com/serie-a/startseite/wettbewerb/IT1', 'IT1'),
    '德甲': ('https://www.transfermarkt.com/bundesliga/startseite/wettbewerb/L1', 'L1'),
    '法甲': ('https://www.transfermarkt.com/ligue-1/startseite/wettbewerb/FR1', 'FR1'),
    '澳超': ('https://www.transfermarkt.com/a-league/startseite/wettbewerb/AUS1', 'AUS1'),
    '芬超': ('https://www.transfermarkt.com/veikkausliiga/startseite/wettbewerb/FIN1', 'FIN1'),
    '瑞超': ('https://www.transfermarkt.com/allsvenskan/startseite/wettbewerb/SE1', 'SE1'),
}

def get_tm_league_url(league_name: str) -> Optional[str]:
    """获取Transfermarkt联赛页面URL"""
    for key, (url, code) in TM_LEAGUES.items():
        if key in league_name or league_name in key:
            return url
    return None


# ═══════════════════════════════════════════════
# 源6: Soccerway — 积分榜+赛程
# ═══════════════════════════════════════════════

SW_LEAGUES = {
    '日职联': 'https://www.soccerway.com/national/japan/j1-league/2026/regular-season/r84312/',
    '英超': 'https://www.soccerway.com/national/england/premier-league/2025-2026/regular-season/r83512/',
}

def get_sw_league_url(league_name: str) -> Optional[str]:
    for key, url in SW_LEAGUES.items():
        if key in league_name:
            return url
    return None


# ═══════════════════════════════════════════════
# 源7: Understat — xG数据 (仅Playwright)
# ═══════════════════════════════════════════════

UNDERSTAT_LEAGUES = {
    '英超': 'https://understat.com/league/EPL',
    '西甲': 'https://understat.com/league/La_liga',
    '德甲': 'https://understat.com/league/Bundesliga',
    '意甲': 'https://understat.com/league/Serie_A',
    '法甲': 'https://understat.com/league/Ligue_1',
}


# ═══════════════════════════════════════════════
# 工具函数: Playwright通用采集器
# ═══════════════════════════════════════════════

PLAYWRIGHT_COLLECT_TEMPLATE = """
import asyncio
from playwright.async_api import async_playwright

async def collect(url, wait_for_text=None, extract_js=None):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path="/usr/bin/chromium-browser")
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        if wait_for_text:
            await page.wait_for_function(f'() => document.body.innerText.includes("{wait_for_text}")', timeout=10000)
        if extract_js:
            result = await page.evaluate(extract_js)
        else:
            result = await page.evaluate("document.body.innerText")
        await browser.close()
        return result
"""


# ═══════════════════════════════════════════════
# 数据源状态检查
# ═══════════════════════════════════════════════

def check_all_sources():
    """检查所有数据源可用性"""
    results = {}
    
    # OpenLigaDB
    r = fetch_openliga('bl1', 2025)
    results['openligadb'] = '✅' if r.get('count', 0) > 0 else '❌'
    
    # 500.com
    try:
        req = urllib.request.Request('https://odds.500.com/', headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=5)
        results['500.com'] = '✅'
    except:
        results['500.com'] = '❌'
    
    # Transfermarkt
    try:
        req = urllib.request.Request('https://www.transfermarkt.com/', headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=5)
        results['transfermarkt'] = '✅'
    except:
        results['transfermarkt'] = '❌'
    
    # Soccerway
    try:
        req = urllib.request.Request('https://www.soccerway.com/', headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, timeout=5)
        results['soccerway'] = '✅'
    except:
        results['soccerway'] = '❌'
    
    return results
