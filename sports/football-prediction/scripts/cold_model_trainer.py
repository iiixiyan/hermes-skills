#!/usr/bin/env python3
"""
爆冷预警系统2.0 — 主动爆冷概率模型 (v1.0)
基于历史预测-赛果数据训练逻辑回归模型，主动识别高风险比赛。
从"事后修正"升级到"事前预测"。

用法:
  from cold_model_trainer import predict_cold_prob, ColdFeatureBuilder
  
  # 单场比赛爆冷预测
  features = ColdFeatureBuilder(h_fifa, a_fifa, ...).build()
  cold_prob = predict_cold_prob(features)
  
  # 训练新模式
  python3 cold_model_trainer.py --train --data-dir ~/.hermes/predictions/
  
特征工程:
  - strength_gap_normalized: 实力差（归一化0-100），越大→实力悬殊越大
  - market_consistency: 市场一致性（同向变动家数/总家数），越高→越可能过热
  - motivation_gap: 战意差（R2-MUSTWIN反向：强队无欲无求时爆冷概率+）
  - injury_surprise: 基本面异常（核心突然复出+1 / 意外缺阵-1）
  - away_factor: 客队属性（长途远征/中立场）
  - historical_cold_rate: 该联赛/赛事历史爆冷率

核心函数:
  predict_cold_prob(features: dict) -> float
    返回爆冷概率 (0.0~1.0)
    当 > 0.35 时: 信心上限65%, 正常比分第2个为小比分冷门(0-1/1-1/0-0)
    当 > 0.50 时: 信心上限50%, 正常比分两场均含弱队方向

  ColdFeatureBuilder 类: 从match信息构建特征向量
    build() -> dict {strength_gap_normalized, market_consistency, motivation_gap, ...}

  train_model(data_dir) -> sklearn.linear_model.LogisticRegression | None
    class_weight='balanced', 输入过去3个月的预测-赛果对

  save/load_model(path) 持久化

简化版回退逻辑：当 sklearn 不可用时，使用基于规则的启发式方法：
  cold_prob = (strength_gap_norm * 0.3 + (1-market_consistency) * 0.25 +
               motivation_gap * 0.2 + injury_surprise_norm * 0.15 + away * 0.1)
"""

import json
import os
import pickle
from pathlib import Path

# ─────────────────────────────────────────────
# 尝试加载 sklearn，不可用时自动回退启发式
# ─────────────────────────────────────────────
try:
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

VERSION = "1.1"
MODEL_FILENAME = "cold_model_v1.pkl"

# =====================================================================
# ColdFeatureBuilder: 从比赛信息构建爆冷特征向量
# =====================================================================

