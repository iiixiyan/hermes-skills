#!/usr/bin/env python3
"""
联赛配置加载器 — 渐进式读取

为每个联赛单独建立配置文件（references/leagues/），
预测时只加载所需联赛的配置，实现渐进式读取。

用法:
    from league_config import load_league, load_all_leagues
    
    # 渐进式: 只加载需要的联赛
    config = load_league('韩K联')
    print(config['lambda_baseline'], config['adjustments'])
    
    # 批量加载（一次性任务用）
    all_configs = load_all_leagues()
"""

import yaml
import re
import os
from typing import Optional

# 全局缓存: 已加载的联赛配置
_LEAGUE_CACHE = {}

# 配置目录
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
LEAGUES_DIR = os.path.join(SKILL_DIR, 'references', 'leagues')

# 联赛名 → 文件名映射
LEAGUE_FILE_MAP = {
    '韩K联': 'kl.md',
    'K1联赛': 'kl.md',
    'K联赛': 'kl.md',
    
    '挪超': 'norway.md',
    '挪威超': 'norway.md',
    'Eliteserien': 'norway.md',
    
    '瑞超': 'sweden.md',
    '瑞典超': 'sweden.md',
    'Allsvenskan': 'sweden.md',
    
    '芬超': 'finland.md',
    '芬兰超': 'finland.md',
    'Veikkausliiga': 'finland.md',
    
    '英超': 'england.md',
    'Premier League': 'england.md',
    '英格兰超级联赛': 'england.md',
    
    '西甲': 'spain.md',
    'La Liga': 'spain.md',
    '西班牙甲级联赛': 'spain.md',
    
    '意甲': 'italy.md',
    'Serie A': 'italy.md',
    '意大利甲级联赛': 'italy.md',
    
    '德甲': 'germany.md',
    'Bundesliga': 'germany.md',
    '德国甲级联赛': 'germany.md',
    
    '法甲': 'france.md',
    'Ligue 1': 'france.md',
    '法国甲级联赛': 'france.md',
    
    '日职联': 'japan.md',
    'J1联赛': 'japan.md',
    'J1 League': 'japan.md',
    
    '澳超': 'australia.md',
    'A-League': 'australia.md',
    
    '美职联': 'mls.md',
    'MLS': 'mls.md',
    '美职': 'mls.md',
    
    '世界杯': 'worldcup.md',
    'World Cup': 'worldcup.md',
    
    '欧冠': 'champions-league.md',
    'Champions League': 'champions-league.md',
    '欧洲冠军联赛': 'champions-league.md',
    
    '欧冠资格赛': 'champions-league.md',
    '欧冠预选赛': 'champions-league.md',
}


def _parse_yaml_frontmatter(content: str) -> Optional[dict]:
    """解析 markdown 文件的 YAML frontmatter"""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except Exception:
            return None
    return None


def _parse_rules_section(content: str) -> list:
    """从 markdown 内容中解析规则部分"""
    rules = []
    
    # 提取所有 ### 或 ## 级别的规则
    # 格式: ### FXX — 规则名 或 ### 规则名
    rule_pattern = re.findall(
        r'### (F\d+|F\d+[A-Z]?|F\d+[A-Z]?-\w+)\s*(?:—|-|–)?\s*(.*?)\n(.*?)(?=\n### |\n## |\Z)',
        content, re.DOTALL
    )
    
    for rule_id, rule_name, rule_body in rule_pattern:
        rule_body = rule_body.strip()
        # 提取触发条件和动作
        trigger_match = re.search(r'\*\*触发\*\*:\s*(.*?)(?:\n|$)', rule_body)
        action_match = re.search(r'\*\*动作\*\*:\s*(.*?)(?:\n|$)', rule_body)
        
        rules.append({
            'id': rule_id.strip(),
            'name': rule_name.strip(),
            'trigger': trigger_match.group(1).strip() if trigger_match else '',
            'action': action_match.group(1).strip() if action_match else '',
            'body': rule_body,
        })
    
    return rules


def _find_league_file(league_name: str) -> Optional[str]:
    """根据联赛名找到对应的配置文件路径"""
    # 精确匹配
    if league_name in LEAGUE_FILE_MAP:
        return os.path.join(LEAGUES_DIR, LEAGUE_FILE_MAP[league_name])
    
    # 模糊匹配
    for key, filename in LEAGUE_FILE_MAP.items():
        if key in league_name or league_name in key:
            return os.path.join(LEAGUES_DIR, filename)
    
    # 在文件名中查找
    for fname in os.listdir(LEAGUES_DIR):
        if fname.endswith('.md') and fname != 'generic.md':
            filepath = os.path.join(LEAGUES_DIR, fname)
            with open(filepath, 'r') as f:
                first_line = f.readline().strip()
                if league_name.lower() in first_line.lower():
                    return filepath
    
    return None


def load_league(league_name: str) -> Optional[dict]:
    """
    加载单个联赛的配置（渐进式）
    
    只加载指定联赛的配置文件，适合逐场预测时使用。
    已加载的配置会被缓存，避免重复读取。
    
    Args:
        league_name: 联赛名（如 '韩K联', '英超', 'World Cup'）
    
    Returns:
        dict: 包含联赛参数和规则的配置字典，找不到返回 generic 配置
    """
    # 缓存命中
    if league_name in _LEAGUE_CACHE:
        return _LEAGUE_CACHE[league_name]
    
    # 找文件
    filepath = _find_league_file(league_name)
    if not filepath or not os.path.exists(filepath):
        # 回退到 generic
        return load_generic()
    
    # 读取并解析
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter = _parse_yaml_frontmatter(content)
    if not frontmatter:
        return load_generic()
    
    rules = _parse_rules_section(content)
    
    config = {
        **frontmatter,
        'file': os.path.basename(filepath),
        'rules': rules,
    }
    
    _LEAGUE_CACHE[league_name] = config
    return config


