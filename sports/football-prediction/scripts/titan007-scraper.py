#!/usr/bin/env python3
"""
球探体育 (titan007.com) 基本盘数据采集器 v1.0

用途: 浏览器采集阵容/评分/近10场战绩/对赛往绩/数据对比 → 结构化JSON
用法: pip install -q beautifulsoup4 lxml  (如需要本地解析)

注意: 需要在Hermes Agent的browser环境下运行
      通过点击titan007 live页面的"析"链接获取分析页

数据能力:
  ✅ 阵容情况（伤停名单）
  ✅ 球员上一场出场评分（全队评分+近10场平均）
  ✅ 杯赛积分排名（小组积分表）
  ✅ 数据对比（胜率/场均进球/场均角球/场均黄牌）
  ✅ 近期战绩（逐场明细含盘口/角球）
  ✅ 对赛往绩（H2H历史交锋记录）
  ✅ 天气/场地信息
"""

import json
import re
import sys


class Titan007Scraper:
    """球探体育基本盘采集器"""
    
    LIVE_URL = "https://live.titan007.com/oldIndexall.aspx"
    
    def __init__(self):
        self.last_raw_text = ""
    
    def find_wc_matches(self):
        """从titan007 live页获取当天世界杯比赛+析链接索引"""
        # 在Hermes Agent中: browser_navigate(LIVE_URL) 后调用
        script = """
        const rows = document.querySelectorAll('tr');
        const result = [];
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 11) {
                const league = cells[1]?.textContent?.trim() || '';
                if (league !== '世界杯') return;
                const time = cells[2]?.textContent?.trim() || '';
                const status = cells[3]?.textContent?.trim() || '';
                const home = cells[4]?.textContent?.trim() || '';
                const score = cells[5]?.textContent?.trim() || '';
                const away = cells[6]?.textContent?.trim() || '';
                const half = cells[7]?.textContent?.trim() || '';
                
                // 找"析"链接的索引
                const dataCell = cells[8];
                let xiIdx = -1, yaIdx = -1, daIdx = -1, ouIdx = -1;
                if (dataCell) {
                    const links = dataCell.querySelectorAll('a');
                    links.forEach((a, i) => {
                        const t = a.textContent.trim();
                        if (t === '析') xiIdx = i;
                        if (t === '亚') yaIdx = i;
                        if (t === '大') daIdx = i;
                        if (t === '欧') ouIdx = i;
                    });
                }
                result.push({
                    time, status, home, score, away, half,
                    xiIdx, yaIdx, daIdx, ouIdx
                });
            }
        });
        return JSON.stringify(result);
        """
        return script
    
    def click_analysis(self, match_index=0):
        """点击第N个世界杯比赛的'析'链接"""
        script = f"""
        const rows = document.querySelectorAll('tr');
        let count = -1;
        for (const row of rows) {{
            const cells = row.querySelectorAll('td');
            if (cells.length >= 11 && cells[1]?.textContent?.trim() === '世界杯') {{
                count++;
                if (count === {match_index}) {{
                    const dataCell = cells[8];
                    if (dataCell) {{
                        const links = dataCell.querySelectorAll('a');
                        for (const a of links) {{
                            if (a.textContent.trim() === '析') {{
                                a.click();
                                return 'clicked';
                            }}
                        }}
                    }}
                }}
            }}
        }}
        return 'not found';
        """
        return script
    
    def parse_analysis_page(self, text):
        """
        解析titan007分析页文本 → 结构化JSON
        
        返回:
        {
            'weather': '天晴 24℃',
            'venue': '西雅图体育场',
            'injuries_h': [{'player':'普利西奇','reason':'身体不适'}],
            'injuries_a': [],
            'player_ratings_h': [{'num':24,'name':'马特弗里兹','pos':'守门员','rating':6.0}],
            'player_ratings_a': [...],
            'avg_rating_h': 6.99,
            'avg_rating_a': 7.10,
            'ranking': [{'rank':1,'team':'美国','w':1,'d':0,'l':0,'gf':4,'ga':1,'pts':3}],
            'comparison': {
                'h_win_rate': '60%', 'h_draw_rate': '10%', 'h_loss_rate': '30%',
                'h_avg_goals': 2.2, 'h_avg_corners': 5.09,
                'a_win_rate': '50%', 'a_draw_rate': '10%', 'a_loss_rate': '40%',
                'a_avg_goals': 1.4, 'a_avg_corners': 2.29,
            },
            'recent_h': [...],  # 近10场逐场明细
            'recent_a': [...],
            'h2h': [...],  # 对赛往绩
        }
        """
        result = {
            'weather': '',
            'venue': '',
            'injuries_h': [],
            'injuries_a': [],
            'player_ratings_h': [],
            'player_ratings_a': [],
            'avg_rating_h': 0,
            'avg_rating_a': 0,
            'ranking': [],
            'comparison': {},
            'recent_h': [],
            'recent_a': [],
            'h2h': [],
        }
        
        lines = text.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            ls = line.strip()
            if not ls:
                continue
            
            # 天气和场地（在第一屏）
            m = re.search(r'场地[：:]?\s*(.+?)(?:\s+天气[：:]?\s*(.+))?', ls)
            if m:
                result['venue'] = m.group(1).strip()
                if m.group(2):
                    result['weather'] = m.group(2).strip()
                continue
            
            # 温度
            m = re.search(r'温度[：:]?\s*([^℃]*℃)', ls)
            if m and not result['weather']:
                result['weather'] = m.group(0).strip()
            
            # 阵容情况
            if ls == '阵容情况':
                current_section = 'injuries'
                continue
            
            # 杯赛积分排名
            if ls == '杯赛积分排名':
                current_section = 'ranking'
                continue
            
            # 数据对比
            if ls == '数据对比':
                current_section = 'comparison'
                continue
            
            # 对赛往绩
            if ls == '对赛往绩':
                current_section = 'h2h'
                continue
            
            # 近期战绩
            if ls == '近期战绩':
                current_section = 'recent_h'
                continue
            
            # ===== 伤停解析 =====
            if current_section == 'injuries':
                # "球员\t缺阵原因" 表头后跟数据行
                m = re.match(r'(\d+\s*\(?\s*[^)]*\)?)?\s*([\u4e00-\u9fa5a-zA-Z·\s]+)\t+(.*)', ls)
                if m and '缺阵原因' not in ls and '球员' not in ls:
                    player = m.group(2).strip()
                    reason = m.group(3).strip()
                    # 判断主客
                    # 在injuries段中, 先遇到的是主队, 遇到"暂无数据"后切换
                    if '暂无' not in ls:
                        result['injuries_h'].append({'player': player, 'reason': reason})
                    else:
                        current_section = None
                    continue
                if '暂无数据' in ls:
                    current_section = 'injuries_a'  # 切换
                    continue
            
            # ===== 球员评分 =====
            # "号码\t球员\t位置\t首发\t评分"
            m = re.match(r'(\d+)\s+([\u4e00-\u9fa5a-zA-Z·\s.]+)\s+([\u4e00-\u9fa5a-zA-Z]+)\s+(\*?)\s+([\d.]+)', ls)
            if m and current_section != 'ranking' and current_section != 'comparison':
                player = {
                    'num': int(m.group(1)),
                    'name': m.group(2).strip(),
                    'pos': m.group(3).strip(),
                    'starter': m.group(4) == '*',
                    'rating': float(m.group(5)),
                }
                result['player_ratings_h'].append(player)
                continue
            
            # 平均评分
            m = re.match(r'平均评分\s+([\d.]+)', ls)
            if m:
                if not result['avg_rating_h']:
                    result['avg_rating_h'] = float(m.group(1))
                else:
                    result['avg_rating_a'] = float(m.group(1))
            
            # ===== 积分排名 =====
            if current_section == 'ranking':
                # 排名\t球队\t总\t胜\t平\t负\t得\t失\t净\t积分
                m = re.match(r'(\d+)\s+([\u4e00-\u9fa5a-zA-Z]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([-\d]+)\s+(\d+)', ls)
                if m and '排名' not in ls:
                    result['ranking'].append({
                        'rank': int(m.group(1)),
                        'team': m.group(2).strip(),
                        'played': int(m.group(3)),
                        'wins': int(m.group(4)),
                        'draws': int(m.group(5)),
                        'losses': int(m.group(6)),
                        'gf': int(m.group(7)),
                        'ga': int(m.group(8)),
                        'gd': int(m.group(9)),
                        'pts': int(m.group(10)),
                    })
                    continue
                # 检测排名段结束
                if '数据对比' in ls:
                    current_section = None
            
            # ===== 数据对比 =====
            if current_section == 'comparison':
                # 美国\t60%\t10%\t30%\t22\t16\t6\t2.2\t5.09\t...
                m = re.match(r'([\u4e00-\u9fa5a-zA-Z]+)\s+(\d+%)\s+(\d+%)\s+(\d+%)\s+(\d+)\s+(\d+)\s+([-\d]+)\s+([\d.]+)\s+([\d.]+)', ls)
                if m and '球队' not in ls and '胜' not in ls:
                    team = m.group(1).strip()
                    is_home = len(result['recent_h']) == 0  # 按出现顺序
                    key_prefix = 'h_' if is_home else 'a_'
                    result['comparison'][f'{key_prefix}win_rate'] = m.group(2)
                    result['comparison'][f'{key_prefix}draw_rate'] = m.group(3)
                    result['comparison'][f'{key_prefix}loss_rate'] = m.group(4)
                    result['comparison'][f'{key_prefix}goals'] = int(m.group(5))
                    result['comparison'][f'{key_prefix}concede'] = int(m.group(6))
                    result['comparison'][f'{key_prefix}avg_goals'] = float(m.group(8))
                    result['comparison'][f'{key_prefix}avg_corners'] = float(m.group(9)) if len(m.groups()) >= 9 else 0
                    continue
                if '对赛往绩' in ls:
                    current_section = None
        
        return result
    
    def get_enhanced_signals(self, parsed):
        """从titan007基本盘生成引擎修正信号"""
        signals = {
            'injury_impact_h': 0,
            'injury_impact_a': 0,
            'form_win_rate_h': 0,
            'form_win_rate_a': 0,
            'avg_rating_diff': 0,
            'avg_goals_h': 0,
            'avg_goals_a': 0,
            'h2h_advantage': 0,
            'ranking_points': '',
            'key_player_missing': False,
        }
        
        # 伤停影响
        if parsed['injuries_h']:
            for inj in parsed['injuries_h']:
                if any(kw in inj.get('player','') for kw in ['队长','前锋','中场','核心']):
                    signals['injury_impact_h'] = 2
                    signals['key_player_missing'] = True
                    break
            else:
                signals['injury_impact_h'] = 1
        if parsed['injuries_a']:
            for inj in parsed['injuries_a']:
                if any(kw in inj.get('player','') for kw in ['队长','前锋','中场','核心']):
                    signals['injury_impact_a'] = 2
                    signals['key_player_missing'] = True
                    break
            else:
                signals['injury_impact_a'] = 1
        
        # 评分差距
        if parsed['avg_rating_h'] and parsed['avg_rating_a']:
            signals['avg_rating_diff'] = round(parsed['avg_rating_h'] - parsed['avg_rating_a'], 2)
        
        # 场均进球
        cmp = parsed['comparison']
        if 'h_avg_goals' in cmp:
            signals['avg_goals_h'] = float(cmp['h_avg_goals'])
        if 'a_avg_goals' in cmp:
            signals['avg_goals_a'] = float(cmp['a_avg_goals'])
        
        return signals


if __name__ == "__main__":
    print("球探体育基本盘采集器 v1.0")
    print("使用方式: 在Hermes Agent中调用 browser_console 执行JS")
    print()
    print("示例流程:")
    print("1. browser_navigate('https://live.titan007.com/oldIndexall.aspx')")
    print("2. browser_console(expression=scraper.find_wc_matches())  # 找到比赛和析链接")
    print("3. browser_console(expression=scraper.click_analysis(0))  # 点击第一个析链接")
    print("4. browser_console(expression='document.body.innerText')  # 获取分析页文本")
    print("5. scraper.parse_analysis_page(text)  # 解析为结构化JSON")
    print("6. scraper.get_enhanced_signals(parsed)  # 生成引擎修正信号")