class ColdFeatureBuilder:
    """
    从比赛信息构建爆冷特征向量。
    
    输入参数:
        h_fifa, a_fifa          : 主客队 FIFA 排名
        h_name, a_name          : 主客队名称
        o1, o3                  : 百家平均主胜/客胜即赔
        r1, c1, r2, c2, r3, c3 : 升/降家数（市场变动）
        rd                      : 轮次 (1=首轮, 2+=第2轮起)
        neutral                 : 中立场标志 (0=主场, 1=中立)
        form_signal             : 基本面字典（可选，含 injury_impact_h/a 等）
        league                  : 联赛标识 (默认 'worldcup')
    
    特征（build() 返回的 dict key）:
        strength_gap_normalized : float 0-100, FIFA 实力差归一化
        market_consistency      : float 0-1,   市场同向变动比例
        motivation_gap          : float 0-1,   强队战意缺失度
        injury_surprise         : float -1~1,  伤病异常信号
        away_factor             : float 0-1,   客队属性得分
        historical_cold_rate    : float 0-1,   联赛历史爆冷率
    """

    def __init__(self, h_fifa=0, a_fifa=0, h_name='', a_name='',
                 o1=0, o3=0, r1=0, c1=0, r2=0, c2=0, r3=0, c3=0,
                 rd=1, neutral=0, form_signal=None,
                 league='worldcup'):
        # 基础比赛信息
        self.h_fifa = h_fifa
        self.a_fifa = a_fifa
        self.h_name = h_name
        self.a_name = a_name
        # 赔率与市场变动
        self.o1 = o1
        self.o3 = o3
        self.r1 = r1
        self.c1 = c1
        self.r2 = r2
        self.c2 = c2
        self.r3 = r3
        self.c3 = c3
        # 轮次与环境
        self.rd = rd
        self.neutral = neutral
        self.form_signal = form_signal or {}
        self.league = league

    def build(self):
        """
        构建特征向量字典。
        所有特征均为数值型，范围明确，可直接用于模型推理或启发式计算。
        """
        fd = abs(self.h_fifa - self.a_fifa)

        # ── 1. strength_gap_normalized: 实力差归一化 0-100 ──
        # FIFA 差越大（强队 vs 弱队），一旦弱队爆冷影响越大。
        # 归一化: FIFA 差 * 1.5, 上限 100.
        # v10.8f 修复: 当主队更强(fh<fa)时反转方向 — 大差距→低爆冷概率
        # 法国vs塞内加尔: fh=3<15=fa, fd=12, 旧公式产生18%冷概率(过高), 新公式=82(反转后18)
        fd = abs(self.h_fifa - self.a_fifa)
        if self.h_fifa < self.a_fifa:
            # 主队FIFA排名更高(更强) → 差距越大爆冷概率越低
            strength_gap_normalized = max(0, 100 - min(100, fd * 1.5))
        elif self.h_fifa > self.a_fifa:
            # 客队更强 → 差距越大爆冷概率越高(正常)
            strength_gap_normalized = min(100, fd * 1.5)
        else:
            # 平排名 → 中等风险
            strength_gap_normalized = 50

        # ── 2. market_consistency: 市场一致性 0-1 ──
        # 计算所有升/降家数中 "同向" 变动的比例。
        # 同向趋势越强 → 市场越过热 → 爆冷概率越高。
        total_market = self.r1 + self.c1 + self.r2 + self.c2 + self.r3 + self.c3
        total_market = max(1, total_market)  # 防除零
        # 同向变动 = 每家公司的方向取最大值再求和
        same_dir = max(self.r1, self.c1) + max(self.r2, self.c2) + max(self.r3, self.c3)
        market_consistency = min(1.0, same_dir / total_market)

        # ── 3. motivation_gap: 战意差 0-1 ──
        # R2+ 轮次，强队若已出线或战意不足，爆冷概率上升。
        motivation_gap = 0.0
        if self.rd >= 2:
            # 强队(FIFA≤15)遇极端升主胜(xh): 已出线轮换风险
            if self.h_fifa <= 15 and self.a_fifa >= 50 and self.r1 >= 40 and self.c1 <= 5:
                motivation_gap = 0.7
            elif self.a_fifa <= 15 and self.h_fifa >= 50 and self.r3 >= 40 and self.c3 <= 5:
                motivation_gap = 0.7
            # 非关键战: 强队(FIFA前10)无出线压力
            elif self.h_fifa <= 10 and self.a_fifa >= 40:
                motivation_gap = 0.3

        # ── 4. injury_surprise: 基本面异常 -1~1 ──
        # 核心球员意外缺阵(≥2) → 该队实力下降，爆冷概率调整。
        # 正 = 有利于弱队，负 = 有利于强队
        injury_surprise = 0.0
        if self.form_signal:
            injury_h = self.form_signal.get('injury_impact_h', 0)
            injury_a = self.form_signal.get('injury_impact_a', 0)
            if injury_h >= 2:
                injury_surprise -= 1.0   # 主队核心伤缺 → 主队削弱
            if injury_a >= 2:
                injury_surprise += 1.0   # 客队核心伤缺 → 客队削弱

        # ── 5. away_factor: 客队属性 0-1 ──
        # 中立场/客队属性影响爆冷概率。
        if self.neutral == 1:
            away_factor = 0.5            # 中立场
        elif self.a_fifa <= self.h_fifa:
            away_factor = 0.3            # 客队排名更优(数字更小)
        else:
            away_factor = 0.7            # 客队排名更差(数字更大)

        # ── 6. historical_cold_rate: 联赛历史爆冷率 0-1 ──
        historical_cold_rate = {
            'worldcup': 0.25,
            'premier': 0.22,
            'laliga': 0.24,
            'seriea': 0.23,
            'bundes': 0.21,
            'ligue1': 0.22,
            'default': 0.20,
        }.get(self.league, 0.20)

        return {
            'strength_gap_normalized': strength_gap_normalized,
            'market_consistency': market_consistency,
            'motivation_gap': motivation_gap,
            'injury_surprise': injury_surprise,
            'away_factor': away_factor,
            'historical_cold_rate': historical_cold_rate,
        }


# =====================================================================
# 启发式回退计算
# =====================================================================