def load_generic() -> dict:
    """加载通用联赛兜底配置"""
    if 'generic' in _LEAGUE_CACHE:
        return _LEAGUE_CACHE['generic']
    
    filepath = os.path.join(LEAGUES_DIR, 'generic.md')
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        frontmatter = _parse_yaml_frontmatter(content) or {}
        rules = _parse_rules_section(content)
        config = {**frontmatter, 'file': 'generic.md', 'rules': rules}
    else:
        config = {
            'name': '通用联赛',
            'name_en': 'Generic League',
            'avg_goals': 2.50,
            'lambda_baseline': 1.35,
            'prior_weight': 5,
            'dc_rho': -0.07,
            'home_advantage': 1.10,
            'file': 'generic.md',
            'rules': [],
        }
    
    _LEAGUE_CACHE['generic'] = config
    return config


def load_all_leagues() -> dict:
    """批量加载所有联赛配置（批量任务用）"""
    configs = {}
    if not os.path.exists(LEAGUES_DIR):
        return configs
    
    for fname in sorted(os.listdir(LEAGUES_DIR)):
        if not fname.endswith('.md'):
            continue
        filepath = os.path.join(LEAGUES_DIR, fname)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = _parse_yaml_frontmatter(content) or {}
        league_name = frontmatter.get('name', fname.replace('.md', ''))
        
        config = {
            **frontmatter,
            'file': fname,
            'rules': _parse_rules_section(content),
        }
        configs[league_name] = config
        _LEAGUE_CACHE[league_name] = config
    
    return configs


def get_adjustments(league_name: str) -> dict:
    """获取联赛系数修正"""
    config = load_league(league_name)
    if not config:
        return {}
    
    adjustments = {}
    frontmatter = config
    
    # 从frontmatter提取基础参数
    for key in ['lambda_coefficient', 'home_advantage', 'dc_rho']:
        if key in frontmatter:
            adjustments[key] = frontmatter[key]
    
    # 从规则中提取动作
    for rule in config.get('rules', []):
        action = rule.get('action', '')
        if 'λ' in action or 'lambda' in action.lower():
            adjustments[rule['id']] = rule['action']
    
    return adjustments


def get_4b_weight(league_name: str) -> str:
    """获取联赛的4b权重等级"""
    config = load_league(league_name)
    if not config:
        return 'P0'
    
    # 从规则中查找4b权重
    for rule in config.get('rules', []):
        if '4b' in rule['id'].lower() or '4b' in rule['name'].lower():
            weight_match = re.search(r'P[0-3]', rule.get('body', ''))
            if weight_match:
                return weight_match.group(0)
    
    # 从frontmatter中查找
    return config.get('factor4b_weight', 'P0')


def apply_league_adjustments(lambda_h: float, lambda_a: float, 
                              league: str, sina_data: dict = None) -> tuple:
    """
    应用联赛专属λ系数修正
    
    Args:
        lambda_h: 主队λ
        lambda_a: 客队λ
        league: 联赛名
        sina_data: 数据字典（可选）
    
    Returns:
        (修正后λ_h, 修正后λ_a, [原因列表])
    """
    config = load_league(league)
    if not config:
        return lambda_h, lambda_a, []
    
    reasons = []
    
    # 应用lambda_coefficient
    coeff = config.get('adjustments', {}).get('lambda_coefficient', 1.0)
    # 也检查直接放在顶层的
    if 'lambda_coefficient' in config:
        coeff = config['lambda_coefficient']
    
    if coeff != 1.0:
        lambda_h *= coeff
        lambda_a *= coeff
        fn = os.path.basename(config.get('file', ''))
        reasons.append(f'{fn}:λ×{coeff:.2f}')
    
    # 客场系数
    away_coeff = config.get('adjustments', {}).get('away_coefficient', 1.0)
    if 'away_coefficient' in config:
        away_coeff = config['away_coefficient']
    
    if away_coeff != 1.0:
        lambda_a *= away_coeff
        reasons.append(f'客场×{away_coeff:.2f}')
    
    return lambda_h, lambda_a, reasons


# =============================================
# CLI 用法
# =============================================
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        league = sys.argv[1]
        config = load_league(league)
        if config:
            print(f"联赛: {config.get('name', league)}")
            print(f"  λ基线: {config.get('lambda_baseline', 'N/A')}")
            print(f"  DC τ: {config.get('dc_rho', 'N/A')}")
            print(f"  主场优势: {config.get('home_advantage', 'N/A')}")
            print(f"  4b权重: {get_4b_weight(league)}")
            print(f"  规则数: {len(config.get('rules', []))}")
            print(f"  文件: {config.get('file', 'N/A')}")
        else:
            print(f"未找到联赛配置: {league}")
    else:
        # 显示所有可用联赛
        configs = load_all_leagues()
        print(f"可用联赛配置 ({len(configs)}):")
        for name in sorted(configs.keys()):
            c = configs[name]
            print(f"  {name:12s} λ={c.get('lambda_baseline', '?'):<5} τ={c.get('dc_rho', '?'):<5} 文件={c.get('file', '?')}")
