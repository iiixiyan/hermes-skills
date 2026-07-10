#!/usr/bin/env python3
"""
L3数据采集器 — 500彩票网 + 澳客网
自动从500.com首页导航到世界杯→匹配队名→提取shuju页数据
自动从okooo.com匹配队名→提取身价/积分榜

核心函数:
  find_500_id(browser, h_name, a_name) -> (match_id, page_body)
  find_okooo_id(browser, h_name, a_name) -> (match_id, page_body)
  collect_l3(browser, h_name, a_name) -> dict
"""
import os, re, sys
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/usr/bin'
from playwright.sync_api import sync_playwright


def find_500_id(browser, h_name, a_name, timeout=15000):
    """从500.com首页赛程表匹配比赛ID"""
    page = browser.new_page()
    page.set_extra_http_headers({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })
    
    try:
        resp = page.goto('https://odds.500.com/', timeout=timeout, wait_until='domcontentloaded')
        body = page.inner_text('body')
        
        # 在body里找"主队 VS 客队"模式 → 确定比赛索引
        lines = body.split('\n')
        match_idx = -1
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if h_name in line_clean and 'VS' in line_clean and a_name in line_clean:
                match_idx = i
                break
        
        # 获取所有shuju链接（顺序与赛程表一致）
        links = page.query_selector_all('a')
        shuju_links = []
        for link in links:
            href = link.get_attribute('href')
            if href and 'shuju-' in str(href):
                mid = re.search(r'shuju-(\d+)', str(href))
                if mid:
                    shuju_links.append(int(mid.group(1)))
        
        page.close()
        
        if match_idx >= 0 and shuju_links:
            # 使用shuju链接的顺序索引
            # 需要计算匹配比赛在赛程中的位置
            # 简化: 按行号估算
            match_line_num = 0
            for i, line in enumerate(lines):
                if h_name in line and 'VS' in line:
                    if i == match_idx:
                        break
                    match_line_num += 1
            
            if match_line_num < len(shuju_links):
                matched = shuju_links[match_line_num]
            else:
                matched = shuju_links[0] if shuju_links else None
        elif shuju_links:
            matched = shuju_links[0]
        else:
            return None, None
        
        # 获取数据
        page2 = browser.new_page()
        page2.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://odds.500.com/',
        })
        resp2 = page2.goto(f'https://odds.500.com/fenxi/shuju-{matched}.shtml',
                          timeout=timeout, wait_until='domcontentloaded')
        body2 = page2.inner_text('body')
        page2.close()
        
        if len(body2) > 200:
            return matched, body2
        return matched, None
        
    except Exception as e:
        try: page.close()
        except: pass
        return None, None


def find_okooo_id(browser, h_name, a_name, timeout=15000):
    """从澳客网赛程页匹配比赛ID"""
    page = browser.new_page()
    page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0'})
    
    try:
        resp = page.goto('https://www.okooo.com/soccer/league/16/schedule/',
                        timeout=timeout, wait_until='domcontentloaded')
        body = page.inner_text('body')
        
        # 找"主队 VS 客队"行
        lines = body.split('\n')
        match_line_idx = -1
        for i, line in enumerate(lines):
            if f'{h_name}\tVS\t{a_name}' in line or f'{h_name[:2]}\tVS\t{a_name[:2]}' in line:
                match_line_idx = i
                break
        
        if match_line_idx < 0:
            page.close()
            return None, None
        
        # 获取所有match链接（顺序与赛程表一致）
        links = page.query_selector_all('a')
        match_ids = []
        for link in links:
            href = link.get_attribute('href')
            if href and '/soccer/match/' in str(href) and '/odds/' in str(href):
                mid = re.search(r'/soccer/match/(\d+)/', str(href))
                if mid and int(mid.group(1)) not in match_ids:
                    match_ids.append(int(mid.group(1)))
        
        page.close()
        
        # 估算匹配索引: 数"VS"出现在第几个
        vs_count = 0
        for i, line in enumerate(lines):
            if 'VS' in line and len(line) > 10:
                if i == match_line_idx:
                    break
                vs_count += 1
        
        matched = match_ids[vs_count] if vs_count < len(match_ids) else (match_ids[0] if match_ids else None)
        if not matched:
            return None, None
        
        # 获取数据
        page2 = browser.new_page()
        page2.set_extra_http_headers({'User-Agent': 'Mozilla/5.0'})
        resp2 = page2.goto(f'https://www.okooo.com/soccer/match/{matched}/odds/',
                          timeout=timeout, wait_until='domcontentloaded')
        body2 = page2.inner_text('body')
        page2.close()
        
        return matched, body2
        
    except Exception as e:
        try: page.close()
        except: pass
        return None, None