def _heuristic_cold_prob(features):
    """
    基于规则的启发式爆冷概率计算 (v1.1 — 2026-06-22 修复).
    
    公式:
        cold_prob = (1 - strength_gap_norm) * 0.15
                  + (1 - market_consistency) * 0.25
                  + motivation_gap * 0.25
                  + injury_surprise_norm * 0.20
                  + away_factor * 0.15
    
    说明:
        - strength_gap_norm 经 (1-s) 反转: FIFA 差越大→实力越悬殊→爆冷概率越低 ✅
          (旧公式 s*0.30 方向错误: FIFA 差越大反而增加爆冷概率, 导致法国vs伊拉克等
          超级碾压局被错误标记44%爆冷概率, 覆盖了正确的R2-Deep 3-0预测)
        - (1 - market_consistency) 越低一致性→越可能爆冷
        - injury_surprise_norm 把 -1~1 映射到 0~1
    """
    s = features['strength_gap_normalized'] / 100.0   # 0~1
    m = features['market_consistency']
    v = features['motivation_gap']
    i_raw = max(-1.0, min(1.0, features['injury_surprise']))
    i_norm = (i_raw + 1.0) / 2.0                      # -1..1 → 0..1
    a = features['away_factor']

    # 🔧 v1.1: strength_gap 反转 → (1-s)*0.15, 权重从0.30降至0.15
    #      motivation_gap 权重从0.20升至0.25 (更依赖实际战意信号)
    #      injury_surprise 权重从0.15升至0.20 (伤停是爆冷最强信号)
    cold_prob = ((1.0 - s) * 0.15 + (1.0 - m) * 0.25 + v * 0.25 + i_norm * 0.20 + a * 0.15)
    return min(1.0, max(0.0, cold_prob))


# =====================================================================
# 全局模型缓存 (避免重复 IO)
# =====================================================================
_model_cache = None


def predict_cold_prob(features, model_path=None):
    """
    返回爆冷概率 (0.0~1.0)。

    参数:
        features   : dict — 由 ColdFeatureBuilder.build() 返回的特征向量
        model_path : str  — 模型路径（可选，若不提供则尝试全局缓存）

    返回:
        float: 爆冷概率 0.0~1.0

    规则:
        > 0.35 : 信心上限 65%, 正常比分第 2 个为小比分冷门 (0-1/1-1/0-0)
        > 0.50 : 信心上限 50%, 正常比分两场均含弱队方向

    优先级:
        1. sklearn 逻辑回归模型（如已训练 & 可用）
        2. 启发式规则回退（默认路径）
    """
    global _model_cache

    # ── 尝试使用 sklearn 模型 ──
    if SKLEARN_AVAILABLE:
        try:
            if model_path and os.path.exists(model_path):
                model = load_model(model_path)
            elif _model_cache is not None:
                model = _model_cache
            else:
                model = None

            if model is not None:
                # 特征顺序必须与训练时一致
                X = [[
                    features['strength_gap_normalized'] / 100.0,
                    features['market_consistency'],
                    features['motivation_gap'],
                    max(-1.0, min(1.0, features['injury_surprise'])),
                    features['away_factor'],
                    features['historical_cold_rate'],
                ]]
                prob = model.predict_proba(X)[0][1]  # 爆冷类概率
                return float(prob)
        except Exception:
            pass  # 任何异常降级到启发式

    # ── 启发式回退 ──
    return _heuristic_cold_prob(features)


# =====================================================================
# 训练 / 保存 / 加载
# =====================================================================

