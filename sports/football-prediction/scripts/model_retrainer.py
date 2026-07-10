#!/usr/bin/env python3
"""
模型自学习闭环 v1.0 (2026-06-21)
建立预测误差反馈与模型修正的自动化闭环。
每周自动运行，读取过去一个月的预测-赛果对，分析误差与特征的关系，输出修正建议。

用法:
  # 分析预测误差并输出修正建议
  python3 model_retrainer.py --data-dir ~/.hermes/predictions/ --days-back 30

  # 查看当前模型参数统计
  python3 model_retrainer.py --stats

功能:
  1. 加载过去 N 天的所有结构化预测记录
  2. 对每场计算预测误差（λ偏差、比分偏差）
  3. 按特征分组统计误差模式
  4. 输出修正建议（P0自动/P1人工）

结构化预测记录格式 (JSON):
  ~/.hermes/predictions/records/{match_id}.json

修正建议分级:
  P0 自动执行: 系数微调(幅度<5%), 自动生效并记录
  P1 人工确认: 结构性规则变更, 生成报告等待确认
"""

import json, os, sys, math
from datetime import datetime, timedelta
from collections import defaultdict


# ============================================================
#  当前模型参数表 (供P0自动修正参考)
#  格式: {特征名: {条件描述: 当前值}}
# ============================================================
CURRENT_PARAMS = {
    'temperature': {
        'high_temp_mod': 0.90,       # 高温(≥30°C) λ修正系数
        'low_temp_mod': 1.05,        # 低温(≤15°C) λ修正系数
    },
    'neutral': {
        'neutral_mod': 0.95,         # 中立场地 λ修正系数
    },
    'injury': {
        'injury_heavy_mod': 0.85,    # 伤停影响≥2 λ修正系数
        'injury_light_mod': 0.93,    # 伤停影响=1 λ修正系数
    },
    'form': {
        'form_big_diff_mod': 1.15,   # 状态差≥5 λ修正系数(有利方)
        'form_big_diff_penalty': 0.85,  # 状态差≥5 λ修正系数(不利方)
    },
    'strength': {
        'strength_gap_mod': 1.10,    # 实力差≥20+已知首发 λ修正系数
    },
    'rating': {
        'rating_diff_mod': 1.10,     # 评分差≥0.5 λ修正系数
    },
    'round2': {
        'round2_mod': 1.05,          # R2+轮次 λ修正系数(双方)
    },
}


