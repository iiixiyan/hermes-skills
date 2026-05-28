# -*- coding: utf-8 -*-
"""
竞彩预测记录追踪器 + 凯利公式配比
===================================
集成自虾评「足彩盈利系统」的核心功能：
1. SQLite持久化存储每场预测记录
2. 赛后更新实际结果，自动计算命中率
3. 按联赛/信心等级/推荐类型分组统计
4. 凯利公式计算建议投注配比
5. 导出CSV/生成回测报告

使用方法：
    from prediction_tracker import get_tracker, kelly_analysis
    
    tracker = get_tracker()
    
    # 记录预测（预测时调用）
    tracker.add_prediction({
        'match_num': '5001',
        'home_team': '町田泽维', 'away_team': '浦和红钻',
        'league': '日职联', 'date': '2026-05-22',
        'prediction_1': '1-1',  # 正常比分1
        'prediction_2': '2-1',  # 正常比分2
        'prediction_3': '0-0',  # 异常比分1
        'prediction_4': '1-2',  # 异常比分2
        'confidence': 3,  # 1-5星
        'lambda_1': 1.23, 'lambda_2': 1.58,
        'home_odds': 2.20, 'draw_odds': 3.00, 'away_odds': 2.93,
        'home_win_prob': 0.41,  # 市场概率
    })
    
    # 赛后更新结果
    tracker.update_result(match_num='5001', actual_score='1-1', home_goals=1, away_goals=1)
    
    # 查看统计
    stats = tracker.get_statistics(days=7)
    print(stats['hit_rate'], stats['roi'])
    
    # 凯利计算
    kelly = kelly_analysis(poisson_home=0.45, poisson_draw=0.28, poisson_away=0.27,
                          odds_home=2.20, odds_draw=3.00, odds_away=2.93,
                          bankroll=10000)
"""

import sqlite3
import csv
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
import math


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'predictions.db')


# ============================================================
# 凯利公式
# ============================================================

def kelly_fraction(our_prob: float, market_prob: float, fraction: int = 2) -> float:
    """
    凯利配比公式（半凯利）
    
    配比 = (我们的概率 - 市场隐含概率) ÷ 调整系数
    
    参数:
        our_prob: 我们计算的胜率（或方向概率）
        market_prob: 市场隐含概率（1/赔率）
        fraction: 调整系数 (默认2=半凯利，更保守)
    
    返回:
        float: 建议配比比例 (0-1)，0表示无价值投注
    """
    edge = our_prob - market_prob
    if edge <= 0:
        return 0.0
    kelly = edge / fraction
    return max(0.0, min(kelly, 0.25))  # 上限25%防止激进


def kelly_analysis(poisson_home: float, poisson_draw: float, poisson_away: float,
                   odds_home: float, odds_draw: float, odds_away: float,
                   bankroll: float = 10000, fraction: int = 2) -> Dict:
    """
    完整的凯利公式分析
    
    参数:
        poisson_*: 我们的胜平负概率（来自λ计算或其他模型）
        odds_*: 对应赔率（百家平均即赔）
        bankroll: 资金池总额（默认1万）
        fraction: 凯利调整系数
    
    返回:
        dict: 每个选项的凯利分析
    """
    # 市场隐含概率（归一化）
    total_implied = 1/odds_home + 1/odds_draw + 1/odds_away
    market_home = (1/odds_home) / total_implied
    market_draw = (1/odds_draw) / total_implied
    market_away = (1/odds_away) / total_implied
    
    result = {}
    for label, our_p, market_p, odds in [
        ('home', poisson_home, market_home, odds_home),
        ('draw', poisson_draw, market_draw, odds_draw),
        ('away', poisson_away, market_away, odds_away)
    ]:
        edge = our_p - market_p
        kelly = kelly_fraction(our_p, market_p, fraction)
        result[label] = {
            'our_prob': round(our_p, 4),
            'market_prob': round(market_p, 4),
            'edge': round(edge, 4),
            'odds': odds,
            'kelly_fraction': round(kelly, 4),
            'bet_amount': round(bankroll * kelly, 2),
            'recommendation': '推荐' if kelly > 0.01 else '不推荐'
        }
    
    result['bankroll'] = bankroll
    rec_amounts = [v['bet_amount'] for v in result.values() if isinstance(v, dict) and v.get('kelly_fraction', 0) > 0.01]
    result['recommended_total'] = sum(rec_amounts)
    return result