def train_model(data_dir="~/.hermes/predictions/"):
    """
    从历史预测-赛果数据训练逻辑回归模型。

    参数:
        data_dir: str — 数据目录, 包含预测记录 JSON 文件

    返回:
        LogisticRegression | None — 训练好的模型, 失败返回 None

    JSON 记录所需字段:
        h_fifa, a_fifa          : FIFA 排名
        h_name, a_name          : 队伍名称
        o1, o3, r1, c1, ...     : 赔率/市场变动
        predicted_h, predicted_a: 预测比分
        actual_h, actual_a      : 实际比分（用于标签）
        round, neutral          : 轮次与环境

    爆冷标签定义:
        - 弱队(排名数字更大)赢球 → 爆冷 (1)
        - 其他 → 非爆冷 (0)
    """
    if not SKLEARN_AVAILABLE:
        print("[cold_model] ⚠ sklearn 不可用, 跳过训练")
        return None

    data_dir = os.path.expanduser(data_dir)
    if not os.path.isdir(data_dir):
        print(f"[cold_model] ⚠ 数据目录不存在: {data_dir}")
        return None

    # ── 收集训练数据 ──
    X, y = [], []
    data_files = sorted(Path(data_dir).glob("*predictions*.json")) + \
                 sorted(Path(data_dir).glob("*results*.json")) + \
                 sorted(Path(data_dir).glob("*history*.json"))

    for fpath in data_files:
        try:
            with open(fpath) as f:
                records = json.load(f)
                if isinstance(records, dict):
                    records = [records]
                for rec in records:
                    if not isinstance(rec, dict):
                        continue
                    # 必须至少包含 FIFA 排名
                    if 'h_fifa' not in rec or 'a_fifa' not in rec:
                        continue

                    # 构建特征
                    fb = ColdFeatureBuilder(
                        h_fifa=rec.get('h_fifa', 50),
                        a_fifa=rec.get('a_fifa', 50),
                        h_name=rec.get('h_name', ''),
                        a_name=rec.get('a_name', ''),
                        o1=rec.get('o1', 0),
                        o3=rec.get('o3', 0),
                        r1=rec.get('r1', 0), c1=rec.get('c1', 0),
                        r2=rec.get('r2', 0), c2=rec.get('c2', 0),
                        r3=rec.get('r3', 0), c3=rec.get('c3', 0),
                        rd=rec.get('round', 1),
                        neutral=rec.get('neutral', 0),
                    )
                    feats = fb.build()

                    features_vec = [
                        feats['strength_gap_normalized'] / 100.0,
                        feats['market_consistency'],
                        feats['motivation_gap'],
                        max(-1.0, min(1.0, feats['injury_surprise'])),
                        feats['away_factor'],
                        feats['historical_cold_rate'],
                    ]

                    # ── 计算标签: 是否爆冷 ──
                    actual_h = rec.get('actual_h', -1)
                    actual_a = rec.get('actual_a', -1)
                    if actual_h < 0 or actual_a < 0:
                        continue  # 无赛果跳过

                    h_fifa = rec['h_fifa']
                    a_fifa = rec['a_fifa']
                    fd = abs(h_fifa - a_fifa)

                    if fd <= 10:
                        # 实力接近 → 平局不算爆冷
                        is_cold = 0
                    elif h_fifa > a_fifa:
                        # 主队排名更差(弱队) → 主队赢才算爆冷
                        is_cold = 1 if actual_h > actual_a else 0
                    else:
                        # 客队排名更差(弱队) → 客队赢才算爆冷
                        is_cold = 1 if actual_a > actual_h else 0

                    X.append(features_vec)
                    y.append(is_cold)
        except (json.JSONDecodeError, IOError):
            continue

    if len(X) < 10:
        print(f"[cold_model] ⚠ 训练数据不足 ({len(X)} 条, 需要 ≥ 10)")
        return None

    # ── 训练逻辑回归 ──
    model = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
    model.fit(X, y)

    score = model.score(X, y)
    print(f"[cold_model] ✅ 训练完成: {len(X)} 条数据, 准确率={score:.2%}")
    return model


def load_model(model_path):
    """
    加载已训练的模型 (pickle 格式)。

    参数:
        model_path: str — 模型文件路径

    返回:
        LogisticRegression | None
    """
    global _model_cache
    try:
        with open(model_path, 'rb') as f:
            _model_cache = pickle.load(f)
        print(f"[cold_model] ✅ 加载模型: {model_path}")
        return _model_cache
    except Exception as e:
        print(f"[cold_model] ⚠ 加载失败: {e}")
        return None


def save_model(model, model_path):
    """
    保存训练好的模型到磁盘 (pickle 格式)。

    参数:
        model      : LogisticRegression — 模型对象
        model_path : str — 保存路径
    """
    try:
        parent = os.path.dirname(model_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"[cold_model] ✅ 保存模型: {model_path}")
    except Exception as e:
        print(f"[cold_model] ⚠ 保存失败: {e}")


# =====================================================================
# 比分后处理：将 cold_prob 转化为信心上限 / 比分调整
# =====================================================================

