#!/usr/bin/env python3
"""
北单预测记录追踪器（bjdc_prediction_tracker.py）v1.0
仿照 football-prediction 的 PredictionTracker，建北单专用 DB。

建表: bjdc_predictions + bjdc_daily_summary
字段: 让球方向/Edge/信号/双模结果/赛后判定/命中

用法:
  from bjdc_prediction_tracker import BjdcTracker
  tracker = BjdcTracker()
  tracker.add_prediction({...})
  tracker.update_result(match_num='5401', actual_direction='让胜')
  stats = tracker.get_statistics(days=7)
"""

import sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

DB_DIR = Path.home() / ".hermes" / "skills" / "sports" / "db"
DB_PATH = DB_DIR / "bjdc_predictions.db"


class BjdcTracker:
    """北单预测记录器"""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bjdc_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_num TEXT,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                league TEXT,
                handicap TEXT,               -- 让球数（如"-1"）
                pred_direction TEXT,          -- 让胜/让平/让负
                pred_confidence INTEGER,      -- 信心星级 1-5
                model1_direction TEXT,        -- 八维预测法结果
                model2_direction TEXT,        -- 实力盘定位法结果
                edge REAL,                    -- Edge 值
                signal_flags TEXT,            -- 信号列表（JSON）
                actual_direction TEXT,        -- 赛后实际方向
                hit_status INTEGER DEFAULT -1,-- -1待更新 / 0未中 / 1方向命中 / 2高赔命中
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bjdc_daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                total INTEGER DEFAULT 0,
                direction_hits INTEGER DEFAULT 0,
                edge_hits INTEGER DEFAULT 0,
                avg_edge REAL DEFAULT 0,
                dual_agree INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')

        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bjdc_date ON bjdc_predictions(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bjdc_league ON bjdc_predictions(league)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bjdc_hit ON bjdc_predictions(hit_status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bjdc_daily_date ON bjdc_daily_summary(date)')

        conn.commit()
        conn.close()

    def add_prediction(self, data: Dict) -> int:
        """记录一条预测"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO bjdc_predictions
                (match_num, date, home_team, away_team, league,
                 handicap, pred_direction, pred_confidence,
                 model1_direction, model2_direction,
                 edge, signal_flags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('match_num', ''),
            data.get('date', datetime.now().strftime('%Y-%m-%d')),
            data.get('home_team', ''),
            data.get('away_team', ''),
            data.get('league', ''),
            data.get('handicap', ''),
            data.get('pred_direction', ''),
            data.get('pred_confidence', 0),
            data.get('model1_direction', ''),
            data.get('model2_direction', ''),
            data.get('edge', 0.0),
            json.dumps(data.get('signal_flags', []), ensure_ascii=False),
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def update_result(self, match_num: str,
                      actual_direction: str,
                      pred_direction: str = None) -> bool:
        """赛后更新实际结果和命中判定"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if pred_direction:
            hit = 1 if pred_direction == actual_direction else 0
            cursor.execute('''
                UPDATE bjdc_predictions
                SET actual_direction=?, hit_status=?
                WHERE match_num=? AND hit_status=-1
            ''', (actual_direction, hit, match_num))
        else:
            cursor.execute('''
                UPDATE bjdc_predictions
                SET actual_direction=?
                WHERE match_num=? AND hit_status=-1
            ''', (actual_direction, match_num))

        updated = cursor.rowcount
        conn.commit()
        conn.close()
        return updated > 0

    def get_statistics(self, days: int = 7) -> Dict:
        """获取近期统计"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN hit_status=1 THEN 1 ELSE 0 END) as hits,
                AVG(edge) as avg_edge,
                SUM(CASE WHEN model1_direction=model2_direction THEN 1 ELSE 0 END) as dual_agree
            FROM bjdc_predictions
            WHERE date >= ? AND hit_status != -1
        ''', (since,))

        row = cursor.fetchone()
        conn.close()

        return {
            'total': row[0] or 0,
            'hits': row[1] or 0,
            'hit_rate': round((row[1] or 0) / max(row[0] or 1, 1) * 100, 1),
            'avg_edge': round(row[2] or 0, 3),
            'dual_agree': row[3] or 0,
        }

    def get_pending_reviews(self, days: int = 3) -> List[Dict]:
        """获取待复盘（hit_status=-1）的预测"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute('''
            SELECT match_num, date, home_team, away_team, league,
                   handicap, pred_direction, edge, signal_flags
            FROM bjdc_predictions
            WHERE date >= ? AND hit_status=-1
            ORDER BY date DESC
        ''', (since,))

        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'match_num': r[0], 'date': r[1],
                'home_team': r[2], 'away_team': r[3],
                'league': r[4], 'handicap': r[5],
                'pred_direction': r[6], 'edge': r[7],
                'signal_flags': json.loads(r[8]) if r[8] else [],
            }
            for r in rows
        ]

    def export_gt_candidates(self, min_confidence: int = 4) -> List[Dict]:
        """导出高信心+命中的预测，供 skill-evolver GT 扩展"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            SELECT match_num, date, home_team, away_team, league,
                   handicap, pred_direction, actual_direction, edge
            FROM bjdc_predictions
            WHERE hit_status=1 AND pred_confidence >= ?
            ORDER BY date DESC
        ''', (min_confidence,))

        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'match_num': r[0], 'date': r[1],
                'home_team': r[2], 'away_team': r[3],
                'league': r[4], 'handicap': r[5],
                'pred_direction': r[6], 'actual_direction': r[7],
                'edge': r[8],
            }
            for r in rows
        ]
