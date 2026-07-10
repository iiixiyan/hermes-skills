#!/usr/bin/env python3
"""
天天盈球 (ttyingqiu.com) 基本面数据采集器 v1.0
用途: 用浏览器提取阵容/阵型/伤停/综合实力分析 → 结构化JSON注入预测引擎
用法: 作为库 from ttyingqiu_scraper import TTYingqiuScraper
      或 CLI: python3 ttyingqiu-scraper.py --match-id <matchId> [--output <file>]

注意: 只能在 Hermes Agent 环境中运行（依赖 browser_* 工具）
"""

import json
import re
import sys

# ==================== 已知世界杯MatchID对照表 ====================
# 从天天盈球 https://www.ttyingqiu.com/jczq 获取
# 格式: 比赛日期 -> [(matchId, 主队, 客队, 轮次)]
WORLDCUP_MATCHES = {
    "2026-06-11": [
        (1921022, "墨西哥", "南非", 1),  # 墨西哥2-0南非 ✅
        (1921023, "韩国", "捷克", 1),  # 韩国2-1捷克 ✅
    ],
    "2026-06-12": [
        (1921024, "加拿大", "波黑", 1),  # 加拿大1-1波黑 ✅
        (1921025, "美国", "巴拉圭", 1),  # 美国4-1巴拉圭 ✅
    ],
    "2026-06-13": [
        (1921026, "卡塔尔", "瑞士", 1),  # 卡塔尔1-1瑞士 ✅
        (1921027, "巴西", "摩洛哥", 1),  # 巴西1-1摩洛哥 ✅
        (1921028, "海地", "苏格兰", 1),  # 海地0-1苏格兰 ✅
        (1921029, "澳大利亚", "土耳其", 1),  # 澳大利亚2-0土耳其 ✅
    ],
    "2026-06-14": [
        (1921030, "德国", "库拉索", 1),  # 德国7-1库拉索 ✅
        (1921031, "荷兰", "日本", 1),  # 荷兰2-2日本 ✅
        (1921032, "科特迪瓦", "厄瓜多尔", 1),  # 科特迪瓦1-0厄瓜多尔 ✅
        (1921033, "瑞典", "突尼斯", 1),  # 瑞典5-1突尼斯 ✅
    ],
    "2026-06-15": [
        (1921034, "西班牙", "佛得角", 1),  # 西班牙0-0佛得角 ✅
        (1921035, "比利时", "埃及", 1),  # 比利时1-1埃及 ✅
        (1921036, "沙特", "乌拉圭", 1),  # 沙特1-1乌拉圭 ✅
        (1921037, "伊朗", "新西兰", 1),  # 伊朗2-2新西兰 ✅
    ],
    "2026-06-16": [
        (1921038, "法国", "塞内加尔", 1),  # 法国3-1塞内加尔 ✅
        (1921039, "伊拉克", "挪威", 1),  # 伊拉克1-4挪威 ✅
        (1921040, "阿根廷", "阿尔及利亚", 1),  # 阿根廷3-0阿尔及利亚 ✅
    ],
    "2026-06-17": [
        (1921041, "奥地利", "约旦", 1),  # 奥地利3-1约旦 ✅
        (1921042, "葡萄牙", "民主刚果", 1),  # 葡萄牙1-1民主刚果 ✅
        (1921043, "英格兰", "克罗地亚", 1),  # 英格兰4-2克罗地亚 ✅
        (1921044, "加纳", "巴拿马", 1),  # 加纳1-0巴拿马 ✅
        (1921045, "乌兹别克", "哥伦比亚", 1),  # 乌兹别克1-3哥伦比亚 ✅
    ],
    "2026-06-18": [
        (1921046, "捷克", "南非", 2),  # 捷克1-1南非 ✅
        (1921047, "瑞士", "波黑", 2),  # 瑞士4-1波黑 ✅
        (1921048, "加拿大", "卡塔尔", 2),  # 加拿大6-0卡塔尔 ✅
        (1921049, "墨西哥", "韩国", 2),  # 墨西哥1-0韩国 ✅
    ],
    "2026-06-20": [
        (1921050, "美国", "澳大利亚", 2),
        (1921051, "苏格兰", "摩洛哥", 2),
        (1921052, "巴西", "海地", 2),
        (1921053, "土耳其", "巴拉圭", 2),
    ],
    "2026-06-21": [
        (1921054, "荷兰", "瑞典", 2),
        (1921055, "德国", "科特迪瓦", 2),
        (1921056, "厄瓜多尔", "库拉索", 2),
        (1921057, "突尼斯", "日本", 2),
    ],
    "2026-06-22": [
        (1921058, "西班牙", "沙特", 2),
        (1921059, "比利时", "伊朗", 2),
        (1921060, "乌拉圭", "新西兰", 2),
        (1921061, "埃及", "佛得角", 2),
        (1921062, "法国", "葡萄牙", 2),
        (1921063, "挪威", "英格兰", 2),
        (1921064, "阿根廷", "加纳", 2),
        (1921065, "哥伦比亚", "奥地利", 2),
    ],
}