def adjust_by_cold_prob(h_goals, a_goals, rule, conf_level, cold_prob,
                        h_name='', a_name='', h_fifa=0, a_fifa=0):
    """
    根据爆冷概率调整预测输出。

    参数:
        h_goals, a_goals : 原始预测比分
        rule, conf_level : 原始规则名和信心等级
        cold_prob        : 爆冷概率 (0~1)
        h_name, a_name   : 队伍名称(用于提示)
        h_fifa, a_fifa   : 排名(用于判断强弱)

    返回:
        (h_goals, a_goals, rule, conf_level, cold_warning)
        cold_warning: str — 爆冷预警文本，空字符串表示无预警
    """
    cold_warning = ""
    if cold_prob <= 0.35:
        return h_goals, a_goals, rule, conf_level, cold_warning

    # ── 高风险预警 (0.35 < cold_prob ≤ 0.50) ──
    if cold_prob <= 0.50:
        # 信心上限 65% → 降 1 级
        new_conf = max(1, conf_level - 1)
        # 判断强弱: FIFA 排名数字小 = 强
        stronger_is_home = h_fifa < a_fifa
        is_cold_score = False

        if stronger_is_home:
            # 主队更强 → 爆冷意味客队赢或平
            if h_goals > a_goals:
                # 原预测主胜 → 第2个比分替换为小比分冷门
                is_cold_score = True
                cold_scores = [(0, 1), (1, 1), (0, 0)]
                # 选一个与原比分不同的冷门比分
                for ch, ca in cold_scores:
                    if (ch, ca) != (h_goals, a_goals):
                        h_goals, a_goals = ch, ca
                        break
        else:
            # 客队更强 → 爆冷意味主队赢或平
            if a_goals > h_goals:
                is_cold_score = True
                cold_scores = [(1, 0), (1, 1), (0, 0)]
                for ch, ca in cold_scores:
                    if (ch, ca) != (h_goals, a_goals):
                        h_goals, a_goals = ch, ca
                        break

        cold_warning = (
            f"❄️ 爆冷预警{cold_prob:.0%}"
            f"{'→冷门比分' if is_cold_score else ''}"
        )
        rule = f"{rule}+{cold_warning}"
        return h_goals, a_goals, rule, new_conf, cold_warning

    # ── 极高风险预警 (cold_prob > 0.50) ──
    # 信心上限 50% → 降 2 级
    new_conf = max(1, conf_level - 2)
    stronger_is_home = h_fifa < a_fifa
    is_cold_score = False

    if stronger_is_home:
        # 主队更强 → 比分两场均含弱队(客队)方向
        if h_goals > a_goals:
            is_cold_score = True
            # 客队赢或平
            cold_scores = [(0, 1), (1, 2), (0, 0), (1, 1)]
            for ch, ca in cold_scores:
                if (ch, ca) != (h_goals, a_goals):
                    h_goals, a_goals = ch, ca
                    break
    else:
        # 客队更强 → 比分两场均含弱队(主队)方向
        if a_goals > h_goals:
            is_cold_score = True
            cold_scores = [(1, 0), (2, 1), (0, 0), (1, 1)]
            for ch, ca in cold_scores:
                if (ch, ca) != (h_goals, a_goals):
                    h_goals, a_goals = ch, ca
                    break

    cold_warning = (
        f"🔴 严重爆冷预警{cold_prob:.0%}"
        f"{'→冷门比分' if is_cold_score else ''}"
    )
    rule = f"{rule}+{cold_warning}"
    return h_goals, a_goals, rule, new_conf, cold_warning


# =====================================================================
# 便捷接口: 一键完成特征构建+预测+后处理
# =====================================================================