def league_ev_threshold(league: str) -> float:
    """
    联赛差异化EV阈值（集成自足彩盈利系统）
    不同联赛的庄家定价精度不同，需要不同的EV门槛
    """
    thresholds = {
        '英超': 0.25,
        '法甲': 0.22,
        '葡超': 0.22,
        '比甲': 0.22,
        '荷甲': 0.22,
        'K联赛': 0.22,
        'J联赛': 0.22,
        '日职联': 0.22,
        '日职': 0.22,
        '韩职': 0.22,
        '芬超': 0.20,
        '瑞超': 0.20,
        '瑞典超': 0.20,
        '挪超': 0.20,
        '德甲': 0.20,
        '西甲': 0.20,
        '意甲': 0.20,
        '德乙': 0.18,
        '法乙': 0.18,
        '荷乙': 0.18,
        '法国杯': 0.18,
        '德国杯': 0.18,
    }
    return thresholds.get(league, 0.20)


# ============================================================
# 预测记录器
# ============================================================

class PredictionTracker:
    """竞彩预测记录追踪器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 预测记录表（适配双轨比分格式）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_num TEXT,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                league TEXT,
                -- 正常比分
                pred_normal_1 TEXT,
                pred_normal_2 TEXT,
                -- 异常比分
                pred_abnormal_1 TEXT,
                pred_abnormal_2 TEXT,
                -- 信心
                confidence INTEGER,
                -- λ值
                lambda_1 REAL,
                lambda_2 REAL,
                -- 赔率
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                home_win_prob REAL,
                -- 赛后结果
                actual_score TEXT,
                home_goals INTEGER,
                away_goals INTEGER,
                -- 命中判定（-1=待更新, 0=未中, 1=方向命中, 2=精确比分命中, 3=异常比分命中）
                hit_status INTEGER DEFAULT -1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')

        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_date ON predictions(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_league ON predictions(league)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_hit ON predictions(hit_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_created ON predictions(created_at)')

        # 每日汇总表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                total INTEGER DEFAULT 0,
                exact_hits INTEGER DEFAULT 0,
                direction_hits INTEGER DEFAULT 0,
                abnormal_hits INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_summary(date)')
        conn.commit()
        conn.close()
    
    def add_prediction(self, data: Dict) -> int:
        """
        添加预测记录
        
        参数:
            data: {
                'match_num', 'home_team', 'away_team', 'league', 'date',
                'prediction_1', 'prediction_2',  # 正常比分
                'prediction_3', 'prediction_4',  # 异常比分
                'confidence': 1-5,
                'lambda_1', 'lambda_2',
                'home_odds', 'draw_odds', 'away_odds',
                'home_win_prob': 市场主胜概率 (可选)
            }
        
        返回:
            int: 记录ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (
                match_num, date, home_team, away_team, league,
                pred_normal_1, pred_normal_2,
                pred_abnormal_1, pred_abnormal_2,
                confidence, lambda_1, lambda_2,
                home_odds, draw_odds, away_odds,
                home_win_prob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('match_num'), data.get('date'), data.get('home_team'),
            data.get('away_team'), data.get('league'),
            data.get('prediction_1'), data.get('prediction_2'),
            data.get('prediction_3'), data.get('prediction_4'),
            data.get('confidence', 3),
            data.get('lambda_1'), data.get('lambda_2'),
            data.get('home_odds'), data.get('draw_odds'), data.get('away_odds'),
            data.get('home_win_prob')
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id
    
    def update_result(self, match_num: str, actual_score: str,
                      home_goals: int, away_goals: int) -> Dict:
        """
        赛后更新实际结果，自动判定命中
        
        命中规则:
        - 精确比分命中（2）：实际比分与任一预测比分完全一致
        - 方向命中（1）：胜负方向正确但比分不精确
        - 异常比分命中（3）：异常比分区域命中精确比分或方向
        
        参数:
            match_num: 场次号（如5001）
            actual_score: 实际比分（如"1-1"）
            home_goals: 主队进球数
            away_goals: 客队进球数
        
        返回:
            dict: 命中判定详情
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM predictions WHERE match_num = ? AND hit_status = -1 ORDER BY id DESC LIMIT 1', (match_num,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {'error': f'未找到待更新的预测记录: {match_num}'}
        
        # 解析预测比分
        normal_scores = [row['pred_normal_1'], row['pred_normal_2']]
        abnormal_scores = [row['pred_abnormal_1'], row['pred_abnormal_2']]
        all_scores = normal_scores + abnormal_scores
        
        # 判定命中
        hit_status = 0  # 默认未中
        abnormal_hit = 0
        
        # 判定实际胜负
        if home_goals > away_goals:
            actual_result = '胜'
        elif home_goals == away_goals:
            actual_result = '平'
        else:
            actual_result = '负'
        
        # 检查精确比分命中
        if actual_score in normal_scores:
            hit_status = 2  # 正常精确命中
        elif actual_score in abnormal_scores:
            hit_status = 3  # 异常精确命中
            abnormal_hit = 1
        else:
            # 检查方向命中（胜平负方向）
            for pred_score in all_scores:
                try:
                    parts = pred_score.split('-')
                    if len(parts) == 2:
                        ph, pa = int(parts[0]), int(parts[1])
                        if ph > pa and actual_result == '胜':
                            hit_status = 1
                            break
                        elif ph == pa and actual_result == '平':
                            hit_status = 1
                            break
                        elif ph < pa and actual_result == '负':
                            hit_status = 1
                            break
                except:
                    continue
        
        # 检查异常比分方向命中
        if hit_status in [0, 1]:
            for pred_score in abnormal_scores:
                try:
                    parts = pred_score.split('-')
                    if len(parts) == 2:
                        ph, pa = int(parts[0]), int(parts[1])
                        if ph > pa and actual_result == '胜':
                            abnormal_hit = 1
                            hit_status = 3  # 异常方向命中
                            break
                        elif ph == pa and actual_result == '平':
                            abnormal_hit = 1
                            hit_status = 3
                            break
                        elif ph < pa and actual_result == '负':
                            abnormal_hit = 1
                            hit_status = 3
                            break
                except:
                    continue
        
        # 更新数据库
        cursor.execute('''
            UPDATE predictions 
            SET actual_score = ?, home_goals = ?, away_goals = ?,
                hit_status = ?, abnormal_hit = ?
            WHERE id = ?
        ''', (actual_score, home_goals, away_goals, hit_status, abnormal_hit, row['id']))
        
        conn.commit()
        conn.close()
        
        # 更新每日汇总
        self._update_daily_summary(row['date'])
        
        status_map = {-1: '待更新', 0: '未命中', 1: '方向命中', 2: '精确比分命中', 3: '异常比分命中'}
        return {
            'match_num': match_num,
            'predicted': f"{row['pred_normal_1']}/{row['pred_normal_2']} (正常) + {row['pred_abnormal_1']}/{row['pred_abnormal_2']} (异常)",
            'actual': actual_score,
            'hit_status': hit_status,
            'hit_label': status_map.get(hit_status, '未知'),
            'abnormal_hit': bool(abnormal_hit)
        }
    
    def _update_daily_summary(self, date: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN hit_status >= 2 THEN 1 ELSE 0 END) as exact_hits,
                SUM(CASE WHEN hit_status >= 1 THEN 1 ELSE 0 END) as direction_hits,
                SUM(CASE WHEN abnormal_hit = 1 THEN 1 ELSE 0 END) as abnormal_hits,
                AVG(confidence) as avg_conf
            FROM predictions 
            WHERE date = ? AND hit_status != -1
        ''', (date,))
        
        row = cursor.fetchone()
        if row and row['total'] > 0:
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summary 
                (date, total, exact_hits, direction_hits, abnormal_hits, avg_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, row['total'], row['exact_hits'] or 0,
                  row['direction_hits'] or 0, row['abnormal_hits'] or 0,
                  row['avg_conf'] or 0))
            conn.commit()
        
        conn.close()
    
    def get_statistics(self, days: int = None, league: str = None,
                       min_confidence: int = None) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        where = ['hit_status != -1']
        params = []
        
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            where.append(f"date >= '{cutoff}'")
        if league:
            where.append("league = ?")
            params.append(league)
        if min_confidence:
            where.append("confidence >= ?")
            params.append(min_confidence)
        
        where_sql = ' WHERE ' + ' AND '.join(where) if where else ''
        
        # 基本统计
        cursor.execute(f'''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN hit_status >= 2 THEN 1 ELSE 0 END) as exact_hits,
                   SUM(CASE WHEN hit_status >= 1 THEN 1 ELSE 0 END) as direction_hits,
                   SUM(CASE WHEN hit_status >= 1 THEN 1.0 ELSE 0 END) / COUNT(*) as direction_rate,
                   SUM(CASE WHEN abnormal_hit = 1 THEN 1 ELSE 0 END) as abnormal_hits,
                   AVG(confidence) as avg_confidence
            FROM predictions {where_sql}
        ''', params)
        row = cursor.fetchone()
        
        stats = {
            'total': row['total'] or 0,
            'exact_hits': row['exact_hits'] or 0,
            'direction_hits': row['direction_hits'] or 0,
            'direction_rate': round(row['direction_rate'] or 0, 4),
            'abnormal_hits': row['abnormal_hits'] or 0,
            'avg_confidence': round(row['avg_confidence'] or 0, 1)
        }
        
        if stats['total'] > 0:
            stats['exact_rate'] = round(stats['exact_hits'] / stats['total'], 4)
        else:
            stats['exact_rate'] = 0.0
        
        # 按联赛统计
        cursor.execute(f'''
            SELECT league, COUNT(*) as total,
                   SUM(CASE WHEN hit_status >= 1 THEN 1 ELSE 0 END) as hits,
                   ROUND(AVG(CASE WHEN hit_status >= 1 THEN 1.0 ELSE 0 END), 4) as rate
            FROM predictions {where_sql}
            GROUP BY league ORDER BY total DESC
        ''', params)
        stats['by_league'] = {r['league']: {
            'total': r['total'], 'hits': r['hits'], 'rate': r['rate']
        } for r in cursor.fetchall()}
        
        # 按信心等级统计
        cursor.execute(f'''
            SELECT confidence, COUNT(*) as total,
                   SUM(CASE WHEN hit_status >= 1 THEN 1 ELSE 0 END) as hits,
                   ROUND(AVG(CASE WHEN hit_status >= 1 THEN 1.0 ELSE 0 END), 4) as rate
            FROM predictions {where_sql}
            GROUP BY confidence ORDER BY confidence DESC
        ''', params)
        stats['by_confidence'] = {f"{r['confidence']}星": {
            'total': r['total'], 'hits': r['hits'], 'rate': r['rate']
        } for r in cursor.fetchall()}
        
        conn.close()
        return stats
    
    def get_pending(self) -> List[Dict]:
        """获取待更新结果的预测"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, match_num, date, home_team, away_team, league,
                   pred_normal_1, pred_normal_2, pred_abnormal_1, pred_abnormal_2,
                   confidence
            FROM predictions WHERE hit_status = -1
            ORDER BY date DESC, match_num
        ''')
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    
    def get_daily_summary(self, days: int = 7) -> List[Dict]:
        """获取每日汇总"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT * FROM daily_summary WHERE date >= ? ORDER BY date DESC
        ''', (cutoff,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    
    def export_csv(self, filepath: str, days: int = None):
        """导出预测记录为CSV"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        where = 'WHERE hit_status != -1' if not days else 'WHERE date >= ? AND hit_status != -1'
        params = []
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            params.append(cutoff)
        
        cursor.execute(f'''
            SELECT match_num, date, home_team, away_team, league,
                   pred_normal_1, pred_normal_2, pred_abnormal_1, pred_abnormal_2,
                   confidence, hit_status, actual_score, lambda_1, lambda_2
            FROM predictions {where}
            ORDER BY date DESC, match_num
        ''', params)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['场次', '日期', '主队', '客队', '联赛',
                           '正常比分1', '正常比分2', '异常比分1', '异常比分2',
                           '信心', '命中状态', '实际比分', 'λ1', 'λ2'])
            for r in cursor.fetchall():
                status_map = {-1: '待更新', 0: '未命中', 1: '方向命中', 2: '精确比分命中', 3: '异常比分命中'}
                writer.writerow([r['match_num'], r['date'], r['home_team'], r['away_team'],
                               r['league'], r['pred_normal_1'], r['pred_normal_2'],
                               r['pred_abnormal_1'], r['pred_abnormal_2'],
                               r['confidence'], status_map.get(r['hit_status'], '未知'),
                               r['actual_score'], r['lambda_1'], r['lambda_2']])
        
        conn.close()
        return filepath
    
    def generate_report(self, days: int = 7) -> str:
        """生成文字版回测报告"""
        stats = self.get_statistics(days=days)
        daily = self.get_daily_summary(days=days)
        
        lines = []
        lines.append(f"📊 竞彩预测回测报告（近{days}天）")
        lines.append(f"{'='*40}")
        lines.append(f"总场次: {stats['total']}")
        lines.append(f"精确比分命中: {stats['exact_hits']} ({stats['exact_rate']*100:.1f}%)")
        lines.append(f"方向命中: {stats['direction_hits']} ({stats['direction_rate']*100:.1f}%)")
        lines.append(f"异常比分命中: {stats['abnormal_hits']}")
        lines.append(f"平均信心: {stats['avg_confidence']}星")
        lines.append("")
        
        lines.append("📈 按联赛统计:")
        for league, data in sorted(stats['by_league'].items(), key=lambda x: -x[1]['total']):
            lines.append(f"  {league}: {data['total']}场 {data['rate']*100:.0f}%方向命中率")
        
        lines.append("")
        lines.append("📈 按信心等级统计:")
        for conf, data in sorted(stats['by_confidence'].items(), key=lambda x: -x[1]['total']):
            lines.append(f"  {conf}: {data['total']}场 {data['rate']*100:.0f}%方向命中率")
        
        lines.append("")
        lines.append("📅 每日明细:")
        for d in daily:
            label = f"精确{d['exact_hits']}" if d['exact_hits'] > 0 else ""
            label += f" 异常{d['abnormal_hits']}" if d['abnormal_hits'] > 0 else ""
            lines.append(f"  {d['date']}: {d['total']}场 方向{d['direction_hits']} {label}")
        
        return "\n".join(lines)


def get_tracker(db_path: str = None) -> PredictionTracker:
    """获取追踪器实例"""
    return PredictionTracker(db_path)


if __name__ == '__main__':
    # 测试
    tracker = get_tracker()
    print(f"追踪器就绪: {tracker.db_path}")
    
    # 测试凯利
    kelly = kelly_analysis(
        poisson_home=0.41, poisson_draw=0.30, poisson_away=0.29,
        odds_home=2.20, odds_draw=3.00, odds_away=2.93,
        bankroll=10000
    )
    print(f"\n凯利分析:")
    for k, v in kelly.items():
        if isinstance(v, dict):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")
    
    print(f"\n联赛EV阈值示例:")
    for league in ['英超', '日职联', '芬超', '瑞典超', '德乙', '法国杯']:
        print(f"  {league}: {league_ev_threshold(league)}")