def load_prediction_records(data_dir, days_back=30):
    """
    加载过去 N 天的所有结构化预测记录。
    搜索 data_dir/records/ 下的所有 .json 文件，按日期过滤。

    返回: list[dict] 每条记录包含match_id, date, features, prediction, actual
    """
    records_dir = os.path.join(os.path.expanduser(data_dir), 'records')
    if not os.path.isdir(records_dir):
        print(f"⚠️ 记录目录不存在: {records_dir}")
        return []

    cutoff = datetime.now() - timedelta(days=days_back)
    records = []

    for fname in sorted(os.listdir(records_dir)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(records_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                rec = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 读取文件失败 {fname}: {e}")
            continue

        # 只加载有 actual 赛果的记录
        if 'actual' not in rec or not rec['actual']:
            continue

        # 日期过滤
        rec_date = rec.get('date', '')
        if rec_date:
            try:
                dt = datetime.strptime(rec_date, '%Y-%m-%d')
                if dt < cutoff:
                    continue
            except ValueError:
                pass  # 日期格式不对则保留

        records.append(rec)

    return records


def compute_errors(records):
    """
    对每条记录计算预测误差，添加 error 字段。

    误差指标:
      - lambda_dev_h: λ_h 偏差 (实际进球 - 预测λ_h)
      - lambda_dev_a: λ_a 偏差 (实际进球 - 预测λ_a)
      - total_goal_dev: 总进球偏差
      - direction_correct: 方向是否正确 (胜/平/负)
      - score_exact: 比分是否精确命中

    每场加 error 字段
    """
    results = []
    for rec in records:
        pred = rec.get('prediction', {})
        actual = rec.get('actual', {})

        goals_h = actual.get('goals_h', 0)
        goals_a = actual.get('goals_a', 0)
        lambda_h = pred.get('lambda_h', 0)
        lambda_a = pred.get('lambda_a', 0)

        # λ偏差
        lambda_dev_h = goals_h - lambda_h
        lambda_dev_a = goals_a - lambda_a

        # 总进球偏差
        pred_total = lambda_h + lambda_a
        actual_total = goals_h + goals_a
        total_goal_dev = actual_total - pred_total

        # 方向判断
        pred_scores = pred.get('scores', [])
        actual_score = actual.get('score', '')
        direction_correct = False
        if pred_scores:
            # 预测方向: 取第一个比分判断
            try:
                p_h, p_a = map(int, pred_scores[0].split('-'))
                act_h, act_a = map(int, actual_score.split('-'))
                p_dir = '胜' if p_h > p_a else ('平' if p_h == p_a else '负')
                a_dir = '胜' if act_h > act_a else ('平' if act_h == act_a else '负')
                direction_correct = (p_dir == a_dir)
            except (ValueError, IndexError):
                direction_correct = None

        score_exact = (actual_score in pred_scores)

        # 构建误差记录
        error = {
            'lambda_dev_h': round(lambda_dev_h, 2),
            'lambda_dev_a': round(lambda_dev_a, 2),
            'total_goal_dev': round(total_goal_dev, 2),
            'direction_correct': direction_correct,
            'score_exact': score_exact,
            'match_id': rec.get('match_id', ''),
            'date': rec.get('date', ''),
        }

        rec['error'] = error
        results.append(rec)

    return results


def analyze_by_feature(records_with_errors, feature):
    """
    按某特征的不同取值对误差进行分组统计。

    Args:
        records_with_errors: compute_errors 后的记录列表
        feature: 特征名, 如 'temperature', 'injury_impact_h', 'strength_gap' 等

    返回:
        {
            'feature': feature,
            'groups': [
                {
                    'label': '高温(>=30)',
                    'condition': 'temperature >= 30',
                    'count': N,
                    'avg_lambda_dev_h': ...,
                    'avg_lambda_dev_a': ...,
                    'avg_total_dev': ...,
                    'direction_accuracy': ...,
                    'score_exact_rate': ...,
                },
                ...
            ]
        }
    """
    groups_def = _get_feature_groups(feature)
    if not groups_def:
        return {'feature': feature, 'groups': []}

    groups_data = defaultdict(list)

    for rec in records_with_errors:
        feat_val = rec.get('features', {}).get(feature, None)
        error = rec.get('error', {})

        if feat_val is None and feature not in rec.get('features', {}):
            # 尝试从features外的字段获取
            feat_val = rec.get(feature, None)

        # 分组
        group_label = _classify_value(feature, feat_val, groups_def)
        if group_label:
            groups_data[group_label].append(error)

    groups = []
    for label, err_list in groups_data.items():
        if not err_list:
            continue

        n = len(err_list)
        avg_lambda_h = sum(e.get('lambda_dev_h', 0) for e in err_list) / n
        avg_lambda_a = sum(e.get('lambda_dev_a', 0) for e in err_list) / n
        avg_total = sum(e.get('total_goal_dev', 0) for e in err_list) / n

        dir_corrects = [e for e in err_list if e.get('direction_correct') is not None]
        dir_acc = sum(1 for e in dir_corrects if e['direction_correct']) / len(dir_corrects) if dir_corrects else 0

        exacts = sum(1 for e in err_list if e.get('score_exact'))
        exact_rate = exacts / n if n > 0 else 0

        cond = _get_group_condition(feature, label, groups_def)

        groups.append({
            'label': label,
            'condition': cond,
            'count': n,
            'avg_lambda_dev_h': round(avg_lambda_h, 3),
            'avg_lambda_dev_a': round(avg_lambda_a, 3),
            'avg_total_dev': round(avg_total, 3),
            'direction_accuracy': round(dir_acc, 3),
            'score_exact_rate': round(exact_rate, 3),
        })

    return {'feature': feature, 'groups': groups}


def _get_feature_groups(feature):
    """返回某特征的预定义分组规则"""
    GROUPS_MAP = {
        'temperature': [
            {'label': '高温(>=30)', 'test': lambda v: v is not None and v >= 30},
            {'label': '适中(16-29)', 'test': lambda v: v is not None and 16 <= v <= 29},
            {'label': '低温(<=15)', 'test': lambda v: v is not None and v <= 15},
            {'label': '未知', 'test': lambda v: v is None or v == 0},
        ],
        'weather': [
            {'label': '晴/多云', 'test': lambda v: v is not None and any(k in str(v) for k in ['晴', '云', '晴']) if isinstance(v, str) else False},
            {'label': '阴/雨', 'test': lambda v: v is not None and any(k in str(v) for k in ['阴', '雨', '雪']) if isinstance(v, str) else False},
            {'label': '未知', 'test': lambda v: v is None or v == 0 or v == ''},
        ],
        'injury_impact_h': [
            {'label': '伤停严重(>=2)', 'test': lambda v: v is not None and v >= 2},
            {'label': '伤停轻微(=1)', 'test': lambda v: v is not None and v == 1},
            {'label': '无伤停(=0)', 'test': lambda v: v is not None and v == 0},
        ],
        'injury_impact_a': [
            {'label': '伤停严重(>=2)', 'test': lambda v: v is not None and v >= 2},
            {'label': '伤停轻微(=1)', 'test': lambda v: v is not None and v == 1},
            {'label': '无伤停(=0)', 'test': lambda v: v is not None and v == 0},
        ],
        'strength_gap': [
            {'label': '主队大幅优势(>=20)', 'test': lambda v: v is not None and v >= 20},
            {'label': '主队小幅优势(5~19)', 'test': lambda v: v is not None and 5 <= v < 20},
            {'label': '接近(-4~4)', 'test': lambda v: v is not None and -4 <= v <= 4},
            {'label': '客队小幅优势(-19~-5)', 'test': lambda v: v is not None and -19 <= v <= -5},
            {'label': '客队大幅优势(<=-20)', 'test': lambda v: v is not None and v <= -20},
        ],
        'market_consistency': [
            {'label': '高度一致(>=0.8)', 'test': lambda v: v is not None and v >= 0.8},
            {'label': '中度一致(0.5~0.79)', 'test': lambda v: v is not None and 0.5 <= v < 0.8},
            {'label': '分歧(<0.5)', 'test': lambda v: v is not None and v < 0.5},
        ],
        'motivation_gap': [
            {'label': '主队战意强(>=3)', 'test': lambda v: v is not None and v >= 3},
            {'label': '客队战意强(<=-3)', 'test': lambda v: v is not None and v <= -3},
            {'label': '均衡(-2~2)', 'test': lambda v: v is not None and -2 <= v <= 2},
        ],
        'handicap_diff': [
            {'label': '深盘主让(>=0.75)', 'test': lambda v: v is not None and v >= 0.75},
            {'label': '浅盘主让(0.25~0.5)', 'test': lambda v: v is not None and 0.25 <= v < 0.75},
            {'label': '平手盘(-0.25~0.25)', 'test': lambda v: v is not None and -0.25 <= v < 0.25},
            {'label': '浅盘客让(-0.5~-0.25)', 'test': lambda v: v is not None and -0.75 < v <= -0.25},
            {'label': '深盘客让(<=-0.75)', 'test': lambda v: v is not None and v <= -0.75},
        ],
        'half_life_form_h': [
            {'label': '状态好(>=0.7)', 'test': lambda v: v is not None and v >= 0.7},
            {'label': '状态中(0.4~0.69)', 'test': lambda v: v is not None and 0.4 <= v < 0.7},
            {'label': '状态差(<0.4)', 'test': lambda v: v is not None and v < 0.4},
        ],
        'half_life_form_a': [
            {'label': '状态好(>=0.7)', 'test': lambda v: v is not None and v >= 0.7},
            {'label': '状态中(0.4~0.69)', 'test': lambda v: v is not None and 0.4 <= v < 0.7},
            {'label': '状态差(<0.4)', 'test': lambda v: v is not None and v < 0.4},
        ],
    }
    return GROUPS_MAP.get(feature, [])


def _classify_value(feature, value, groups_def):
    """对某一特征值进行分类"""
    for g in groups_def:
        if g['test'](value):
            return g['label']
    return None


def _get_group_condition(feature, label, groups_def):
    """获取分组条件的文字描述"""
    for g in groups_def:
        if g['label'] == label:
            # 从test函数中提取大致条件描述
            return label  # 用label本身作为condition
    return label


def generate_suggestions(error_analysis_list):
    """
    根据多特征误差分析结果生成修正建议。

    Args:
        error_analysis_list: list of analyze_by_feature 返回的结果

    返回: list[dict]
        {
            'level': 'P0' | 'P1',       # P0=自动, P1=人工
            'component': str,            # 如 'temperature', 'injury'
            'old_value': float|str,
            'new_value': float|str,
            'reason': str,
            'evidence': dict,            # 支持数据
        }
    """
    suggestions = []

    for analysis in error_analysis_list:
        feature = analysis['feature']
        groups = analysis['groups']

        if not groups:
            continue

        # 提取有系统性偏差的分组
        for g in groups:
            if g['count'] < 3:
                continue  # 样本太少不可信

            avg_dev = g['avg_total_dev']
            abs_avg_dev = abs(avg_dev)

            # 只有偏差大于阈值才建议修正
            if abs_avg_dev < 0.15:
                continue

            # 根据特征和偏差方向生成建议
            sug = _build_suggestion(feature, g, avg_dev)
            if sug:
                suggestions.append(sug)

    # 按照 P0 在前、P1 在后排序
    suggestions.sort(key=lambda s: (1 if s['level'] == 'P1' else 0, s['component']))

    return suggestions


def _build_suggestion(feature, group_stats, avg_dev):
    """根据特征和分组统计生成单条建议"""

    # ===== 温度修正 =====
    if feature == 'temperature':
        if '高温' in group_stats['label'] and avg_dev < 0:
            # 高温下总进球持续偏低 → 系数从0.90再下调
            current = CURRENT_PARAMS.get('temperature', {}).get('high_temp_mod', 0.90)
            adjustment = abs(avg_dev) * 0.3  # 按偏差幅度30%调整
            new_val = round(current - adjustment, 2)
            if current - new_val <= 0.05:  # 幅度≤5% → P0
                return {
                    'level': 'P0',
                    'component': 'temperature',
                    'feature': 'temperature',
                    'condition': '高温(>30℃)',
                    'old_value': current,
                    'new_value': new_val,
                    'reason': f"高温场次总进球偏差{avg_dev:+.2f}, 建议λ修正从{current}→{new_val}",
                    'evidence': {'count': group_stats['count'], 'avg_total_dev': avg_dev},
                }
            else:
                return {
                    'level': 'P1',
                    'component': 'temperature',
                    'feature': 'temperature',
                    'condition': '高温(>30℃)',
                    'old_value': current,
                    'new_value': new_val,
                    'reason': f"高温场次偏差较大({avg_dev:+.2f}), λ修正从{current}→{new_val} (幅度>5%,需人工确认)",
                    'evidence': {'count': group_stats['count'], 'avg_total_dev': avg_dev},
                }
        if '低温' in group_stats['label'] and avg_dev > 0:
            current = CURRENT_PARAMS.get('temperature', {}).get('low_temp_mod', 1.05)
            adjustment = abs(avg_dev) * 0.3
            new_val = round(current - adjustment, 2)
            if abs(current - new_val) <= 0.05:
                return {
                    'level': 'P0', 'component': 'temperature', 'feature': 'temperature',
                    'condition': '低温(<=15℃)',
                    'old_value': current, 'new_value': new_val,
                    'reason': f"低温场次总进球偏差{avg_dev:+.2f}, 建议λ修正从{current}→{new_val}",
                    'evidence': {'count': group_stats['count'], 'avg_total_dev': avg_dev},
                }

    # ===== 伤停修正 =====
    if feature in ('injury_impact_h', 'injury_impact_a'):
        side = '主' if feature == 'injury_impact_h' else '客'
        if '伤停严重' in group_stats['label']:
            current = CURRENT_PARAMS.get('injury', {}).get('injury_heavy_mod', 0.85)
            # 如果预测偏高（实际进球<预期），应加大伤停惩罚
            dev_key = 'avg_lambda_dev_h' if feature == 'injury_impact_h' else 'avg_lambda_dev_a'
            dev_val = group_stats.get(dev_key, 0)
            if dev_val < 0:
                new_val = round(current + abs(dev_val) * 0.2, 2)
                if abs(current - new_val) <= 0.05:
                    return {
                        'level': 'P0', 'component': 'injury', 'feature': feature,
                        'condition': f'{side}队伤停≥2',
                        'old_value': current, 'new_value': new_val,
                        'reason': f"{side}队伤停严重时λ偏差{dev_val:+.2f}, 建议惩罚系数{current}→{new_val}",
                        'evidence': {'count': group_stats['count'], f'{dev_key}': dev_val},
                    }

    # ===== 状态修正 =====
    if feature == 'form_diff':
        pass  # 状态差修正由特征的复合条件决定, 暂不自动修改

    # ===== 盘口/方向准确率偏差 =====
    if group_stats.get('direction_accuracy', 0) < 0.50 and group_stats['count'] >= 5:
        if group_stats['direction_accuracy'] < 0.40:
            return {
                'level': 'P1',
                'component': f'direction_{feature}',
                'feature': feature,
                'condition': group_stats['label'],
                'old_value': f"{group_stats['direction_accuracy']*100:.0f}%",
                'new_value': '需人工分析',
                'reason': f"{group_stats['label']}方向准确率仅{group_stats['direction_accuracy']*100:.0f}% ({group_stats['count']}场), 低于50%阈值, 建议审查该分支规则",
                'evidence': {'count': group_stats['count'], 'direction_accuracy': group_stats['direction_accuracy']},
            }

    return None


def print_report(suggestions, scope_info=None):
    """
    输出格式化报告。
    建议分为 P1(人工确认) 和 P0(自动已执行) 两部分。
    """
    today = datetime.now().strftime('%Y-%m-%d')

    lines = []
    lines.append(f"=== 模型自学习报告 {today} ===")
    lines.append("")

    # 范围信息
    if scope_info:
        lines.append(f"📊 分析范围: {scope_info.get('days_back', '?')}天, {scope_info.get('total_matches', 0)}场比赛")
        lines.append("")

    # 分类
    p0_sugs = [s for s in suggestions if s['level'] == 'P0']
    p1_sugs = [s for s in suggestions if s['level'] == 'P1']

    if p1_sugs:
        lines.append("P1 建议(人工确认):")
        for sug in p1_sugs:
            ev = sug.get('evidence', {})
            lines.append(f"  [{sug['component']}] {sug['condition']}的{sug.get('feature', '?')}修正{sug['old_value']}→{sug['new_value']}:")
            lines.append(f"    触发{ev.get('count', '?')}场, {sug['reason']}")
        lines.append("")

    if p0_sugs:
        lines.append("P0 自动已执行:")
        for sug in p0_sugs:
            lines.append(f"  [{sug['component']}] {sug['condition']}的{sug.get('feature', '?')}修正从{sug['old_value']}→{sug['new_value']}: 已更新")
        lines.append("")

    if not suggestions:
        lines.append("✅ 无修正建议: 当前模型偏差在可接受范围内")
        lines.append("")

    # 附加统计摘要
    total_p0 = len(p0_sugs)
    total_p1 = len(p1_sugs)
    lines.append(f"--- 摘要: P0={total_p0}条自动 | P1={total_p1}条人工确认 ---")
    lines.append("")

    print("\n".join(lines))


def print_stats():
    """打印当前模型参数统计"""
    print("=== 当前模型参数统计 ===")
    print()
    for component, params in CURRENT_PARAMS.items():
        print(f"[{component}]")
        for k, v in params.items():
            print(f"  {k}: {v}")
        print()
    print(f"总组件数: {len(CURRENT_PARAMS)}")
    print(f"总参数数: {sum(len(v) for v in CURRENT_PARAMS.values())}")


# ==================== CLI ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="模型自学习闭环 — 预测误差反馈与自动修正")
    parser.add_argument("--data-dir", type=str, default="~/.hermes/predictions/",
                        help="预测数据目录 (默认: ~/.hermes/predictions/)")
    parser.add_argument("--days-back", type=int, default=30,
                        help="分析最近N天的预测记录 (默认: 30)")
    parser.add_argument("--stats", action="store_true",
                        help="查看当前模型参数统计")

    args = parser.parse_args()

    if args.stats:
        print_stats()
        sys.exit(0)

    # --- 主流程 ---
    data_dir = os.path.expanduser(args.data_dir)
    days_back = args.days_back

    print(f"🔍 加载预测记录 (过去{days_back}天)...")
    records = load_prediction_records(data_dir, days_back=days_back)
    print(f"   找到 {len(records)} 条有赛果的记录")

    if not records:
        print("⚠️ 无可用记录, 结束分析")
        sys.exit(0)

    print(f"📐 计算预测误差...")
    records_with_errors = compute_errors(records)

    # 检查误差统计
    lambda_devs_h = [r['error']['lambda_dev_h'] for r in records_with_errors]
    lambda_devs_a = [r['error']['lambda_dev_a'] for r in records_with_errors]
    dir_correct = [r['error']['direction_correct'] for r in records_with_errors if r['error']['direction_correct'] is not None]
    exact_scores = [r['error']['score_exact'] for r in records_with_errors]

    print(f"   λ_h 平均偏差: {sum(lambda_devs_h)/len(lambda_devs_h):+.3f}")
    print(f"   λ_a 平均偏差: {sum(lambda_devs_a)/len(lambda_devs_a):+.3f}")
    print(f"   方向准确率: {sum(dir_correct)/len(dir_correct)*100:.1f}%" if dir_correct else "   方向准确率: N/A")
    print(f"   精确命中率: {sum(exact_scores)/len(exact_scores)*100:.1f}%" if exact_scores else "   精确命中率: N/A")
    print()

    # 按特征分组分析
    features_to_analyze = [
        'temperature', 'weather', 'injury_impact_h', 'injury_impact_a',
        'strength_gap', 'market_consistency', 'motivation_gap',
        'handicap_diff', 'half_life_form_h', 'half_life_form_a',
    ]

    print(f"🔬 按特征分组分析 ({len(features_to_analyze)}个特征)...")
    all_analyses = []
    for feat in features_to_analyze:
        analysis = analyze_by_feature(records_with_errors, feat)
        groups = analysis.get('groups', [])
        if groups:
            all_analyses.append(analysis)
            for g in groups:
                if g['count'] >= 3:
                    print(f"   [{feat}] {g['label']}: {g['count']}场, "
                          f"λ偏差({g['avg_lambda_dev_h']:+.2f}/{g['avg_lambda_dev_a']:+.2f}), "
                          f"方向{g['direction_accuracy']*100:.0f}%")
    print()

    print("💡 生成修正建议...")
    suggestions = generate_suggestions(all_analyses)
    print(f"   共 {len(suggestions)} 条建议 (P0={sum(1 for s in suggestions if s['level']=='P0')}, "
          f"P1={sum(1 for s in suggestions if s['level']=='P1')})")
    print()

    # 输出报告
    scope_info = {'days_back': days_back, 'total_matches': len(records)}
    print_report(suggestions, scope_info=scope_info)

    # 如果存在 actual 缺失的记录，提示
    total_with_actual = len(records)
    total_all = sum(1 for f in os.listdir(os.path.join(data_dir, 'records'))
                    if f.endswith('.json')) if os.path.isdir(os.path.join(data_dir, 'records')) else 0
    if total_all > total_with_actual:
        print(f"📝 提示: 还有 {total_all - total_with_actual} 条待赛果录入的记录")