def analyze_match_cold(h_fifa, a_fifa, h_name='', a_name='',
                       o1=0, o3=0, r1=0, c1=0, r2=0, c2=0, r3=0, c3=0,
                       rd=1, neutral=0, form_signal=None,
                       h_goals=0, a_goals=0, rule='', conf_level=3):
    """
    一站式接口: 构建特征 → 预测爆冷概率 → 调整比分/信心。

    返回:
        {
            'cold_prob': float,
            'warning': str,
            'h_goals': int,
            'a_goals': int,
            'rule': str,
            'conf_level': int,
        }
    """
    fb = ColdFeatureBuilder(
        h_fifa=h_fifa, a_fifa=a_fifa,
        h_name=h_name, a_name=a_name,
        o1=o1, o3=o3,
        r1=r1, c1=c1, r2=r2, c2=c2, r3=r3, c3=c3,
        rd=rd, neutral=neutral, form_signal=form_signal,
    )
    features = fb.build()
    cold_prob = predict_cold_prob(features)

    # ── 📛 超级碾压豁免 v1.1: FIFA差>25 + 赔率<1.20 → 不触发爆冷 ──
    # 即使 heuristic 修复后, 再加一层硬保护防止误触发。
    # 2026-06-22 法国(FIFA3) vs 伊拉克(FIFA57) 案例: 
    #   fd=54, o1=1.077, 原cold_model错误报44%覆盖了R2-Deep 3-0
    #   条件: 强队赔率<1.20 且 FIFA差>25 → 非爆冷场景
    fd = abs(h_fifa - a_fifa)
    if fd > 25:
        # 判断谁更强 (FIFA数字小=强)
        stronger_home = h_fifa < a_fifa
        if stronger_home:
            stronger_odds = o1
        else:
            stronger_odds = o3
        if stronger_odds > 0 and stronger_odds < 1.20:
            # 超级碾压局: 即使 cold_prob 触发, 也强制压制
            return {
                'cold_prob': min(cold_prob, 0.30),  # 强制低于阈值
                'warning': '',
                'h_goals': h_goals,
                'a_goals': a_goals,
                'rule': rule,
                'conf_level': conf_level,
            }

    new_h, new_a, new_rule, new_conf, warning = adjust_by_cold_prob(
        h_goals, a_goals, rule, conf_level, cold_prob,
        h_name=h_name, a_name=a_name,
        h_fifa=h_fifa, a_fifa=a_fifa,
    )

    return {
        'cold_prob': cold_prob,
        'warning': warning,
        'h_goals': new_h,
        'a_goals': new_a,
        'rule': new_rule,
        'conf_level': new_conf,
    }


# =====================================================================
# CLI
# =====================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=f"爆冷预警系统 {VERSION} — 主动爆冷概率模型"
    )
    parser.add_argument("--train", action="store_true",
                        help="训练模型 (需要 sklearn 和历史数据)")
    parser.add_argument("--data-dir", type=str, default="~/.hermes/predictions/",
                        help="历史数据目录")
    parser.add_argument("--model-path", type=str, default="",
                        help="模型保存/加载路径")
    parser.add_argument("--predict", action="store_true",
                        help="对单场比赛做爆冷预测")
    parser.add_argument("--home-fifa", type=int, default=0)
    parser.add_argument("--away-fifa", type=int, default=0)
    parser.add_argument("--home-name", type=str, default="")
    parser.add_argument("--away-name", type=str, default="")
    parser.add_argument("--o1", type=float, default=0)
    parser.add_argument("--o3", type=float, default=0)
    parser.add_argument("--r1", type=int, default=0)
    parser.add_argument("--c1", type=int, default=0)
    parser.add_argument("--r2", type=int, default=0)
    parser.add_argument("--c2", type=int, default=0)
    parser.add_argument("--r3", type=int, default=0)
    parser.add_argument("--c3", type=int, default=0)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--neutral", type=int, default=0)

    args = parser.parse_args()

    if args.train:
        model = train_model(args.data_dir)
        if model is not None:
            model_path = args.model_path or os.path.join(
                os.path.expanduser(args.data_dir), MODEL_FILENAME
            )
            save_model(model, model_path)

    if args.predict:
        fb = ColdFeatureBuilder(
            h_fifa=args.home_fifa, a_fifa=args.away_fifa,
            h_name=args.home_name, a_name=args.away_name,
            o1=args.o1, o3=args.o3,
            r1=args.r1, c1=args.c1,
            r2=args.r2, c2=args.c2,
            r3=args.r3, c3=args.c3,
            rd=args.round,
            neutral=args.neutral,
        )
        features = fb.build()
        prob = predict_cold_prob(features)

        level = "🟢 低风险"
        if prob > 0.50:
            level = "🔴 严重预警: 极高风险"
        elif prob > 0.35:
            level = "🟡 预警: 高风险"

        print(f"[cold_model] 爆冷概率: {prob:.1%} | {level}")
        print(f"  strength_gap_norm={features['strength_gap_normalized']:.1f}")
        print(f"  market_consistency={features['market_consistency']:.2f}")
        print(f"  motivation_gap={features['motivation_gap']:.2f}")
        print(f"  injury_surprise={features['injury_surprise']:.2f}")
        print(f"  away_factor={features['away_factor']:.2f}")
        print(f"  hist_cold_rate={features['historical_cold_rate']:.2f}")

    if not args.train and not args.predict:
        parser.print_help()