def parse_500(body):
    """解析500彩票网shuju页"""
    data = {}
    if not body or len(body) < 200:
        return data
    
    data['data_source'] = '500'
    
    # 1. FIFA排名3期
    idx = body.find('国际足联排名')
    if idx >= 0:
        data['fifa_section'] = body[idx:idx+500]
    
    # 2. 杯赛积分排名
    idx = body.find('杯赛积分排名')
    if idx >= 0:
        data['group_standings'] = body[idx:idx+600]
    
    # 3. 预计阵容
    idx = body.find('预计阵容')
    if idx >= 0:
        data['predicted_lineup'] = body[idx:idx+500]
    
    # 4. 伤病
    idx = body.find('伤病')
    if idx >= 0:
        data['injuries'] = body[idx:idx+200]
    
    # 5. 停赛
    idx = body.find('停赛')
    if idx >= 0:
        data['suspensions'] = body[idx:idx+200]
    
    # 6. 澳门心水
    idx = body.find('澳门心水')
    if idx >= 0:
        data['macau_tip'] = body[idx:idx+500]
    
    # 7. 近期战绩
    idx = body.find('近期战绩')
    if idx >= 0:
        data['recent_form'] = body[idx:idx+500]
    
    # 8. 未来赛事
    idx = body.find('未来赛事')
    if idx >= 0:
        data['future_fixtures'] = body[idx:idx+400]
    
    # 9. 主客场战绩
    for kw in ['总成绩', '主场', '客场']:
        idx = body.find(kw)
        if idx >= 0:
            data[f'form_{kw}'] = body[idx:idx+200]
    
    return data


def parse_okooo(body):
    """解析澳客网比赛页"""
    data = {}
    if not body or len(body) < 200:
        return data
    
    data['data_source'] = 'okooo'
    
    # 1. 身价
    m = re.findall(r'([\d.]+亿€)', body)
    if m:
        data['market_values'] = m
    
    # 2. 积分榜
    idx = body.find('积分榜')
    if idx >= 0:
        data['standings'] = body[idx:idx+400]
    
    # 3. 球队名称
    for kw in ['世界杯', '小组赛']:
        idx = body.find(kw)
        if idx >= 0:
            data['match_info'] = body[max(0,idx-50):idx+200]
    
    return data


def collect_l3(browser, h_name, a_name):
    """全自动L3采集: 500彩票网 + 澳客网"""
    result = {}
    
    # 500彩票网
    print(f"  500彩票网: 匹配 {h_name} vs {a_name}...", end=' ', flush=True)
    mid_500, body_500 = find_500_id(browser, h_name, a_name)
    if mid_500 and body_500:
        result['500'] = parse_500(body_500)
        result['500']['match_id'] = mid_500
        print(f"✅ ID={mid_500} ({len(body_500)}c)")
    else:
        print(f"❌ mid={mid_500}")
    
    # 澳客网
    print(f"  澳客网: 匹配 {h_name} vs {a_name}...", end=' ', flush=True)
    mid_ok, body_ok = find_okooo_id(browser, h_name, a_name)
    if mid_ok and body_ok:
        result['okooo'] = parse_okooo(body_ok)
        result['okooo']['match_id'] = mid_ok
        print(f"✅ ID={mid_ok} ({len(body_ok)}c)")
    else:
        print(f"❌ mid={mid_ok}")
    
    return result


def l3_to_form_signal(l3_data):
    """L3数据 → form_signal补充字段"""
    signal = {}
    
    if not l3_data:
        return signal
    
    sources = []
    
    # 500彩票网数据
    d500 = l3_data.get('500', {})
    if d500.get('data_source') == '500':
        sources.append('500')
        if d500.get('macau_tip'):
            signal['macau_tip'] = d500['macau_tip'][:300]
        if d500.get('injuries'):
            signal['injuries_500'] = d500['injuries'][:200]
        if d500.get('fifa_section'):
            signal['fifa_500'] = d500['fifa_section'][:300]
    
    # 澳客网数据
    dok = l3_data.get('okooo', {})
    if dok.get('data_source') == 'okooo':
        sources.append('okooo')
        if dok.get('market_values'):
            signal['market_values'] = dok['market_values']
        if dok.get('standings'):
            signal['okooo_standings'] = dok['standings'][:300]
    
    if sources:
        signal['sources_used'] = sources
    
    return signal


# ============================================================
#  测试
# ============================================================
if __name__ == "__main__":
    print("L3数据采集器测试")
    print("="*60)
    
    if len(sys.argv) >= 3:
        h_name, a_name = sys.argv[1], sys.argv[2]
    else:
        h_name, a_name = "荷兰", "瑞典"
    
    print(f"测试: {h_name} vs {a_name}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path='/usr/bin/chromium-browser',
            headless=True,
            args=['--no-sandbox']
        )
        
        l3 = collect_l3(browser, h_name, a_name)
        
        print(f"\n=== 结果 ===")
        for src, data in l3.items():
            print(f"\n[{src}] (match_id={data.get('match_id','?')}):")
            for k, v in data.items():
                if k != 'data_source' and k != 'match_id':
                    val = str(v)[:100]
                    print(f"  {k}: {val}")
        
        sig = l3_to_form_signal(l3)
        if sig:
            print(f"\n→ form_signal: {sig}")
        
        browser.close()