class TTYingqiuScraper:
    """天天盈球基本面采集器 — 注意: 需在Hermes Agent的browser环境下运行"""
    
    BASE_URL = "https://www.ttyingqiu.com/live/zq/matchDetail/info"
    
    def __init__(self):
        self.last_raw_text = ""
    
    def get_match_url(self, match_id):
        return f"{self.BASE_URL}/{match_id}"
    
    def parse_prose_data(self, text):
        """
        从天天盈球详情页document.body.innerText解析结构化基本面数据
        
        返回:
        {
            'formation_h': '4-3-3',     # 主队阵型
            'formation_a': '4-4-2',     # 客队阵型  
            'lineup_h': [...],           # 主队首发
            'lineup_a': [...],           # 客队首发
            'injuries_h': [...],         # 主队伤停
            'injuries_a': [...],         # 客队伤停
            'strength_text': '',         # 综合实力分析文本
            'pros_h': [...],             # 主队有利因素
            'cons_h': [...],             # 主队不利因素
            'pros_a': [...],             # 客队有利因素
            'cons_a': [...],             # 客队不利因素
            'intel': '',                 # 精选情报
            'h_strength': 50,            # 主队综合实力分(0-100)
            'a_strength': 50,            # 客队综合实力分(0-100)
            'h_recent': {'w':0,'d':0,'l':0},  # 主近10场
            'a_recent': {'w':0,'d':0,'l':0},  # 客近10场
        }
        """
        result = {
            'formation_h': None,
            'formation_a': None,
            'lineup_h': [],
            'lineup_a': [],
            'injuries_h': [],
            'injuries_a': [],
            'injury_recovery_days_h': None,  # 主队最短伤停恢复天数
            'injury_recovery_days_a': None,  # 客队最短伤停恢复天数
            'strength_text': '',
            'pros_h': [],
            'cons_h': [],
            'pros_a': [],
            'cons_a': [],
            'intel': '',
            'h_strength': 50,
            'a_strength': 50,
            'h_recent': {'w': 0, 'd': 0, 'l': 0},
            'a_recent': {'w': 0, 'd': 0, 'l': 0},
        }
        
        lines = text.split('\n')
        current_section = None
        home_side = None  # True=主队, False=客队
        
        for i, line in enumerate(lines):
            line_s = line.strip()
            
            # === 阵型提取 ===
            m = re.search(r'阵型[:：]\s*(\d+[-－]\d+[-－]\d+)', line_s)
            if m:
                formation = m.group(1).replace('－', '-')
                if home_side is None or home_side is True:
                    result['formation_h'] = formation
                else:
                    result['formation_a'] = formation
            
            # === 近10场战绩 ===
            m = re.search(r'近10场.*?(\d+)胜.*?(\d+)平.*?(\d+)负', line_s)
            if m:
                w, d, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if home_side is None or home_side is True:
                    result['h_recent'] = {'w': w, 'd': d, 'l': l}
                else:
                    result['a_recent'] = {'w': w, 'd': d, 'l': l}
                continue
            
            # === 近10场（不含"各项赛事"前缀）===
            m = re.search(r'近\s*10\s*[场场].*?(\d+)胜.*?(\d+)平.*?(\d+)负', line_s)
            if m:
                w, d, l = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if home_side is None or home_side is True:
                    result['h_recent'] = {'w': w, 'd': d, 'l': l}
                else:
                    result['a_recent'] = {'w': w, 'd': d, 'l': l}
                continue
            
            # === 综合实力分析 ===
            if '综合实力' in line_s and ('差距' in line_s or '占优' in line_s or '分析' in line_s):
                result['strength_text'] += line_s + '\n'
                continue
            
            # === 精选情报 ===
            if line_s.startswith('精选情报') or line_s.startswith('赛前情报'):
                current_section = 'intel'
                continue
            
            # === 有利/不利因素 ===
            m = re.search(r'有利\s*\((\d+)\)', line_s)
            if m:
                current_section = 'pros_h' if home_side is None or home_side else 'pros_a'
                continue
            
            m = re.search(r'不利\s*\((\d+)\)', line_s)
            if m:
                current_section = 'cons_h' if home_side is None or home_side else 'cons_a'
                continue
            
            # === 提取具体情报条目 ===
            if current_section == 'intel' and line_s:
                result['intel'] += line_s + '\n'
            
            # 有利条目
            if current_section in ['pros_h', 'pros_a'] and line_s and len(line_s) > 5:
                target = result['pros_h'] if current_section == 'pros_h' else result['pros_a']
                if not line_s.startswith('有利'):
                    target.append(line_s)
            
            # 不利条目
            if current_section in ['cons_h', 'cons_a'] and line_s and len(line_s) > 5:
                target = result['cons_h'] if current_section == 'cons_h' else result['cons_a']
                if not line_s.startswith('不利'):
                    target.append(line_s)
        
        # === 综合实力打分（文本分析）===
        strength_text = result['strength_text']
        if '无明显差距' in strength_text or '势均力敌' in strength_text:
            result['h_strength'] = 50
            result['a_strength'] = 50
        elif '主队占优' in strength_text:
            result['h_strength'] = 65
            result['a_strength'] = 45
        elif '客队占优' in strength_text:
            result['h_strength'] = 45
            result['a_strength'] = 65
        elif '主队优势' in strength_text:
            result['h_strength'] = 60
            result['a_strength'] = 48
        elif '实力差距' in strength_text:
            # 提取具体数字
            m = re.search(r'实力差距[约]?(\d+)', strength_text)
            if m:
                gap = int(m.group(1))
                if '主队占优' in strength_text or '看好主队' in strength_text:
                    result['h_strength'] = min(50 + gap//2, 85)
                    result['a_strength'] = max(50 - gap//2, 15)
                else:
                    result['a_strength'] = min(50 + gap//2, 85)
                    result['h_strength'] = max(50 - gap//2, 15)
        
        # === 伤停提取（含恢复时间解析）===
        injury_section = False
        home_min_recovery = None  # 记录主队最短恢复天数
        away_min_recovery = None  # 记录客队最短恢复天数
        for line in lines:
            ls = line.strip()
            if '伤停' in ls and ('影响' in ls or '名单' in ls):
                injury_section = True
                continue
            if injury_section and ('主力' in ls or '前锋' in ls or '中场' in ls or '后卫' in ls or '门将' in ls):
                if '主队' in ls or home_side is not False:
                    result['injuries_h'].append(ls)
                    # 解析恢复时间
                    recovery_days = self._parse_recovery_days(ls)
                    if recovery_days is not None:
                        if home_min_recovery is None or recovery_days < home_min_recovery:
                            home_min_recovery = recovery_days
                else:
                    result['injuries_a'].append(ls)
                    # 解析恢复时间
                    recovery_days = self._parse_recovery_days(ls)
                    if recovery_days is not None:
                        if away_min_recovery is None or recovery_days < away_min_recovery:
                            away_min_recovery = recovery_days
            if injury_section and ('阵容' in ls or '首发' in ls):
                injury_section = False
        
        # 写入最短恢复天数
        result['injury_recovery_days_h'] = home_min_recovery
        result['injury_recovery_days_a'] = away_min_recovery
        
        return result
    
    @staticmethod
    def _parse_recovery_days(text):
        """
        从伤停文本中提取预计恢复天数。

        参数:
            text: 伤停文本，如 "预计2周"、"预计3周"、"预计10天"、"预计1个月"

        返回:
            int or None: 恢复天数，无法解析时返回None
        """
        if not text:
            return None
        
        # 匹配 "预计X周"、"预计X月"、"预计X天" 模式
        m = re.search(r'预计\s*(\d+)\s*(周|个月?|天|日)', text)
        if not m:
            # 尝试匹配中文数字
            m = re.search(r'预计\s*([一二三四五六七八九十]+)\s*(周|个月?|天|日)', text)
            if not m:
                return None
        
        num_str = m.group(1)
        unit = m.group(2)
        
        # 中文数字转阿拉伯数字
        cn_num_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        }
        if num_str in cn_num_map:
            num = cn_num_map[num_str]
        else:
            try:
                num = int(num_str)
            except ValueError:
                return None
        
        # 按单位换算天数
        if unit == '天' or unit == '日':
            return num
        elif unit.startswith('周'):
            return num * 7
        elif unit.startswith('个') or unit.startswith('月'):
            return num * 30  # 按30天/月估算
        
        return None
    
    def get_enhanced_signals(self, parsed_data):
        """
        从基本面数据生成信号修正，供v9引擎使用

        返回:
        {
            'home_strength_edge': 0/+1/+2,   # 主队综合实力优势等级
            'away_strength_edge': 0/+1/+2,   # 客队综合实力优势等级
            'form_edge_home': 0/+1,           # 主队状态优势
            'form_edge_away': 0/+1,           # 客队状态优势
            'injury_impact_h': 0/1/2,         # 主队伤停影响(0=无,1=轻,2=重)
            'injury_impact_a': 0/1/2,
            'injury_recovery_days_h': None,   # 主队最短伤停恢复天数
            'injury_recovery_days_a': None,   # 客队最短伤停恢复天数
            'lineup_known': False,             # 是否有首发阵容数据
            'strength_gap': 0,                 # 综合实力差(正=主强)
        }
        """
        signals = {
            'home_strength_edge': 0,
            'away_strength_edge': 0,
            'form_edge_home': 0,
            'form_edge_away': 0,
            'injury_impact_h': 0,
            'injury_impact_a': 0,
            'injury_recovery_days_h': None,
            'injury_recovery_days_a': None,
            'lineup_known': False,
            'strength_gap': 0,
            'form_diff': 0,
        }
        
        # 实力差
        gap = parsed_data['h_strength'] - parsed_data['a_strength']
        signals['strength_gap'] = gap
        if gap >= 20:
            signals['home_strength_edge'] = 2
        elif gap >= 10:
            signals['home_strength_edge'] = 1
        elif gap <= -20:
            signals['away_strength_edge'] = 2
        elif gap <= -10:
            signals['away_strength_edge'] = 1
        
        # 状态差
        h_form = parsed_data['h_recent']['w'] - parsed_data['h_recent']['l']
        a_form = parsed_data['a_recent']['w'] - parsed_data['a_recent']['l']
        signals['form_diff'] = h_form - a_form
        if h_form - a_form >= 4:
            signals['form_edge_home'] = 1
        elif a_form - h_form >= 4:
            signals['form_edge_away'] = 1
        
        # 伤停影响
        if parsed_data['injuries_h']:
            signals['injury_impact_h'] = 1
            for i in parsed_data['injuries_h']:
                if '主力' in i and ('前锋' in i or '中场' in i):
                    signals['injury_impact_h'] = 2
                    break
        
        # 恢复时间信息
        signals['injury_recovery_days_h'] = parsed_data.get('injury_recovery_days_h')
        signals['injury_recovery_days_a'] = parsed_data.get('injury_recovery_days_a')
        if parsed_data['injuries_a']:
            signals['injury_impact_a'] = 1
            for i in parsed_data['injuries_a']:
                if '主力' in i and ('前锋' in i or '中场' in i):
                    signals['injury_impact_a'] = 2
                    break
        
        # 阵容已知
        if parsed_data['formation_h'] or parsed_data['lineup_h']:
            signals['lineup_known'] = True
        
        return signals
    
    def get_v9_modifiers(self, enhanced_signals):
        """
        生成v9引擎可用的修正值
        
        返回: {'lambda_h_mod': 1.0, 'lambda_a_mod': 1.0, 'confidence_mod': 0, 'rule_override': None}
        """
        mod = {
            'lambda_h_mod': 1.0,
            'lambda_a_mod': 1.0,
            'confidence_mod': 0,
            'rule_override': None,
        }
        
        es = enhanced_signals
        
        # 伤重主队 → λ_h ↓
        if es['injury_impact_h'] == 2:
            # 短期伤停（恢复天数<14天）影响减半：λ×0.5 而非 λ×0.85
            if es.get('injury_recovery_days_h') is not None and es['injury_recovery_days_h'] < 14:
                mod['lambda_h_mod'] *= 0.5
            else:
                mod['lambda_h_mod'] *= 0.85
            mod['confidence_mod'] -= 1
        elif es['injury_impact_h'] == 1:
            mod['lambda_h_mod'] *= 0.93
        
        # 伤重客队 → λ_a ↓
        if es['injury_impact_a'] == 2:
            # 短期伤停（恢复天数<14天）影响减半：λ×0.5 而非 λ×0.85
            if es.get('injury_recovery_days_a') is not None and es['injury_recovery_days_a'] < 14:
                mod['lambda_a_mod'] *= 0.5
            else:
                mod['lambda_a_mod'] *= 0.85
            mod['confidence_mod'] -= 1
        elif es['injury_impact_a'] == 1:
            mod['lambda_a_mod'] *= 0.93
        
        # 状态碾压 → 大比分方向修正
        if es['form_diff'] >= 5:
            mod['lambda_h_mod'] *= 1.15
            mod['lambda_a_mod'] *= 0.85
        elif es['form_diff'] <= -5:
            mod['lambda_a_mod'] *= 1.15
            mod['lambda_h_mod'] *= 0.85
        
        # 实力差极大 + 阵容齐全 → 强队方向加强
        if es['strength_gap'] >= 20 and es['lineup_known']:
            mod['lambda_h_mod'] *= 1.10
        elif es['strength_gap'] <= -20 and es['lineup_known']:
            mod['lambda_a_mod'] *= 1.10
        
        return mod


# ==================== CLI ====================
def print_table(matches_by_date, date_filter=None):
    """打印赛程表"""
    print(f"\n📅 天天盈球matchId对照表（{date_filter or '全部'}）\n")
    for date, matches in sorted(matches_by_date.items()):
        if date_filter and date != date_filter:
            continue
        print(f"  {date}:")
        for mid, host, guest, rd in matches:
            print(f"    {mid}  {host} vs {guest}（第{rd}轮）")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="天天盈球基本面采集器")
    parser.add_argument("--match-id", type=int, help="天天盈球matchId")
    parser.add_argument("--date", type=str, help="日期筛选 YYYY-MM-DD")
    parser.add_argument("--list", action="store_true", help="列出所有已知matchId")
    parser.add_argument("--test-parse", type=str, help="测试文本解析（传入包含页面文本的文件路径）")
    
    args = parser.parse_args()
    scraper = TTYingqiuScraper()
    
    if args.list:
        print_table(WORLDCUP_MATCHES, args.date)
        sys.exit(0)
    
    if args.test_parse:
        with open(args.test_parse, 'r', encoding='utf-8') as f:
            text = f.read()
        parsed = scraper.parse_prose_data(text)
        signals = scraper.get_enhanced_signals(parsed)
        print(json.dumps({"parsed": parsed, "signals": signals}, ensure_ascii=False, indent=2))
        sys.exit(0)
    
    if args.match_id:
        print(f"matchId: {args.match_id}")
        print("使用方法: 在Hermes Agent中:")
        print(f"  1. browser_navigate('{scraper.BASE_URL}/{args.match_id}')")
        print(f"  2. browser_console(expression='document.body.innerText')")
        print(f"  3. 传给 scraper.parse_prose_data(text)")
        print(f"  4. scraper.get_enhanced_signals(parsed)")
        print(f"  5. scraper.get_v9_modifiers(signals)")
    else:
        print("用法: python3 ttyingqiu-scraper.py --list  # 列出赛程")
