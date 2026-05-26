"""
多模型融合预测模块
Poisson (主模型) + XGBoost (辅助模型, 需≥20条真实赛果) + 因子修正层

基于微信文章「AI预测体育比赛」的方法论：
- 特征工程比算法选择更重要 ✓ (feature_extractor.py)
- 多模型融合提升稳定性 ✓ (本模块)
- 持续迭代校准 ✓ (与prediction_tracker联动)
"""

import os
import sys
import json
import sqlite3
from typing import Optional, Tuple
from dataclasses import dataclass

import numpy as np

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SKILL_DIR, "predictions.db")


@dataclass
class FusionPrediction:
    """融合后的预测结果"""
    home_goals: float      # 预期主队进球
    away_goals: float      # 预期客队进球
    poisson_home_goals: float  # Poisson原始预测
    poisson_away_goals: float
    xgb_home_prob: Optional[float] = None   # XGBoost主胜概率
    xgb_draw_prob: Optional[float] = None
    xgb_away_prob: Optional[float] = None
    xgb_enabled: bool = False
    fusion_method: str = "poisson_only"


class ModelFusion:
    """
    多模型融合器
    
    工作模式：
    - 数据不足(<20条真实赛果): Poisson only
    - 数据充足(≥20条): Poisson(60%) + XGBoost(40%) 加权融合
    """
    
    MIN_SAMPLES = 20  # XGBoost最小训练样本
    
    def __init__(self):
        self.xgb_model = None
        self.scaler = None
        self.feature_names = None
        self.trained = False
        self.training_samples = 0
    
    def get_training_data(self) -> Tuple[np.ndarray, np.ndarray, int]:
        """从DB读取有实际赛果的训练数据"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT home_goals, away_goals, lambda_1, lambda_2, 
                   home_odds, draw_odds, away_odds, confidence,
                   home_win_prob
            FROM predictions 
            WHERE actual_score IS NOT NULL AND actual_score != '' 
              AND home_goals IS NOT NULL
        """)
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return np.array([]), np.array([]), 0
        
        # Features: [lambda_1, lambda_2, home_odds, draw_odds, away_odds]
        X = np.array([[r[2] or 0, r[3] or 0, r[4] or 0, r[5] or 0, r[6] or 0] for r in rows])
        y_home = np.array([r[0] for r in rows])
        y_away = np.array([r[1] for r in rows])
        
        return X, np.column_stack([y_home, y_away]), len(rows)
    
    def train_if_ready(self) -> bool:
        """检查数据量并训练XGBoost"""
        X, y, n = self.get_training_data()
        self.training_samples = n
        
        if n < self.MIN_SAMPLES:
            self.trained = False
            return False
        
        try:
            from xgboost import XGBRegressor
            from sklearn.preprocessing import StandardScaler
            
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            self.xgb_model = XGBRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                objective='reg:squarederror',
                random_state=42
            )
            self.xgb_model.fit(X_scaled, y)
            self.trained = True
            return True
            
        except ImportError:
            return False
    
    def predict(self, lambda_1: float, lambda_2: float,
                home_odds: float = 0, draw_odds: float = 0, away_odds: float = 0) -> FusionPrediction:
        """
        融合预测
        
        Args:
            lambda_1: Poisson主队预期进球
            lambda_2: Poisson客队预期进球
            home_odds, draw_odds, away_odds: 百家平均即赔
        """
        pred = FusionPrediction(
            home_goals=lambda_1,
            away_goals=lambda_2,
            poisson_home_goals=lambda_1,
            poisson_away_goals=lambda_2
        )
        
        # 尝试XGBoost辅助
        if self.trained and self.xgb_model is not None and home_odds > 0:
            try:
                X = self.scaler.transform([[lambda_1, lambda_2, home_odds, draw_odds, away_odds]])
                xgb_goals = self.xgb_model.predict(X)[0]
                
                pred.xgb_enabled = True
                
                # 60% Poisson + 40% XGBoost 加权融合
                pred.home_goals = lambda_1 * 0.6 + xgb_goals[0] * 0.4
                pred.away_goals = lambda_2 * 0.6 + xgb_goals[1] * 0.4
                pred.fusion_method = "poisson_60_xgb_40"
                
                # 从XGB进球数推导胜平负概率 (简化: 用泊松分布)
                from scipy.stats import poisson
                max_goals = 6
                probs = np.zeros((3,))
                for h in range(max_goals + 1):
                    for a in range(max_goals + 1):
                        p = poisson.pmf(h, pred.home_goals) * poisson.pmf(a, pred.away_goals)
                        if h > a:
                            probs[0] += p
                        elif h == a:
                            probs[1] += p
                        else:
                            probs[2] += p
                total = probs.sum()
                if total > 0:
                    pred.xgb_home_prob = probs[0] / total
                    pred.xgb_draw_prob = probs[1] / total
                    pred.xgb_away_prob = probs[2] / total
                    
            except Exception:
                pass
        
        return pred
    
    def status(self) -> dict:
        """返回融合器状态"""
        return {
            'trained': self.trained,
            'training_samples': self.training_samples,
            'min_samples_needed': self.MIN_SAMPLES,
            'mode': 'poisson+xgboost' if self.trained else 'poisson_only',
            'ready_for_fusion': self.trained
        }


# 全局单例
_fusion_instance = None

def get_fusion() -> ModelFusion:
    global _fusion_instance
    if _fusion_instance is None:
        _fusion_instance = ModelFusion()
        _fusion_instance.train_if_ready()
    return _fusion_instance


def predict_with_fusion(lambda_1: float, lambda_2: float,
                        home_odds: float = 0, draw_odds: float = 0, away_odds: float = 0) -> FusionPrediction:
    """快捷预测接口"""
    fusion = get_fusion()
    return fusion.predict(lambda_1, lambda_2, home_odds, draw_odds, away_odds)
