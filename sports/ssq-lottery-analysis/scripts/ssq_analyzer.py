#!/usr/bin/env python3
"""
双色球(SSQ)分析器 — 5种经典数据过滤方法 + 回测引擎
"""
import json
import random
from collections import Counter, defaultdict
from datetime import datetime

class SSQAnalyzer:
    """双色球综合分析器"""

    RED_RANGE = list(range(1, 34))  # 1-33
    BLUE_RANGE = list(range(1, 17))  # 1-16
    ZONES = {'一区(01-11)': (1, 11), '二区(12-22)': (12, 22), '三区(23-33)': (23, 33)}

    # ═══ 恒值号系統 ═══
    # 16组号码和为34的配对（01+33=34, 02+32=34, ...）
    CONSTANT_PAIRS = [(1,33), (2,32), (3,31), (4,30), (5,29), (6,28),
                      (7,27), (8,26), (9,25), (10,24), (11,23), (12,22),
                      (13,21), (14,20), (15,19), (16,18)]
    # 快速查表：号码→其恒值号
    CONSTANT_MAP = {}
    for a, b in CONSTANT_PAIRS:
        CONSTANT_MAP[a] = b
        CONSTANT_MAP[b] = a

    def __init__(self, data_path='/tmp/ssq_data.json'):
        with open(data_path) as f:
            raw = json.load(f)
        # 按期号升序排列（最早的在前面）
        self.data = sorted(raw, key=lambda x: x['issue'])
        self.N = len(self.data)
        print(f"[SSQAnalyzer] 已加载 {self.N} 期数据 ({self.data[0]['date']} ~ {self.data[-1]['date']})")

    # ── 工具方法 ──────────────────────────────────────

    def _to_int(self, arr):
        """字符串转整数"""
        return [int(x) for x in arr]

    def _last_n(self, n):
        """获取最近N期数据"""
        return self.data[-n:] if n <= self.N else self.data

    def _red_freq(self, n):
        """最近N期红球频率统计"""
        last = self._last_n(n)
        counter = Counter()
        for record in last:
            for r in record['red']:
                counter[int(r)] += 1
        return counter

    # ── 方法1: 历史号码分布（基础热度） ──────────────

    def get_heat_map(self, period=100):
        """
        统计最近N期红球频率，标记热号/冷号
        返回: {sorted_by_freq: [...], hot: [...], cold: [...], freq: {...}}
        """
        freq = self._red_freq(period)
        sorted_nums = sorted(freq.items(), key=lambda x: -x[1])

        hot = [n for n, _ in sorted_nums[:10]]
        cold = [n for n, _ in sorted_nums[-10:]]

        print(f"\n{'='*50}")
        print(f"📊 方法1: 历史号码分布（近{period}期）")
        print(f"{'='*50}")
        print(f"  热号TOP10: {hot}")
        print(f"  冷号TOP10: {cold}")
        print(f"  频率分布: {dict(sorted_nums[:15])}...")

        return {
            'sorted_by_freq': sorted_nums,
            'hot': hot,
            'cold': cold,
            'freq': dict(freq)
        }

    # ── 方法2: 动态追踪冷热号（短期趋势） ────────────

    def track_trend(self, period=30):
        """
        分析短期活跃度
        - 活跃号: 近10期出现≥3次
        - 复苏号: 之前遗漏≥10期，近5期内出现过
        """
        last_n = self._last_n(period)
        recent_10 = last_n[-10:]
        recent_5 = last_n[-5:]
        earlier = last_n[:-5]

        # 近10期计数
        freq_10 = Counter()
        for r in recent_10:
            for n in r['red']:
                freq_10[int(n)] += 1

        # 活跃号: 近10期≥3次
        active = sorted([n for n, c in freq_10.items() if c >= 3])

        # 遗漏分析: 检查哪些号在earlier中遗漏≥10期，但在recent_5中出现
        earlier_set = set()
        for r in earlier:
            earlier_set.update(int(x) for x in r['red'])

        recent_5_set = set()
        for r in recent_5:
            recent_5_set.update(int(x) for x in r['red'])

        # 在earlier中出现的号码（说明不是长期冷号），检测遗漏后复苏
        # 复苏号: 之前遗漏≥10期（不在earlier中每期都出现），近5期出现
        # 简化: check哪些在recent_5出现但不在之前频繁出现
        revival = [n for n in recent_5_set if n not in [x[0] for x in Counter(
            int(x) for r in earlier for x in r['red']
        ).most_common(15)]]

        print(f"\n{'='*50}")
        print(f"📊 方法2: 动态追踪冷热号（近{period}期）")
        print(f"{'='*50}")
        print(f"  活跃号(近10期≥3次): {active}")
        print(f"  复苏号(遗漏后回暖): {revival}")

        return {'active': active, 'revival': revival}

    # ── 方法3: 遗漏值分析（回补概率） ────────────────

    def analyze_omission(self):
        """
        计算当前每个号码的遗漏值
        遗漏值 = 当前期号 - 上次出现期号
        """
        # 找出每个号码最后一次出现的索引
        last_seen = {}
        for i, record in enumerate(reversed(self.data)):
            for r in record['red']:
                n = int(r)
                if n not in last_seen:
                    last_seen[n] = i  # 距离最近一期多少期

        omissions = {}
        for n in self.RED_RANGE:
            omissions[n] = last_seen.get(n, self.N)

        sorted_om = sorted(omissions.items(), key=lambda x: -x[1])
        deep_cold = sorted_om[:5]          # 深冷号TOP5
        avg_omission = sum(omissions.values()) / len(omissions)
        warm = [n for n, v in omissions.items() if abs(v - avg_omission) < 5]

        print(f"\n{'='*50}")
        print(f"📊 方法3: 遗漏值分析")
        print(f"{'='*50}")
        print(f"  平均遗漏值: {avg_omission:.1f}期")
        print(f"  深冷号TOP5: {deep_cold}")
        print(f"  温号(均值附近): {warm[:10]}...")

        return {'omissions': omissions, 'deep_cold': deep_cold, 'warm': warm, 'avg_omission': avg_omission}

    # ── 方法4: 区间比分析 ─────────────────────────────

    def check_zone_ratio(self, last_n=10):
        """
        三区分布分析
        一区: 01-11, 二区: 12-22, 三区: 23-33
        """
        recent = self._last_n(last_n)
        zone_counts = defaultdict(list)

        for record in recent:
            zone = {'一区': 0, '二区': 0, '三区': 0}
            for r in record['red']:
                n = int(r)
                if 1 <= n <= 11:
                    zone['一区'] += 1
                elif 12 <= n <= 22:
                    zone['二区'] += 1
                else:
                    zone['三区'] += 1
            for z in zone:
                zone_counts[z].append(zone[z])

        avg_zones = {z: sum(v)/len(v) for z, v in zone_counts.items()}
        strong_zones = [z for z, avg in avg_zones.items() if avg > 2.3]

        print(f"\n{'='*50}")
        print(f"📊 方法4: 区间比分析（近{last_n}期）")
        print(f"{'='*50}")
        print(f"  各区平均出号: {avg_zones}")
        print(f"  强势区(>2.3): {strong_zones or '无'}")

        return {'avg_zones': dict(avg_zones), 'strong_zones': strong_zones, 'raw': dict(zone_counts)}

    # ── 方法5: 和值走势分析 ───────────────────────────

    def analyze_sum_value(self, last_n=10):
        """
        红球和值分析（参考范围70-130）
        """
        recent = self._last_n(last_n)
        sums = []
        for record in recent:
            s = sum(int(x) for x in record['red'])
            sums.append(s)

        avg_sum = sum(sums) / len(sums)
        last_sum = sums[-1]
        prev_sums = sums[:-1]

        if last_sum < 70:
            verdict = "偏小"
        elif last_sum > 130:
            verdict = "偏大"
        else:
            verdict = "正常"

        # 趋势判断
        trend = None
        if len(prev_sums) >= 3:
            recent_trend = prev_sums[-3:]
            if all(s < 90 for s in recent_trend):
                trend = "下期关注和值回升"
            elif all(s > 120 for s in recent_trend):
                trend = "下期关注和值回落"

        print(f"\n{'='*50}")
        print(f"📊 方法5: 和值走势分析（近{last_n}期）")
        print(f"{'='*50}")
        print(f"  平均和值: {avg_sum:.1f}")
        print(f"  最近一期和值: {last_sum} → {verdict}")
        print(f"  走势判断: {trend or '无明确趋势'}")
        print(f"  近{last_n}期和值序列: {sums}")

        return {'avg_sum': avg_sum, 'last_sum': last_sum, 'verdict': verdict,
                'trend': trend, 'series': sums}

    # ── 方法6: 恒值号分析（知乎融合） ───────────────────

    def analyze_constant_pairs(self, last_n=20):
        """
        恒值号分析 — 16组和为34的配对 (01-33, 02-32, ...)
        
        四大特征：
        1. 恒值号出现频繁，选号时注意对应恒值号
        2. 恒值号可重复到下一期但较难同时出现
        3. 05-29、11-23出现最多，下期大中小号俱全不應斷區
           07-27出现后，下期奖号都没有07和27
           12-22、06-28、13-21等极难同时出现在同一注
        4. 恒值号出现后，两号一热一冷
        """
        recent = self._last_n(last_n)
        
        # 检测恒值号在最近N期中的出现
        pair_appearances = defaultdict(int)  # 每组出现次数
        single_appearances = Counter()       # 单个号码出现次数
        
        for record in recent:
            reds = [int(x) for x in record['red']]
            for n in reds:
                single_appearances[n] += 1
                # 检查恒值号
                partner = self.CONSTANT_MAP.get(n)
                if partner and partner in reds:
                    pair = tuple(sorted([n, partner]))
                    pair_appearances[pair] += 1
        
        # 特征3: 哪些恒值号出现最多
        sorted_pairs = sorted(pair_appearances.items(), key=lambda x: -x[1])
        
        # 查找哪些恒值号从未在同一期出现
        never_together = []
        for a, b in self.CONSTANT_PAIRS:
            a_str, b_str = str(a).zfill(2), str(b).zfill(2)
            together = False
            for record in recent:
                reds = [int(x) for x in record['red']]
                if a in reds and b in reds:
                    together = True
                    break
            if not together:
                never_together.append((a, b))
        
        # 特征2: 上期出现恒值号后，下期的表现
        next_period_stats = defaultdict(lambda: {'同时出现': 0, '只出现一个': 0, '都没出现': 0})
        for i in range(len(recent) - 1):
            curr_reds = [int(x) for x in recent[i]['red']]
            next_reds = [int(x) for x in recent[i+1]['red']]
            
            # 检查本期是否有恒值号
            for a, b in self.CONSTANT_PAIRS:
                both = a in curr_reds and b in curr_reds
                if both:
                    a_in_next = a in next_reds
                    b_in_next = b in next_reds
                    if a_in_next and b_in_next:
                        next_period_stats[(a,b)]['同时出现'] += 1
                    elif a_in_next or b_in_next:
                        next_period_stats[(a,b)]['只出现一个'] += 1
                    else:
                        next_period_stats[(a,b)]['都没出现'] += 1
        
        # 最近一期的情况
        last_reds = [int(x) for x in recent[-1]['red']]
        last_pair = None
        last_partner_found = None
        for n in last_reds:
            partner = self.CONSTANT_MAP.get(n)
            if partner:
                if partner in last_reds:
                    last_pair = tuple(sorted([n, partner]))
                else:
                    last_partner_found = (n, partner)
        
        print(f"\n{'='*50}")
        print(f"📊 方法6: 恒值号分析（近{last_n}期）")
        print(f"{'='*50}")
        print(f"  恒值号定义: 16组和为34的配对")
        print(f"  配对数: {self.CONSTANT_PAIRS}")
        print(f"\n  🔹 本期恒值号状态:")
        if last_pair:
            print(f"    本期已出现恒值号对: {last_pair} ✅")
        elif last_partner_found:
            n, partner = last_partner_found
            print(f"    出现单边恒值号: {n} → 对应恒值号 {partner} 可关注")
        else:
            print(f"    本期无恒值号出现")
        
        print(f"\n  🔹 恒值号同期出现频率TOP5:")
        for pair, cnt in sorted_pairs[:5]:
            print(f"    {pair}: {cnt}次")
        
        print(f"\n  🔹 从未同期出现的恒值号:")
        for a, b in never_together[:8]:
            print(f"    ({a:02d},{b:02d}) — 极难同注")
        
        # 推荐
        suggestions = []
        if last_partner_found and not last_pair:
            n, partner = last_partner_found
            suggestions.append(partner)
            print(f"\n  💡 建议关注: 恒值号 {partner}（{n}的配对）")
        
        return {
            'constant_pairs': dict(self.CONSTANT_PAIRS),
            'pair_frequencies': dict(sorted_pairs),
            'never_together': never_together,
            'last_pair': last_pair,
            'last_partner': last_partner_found[1] if last_partner_found and not last_pair else None,
            'suggestions': suggestions
        }

    # ── 综合分析（单期预测） ───────────────────────────

    def analyze_single(self, issue):
        """对指定期号进行5方法综合分析"""
        # 找到该期号的索引
        idx = None
        for i, r in enumerate(self.data):
            if r['issue'] == issue:
                idx = i
                break
        if idx is None:
            return f"未找到期号 {issue}"

        # 用该期之前的数据做分析
        # 临时调整data范围用于分析
        orig_data = self.data
        self.data = self.data[:idx]  # 只用之前的数据

        print(f"\n{'#'*60}")
        print(f"  双色球 SSQ {issue} 期 综合分析")
        print(f"{'#'*60}")

        results = {}
        results['heat_map'] = self.get_heat_map(period=100)
        results['trend'] = self.track_trend(period=30)
        results['omission'] = self.analyze_omission()
        results['zone'] = self.check_zone_ratio(last_n=10)
        results['sum_value'] = self.analyze_sum_value(last_n=10)
        results['constant_pairs'] = self.analyze_constant_pairs(last_n=20)

        # 实际开奖号码
        actual_red = self._to_int(orig_data[idx]['red'])
        actual_blue = self._to_int(orig_data[idx]['blue'])
        print(f"\n{'='*50}")
        print(f"✅ 实际开奖: 红球={actual_red}  蓝球={actual_blue}")
        print(f"{'='*50}")

        # 恢复数据
        self.data = orig_data
        return results

    # ── 综合投票推荐 ──────────────────────────────────

    def get_recommendation(self, period=100):
        """
        5种方法综合投票选出推荐号码
        投票权重:
          heat_map(热点)  +1/票
          trend(活跃复苏) +2/票  
          omission(遗漏)  +1/票
          zone(分区)      -/控制分布
          sum_value(和值) -/控制大小
        """
        heat = self.get_heat_map(period)
        trend = self.track_trend(period=30)
        omission = self.analyze_omission()

        # 投票
        votes = Counter()
        for n in heat['hot'][:8]:
            votes[n] += 1
        for n in trend['active']:
            votes[n] += 2
        for n in trend['revival']:
            votes[n] += 2
        for n, _ in omission['deep_cold'][:3]:
            votes[n] += 1
        for n in omission['warm'][:8]:
            votes[n] += 1

        # 按票数排序
        candidates = sorted(votes.items(), key=lambda x: -x[1])

        if not getattr(self, '_silent', False):
            print(f"\n{'#'*60}")
            print(f"  综合投票推荐")
            print(f"{'#'*60}")
            print(f"  候选号码(按票数): {candidates[:15]}")

        # 选出6个红球（兼顾三区分布）
        sum_info = self.analyze_sum_value(last_n=10) if not getattr(self, '_silent', False) else {'avg_sum': 102}
        zone_info = self.check_zone_ratio(last_n=10) if not getattr(self, '_silent', False) else {}

        recommended = self._balanced_pick(candidates, sum_info, zone_info)
        # 恒值号过滤：如果推荐中包含同一恒值号对的两个号码，移除较低票数的那个
        cp_result = self.analyze_constant_pairs(last_n=20) if not getattr(self, '_silent', False) else {}
        if not getattr(self, '_silent', False):
            # 检查推荐中是否有恒值号对同时出现
            for a, b in self.CONSTANT_PAIRS:
                if a in recommended and b in recommended:
                    # 移除票数较低的
                    vote_a = votes.get(a, 0)
                    vote_b = votes.get(b, 0)
                    remove_n = b if vote_a >= vote_b else a
                    recommended.remove(remove_n)
                    # 从候选中补一个
                    for n, _ in candidates:
                        if n not in recommended:
                            recommended.append(n)
                            break
                    print(f"  🔄 恒值号过滤: 移除({a},{b})中的{remove_n}")
                    break
        
        blue_recommend = self._pick_blue()

        print(f"\n  🎯 推荐号码: 红球={recommended}  蓝球={blue_recommend}")
        return {'red': recommended, 'blue': blue_recommend, 'votes': dict(candidates[:20])}

    def _balanced_pick(self, candidates, sum_info, zone_info):
        """基于和值+区间平衡+冷号覆盖挑选6个红球"""
        picked = []
        zones_used = {'一区': 0, '二区': 0, '三区': 0}
        has_cold = False  # 确保至少选1个冷号

        for n, votes in candidates:
            n_int = n if isinstance(n, int) else int(n)
            if n_int in picked:
                continue

            # 分区计数
            if 1 <= n_int <= 11:
                z = '一区'
            elif 12 <= n_int <= 22:
                z = '二区'
            else:
                z = '三区'

            # 每区最多选3个
            if zones_used[z] >= 3:
                continue
            zones_used[z] += 1
            picked.append(n_int)
            
            # 标记冷号（投票数≤1的视为冷号）
            if votes <= 1:
                has_cold = True

            if len(picked) >= 6:
                break

        # 如果不够6个，补充票数高的
        if len(picked) < 6:
            for n_int in self.RED_RANGE:
                if n_int not in picked:
                    picked.append(n_int)
                    if len(picked) >= 6:
                        break
        
        # 冷号覆盖检查：如果没有冷号，替换一个热号为遗漏最大的冷号
        if not has_cold and len(picked) >= 6:
            omissions = {}
            for i, rec in enumerate(reversed(self.data)):
                for r in rec['red']:
                    n = int(r)
                    if n not in omissions:
                        omissions[n] = i
            cold_candidates = sorted(
                [(n, omissions.get(n, 999)) for n in self.RED_RANGE if n not in picked],
                key=lambda x: -x[1]
            )
            if cold_candidates:
                cold_n = cold_candidates[0][0]
                # 替换picked中票数最低的那个
                picked_votes = [(n, dict(candidates).get(n, 0)) for n in picked]
                picked_votes.sort(key=lambda x: x[1])
                picked.remove(picked_votes[0][0])
                picked.append(cold_n)
        
        # 和值调整
        current_sum = sum(picked)
        avg_sum = sum_info.get('avg_sum', 102)
        if current_sum < avg_sum - 15:
            # 和值偏低，换一个大号
            picked.sort()
            for i, n in enumerate(picked):
                if n < 20:
                    for bigger in range(23, 34):
                        if bigger not in picked:
                            picked[i] = bigger
                            break
                    if sum(picked) >= avg_sum - 15:
                        break
        elif current_sum > avg_sum + 15:
            # 和值偏高，换一个小号
            picked.sort(reverse=True)
            for i, n in enumerate(picked):
                if n > 20:
                    for smaller in range(1, 12):
                        if smaller not in picked:
                            picked[i] = smaller
                            break
                    if sum(picked) <= avg_sum + 15:
                        break

        return sorted(picked[:6])

    def _pick_blue(self):
        """蓝球推荐：冷号轮换策略（避免始终锁定同一号）"""
        import random
        last_seen = {}
        for i, record in enumerate(reversed(self.data)):
            for b in record['blue']:
                n = int(b)
                if n not in last_seen:
                    last_seen[n] = i
        omissions = {n: last_seen.get(n, self.N) for n in self.BLUE_RANGE}
        sorted_blue = sorted(omissions.items(), key=lambda x: -x[1])
        # 从TOP3冷号中随机选1个，而不是固定选最冷的
        # 避免"永远锁死同一号"的问题
        candidates = sorted_blue[:3]
        weights = [c[1] for c in candidates]  # 遗漏值越大权重越高
        total_w = sum(weights)
        if total_w > 0:
            weights = [w/total_w for w in weights]
            chosen = random.choices(candidates, weights=weights, k=1)[0]
        else:
            chosen = candidates[0]
        return chosen[0]

    # ── 回测引擎 ──────────────────────────────────────

    def backtest_individual_methods(self, periods=100):
        """
        回测每种方法的独立命中率
        对最近periods期，每期用之前300期数据预测，检查实际结果
        """
        if periods > self.N - 310:
            periods = self.N - 310

        test_data = self.data[-(periods + 300):]
        test_start = 300  # 前300期作为训练数据起点

        print(f"\n{'#'*60}")
        print(f"  方法独立回测 — 近{periods}期")
        print(f"{'#'*60}")

        results = {
            'heat_map': {'matches': [], 'hit_rate': 0},   # 热号TOP6命中数
            'active': {'matches': [], 'hit_rate': 0},       # 活跃号TOP6
            'omission_rev': {'matches': [], 'hit_rate': 0}, # 遗漏回补
            'zone_balance': {'matches': [], 'hit_rate': 0}, # 区间平衡
        }

        for i in range(test_start, len(test_data)):
            train = test_data[:i]
            self.data = train
            actual = self._to_int(test_data[i]['red'])

            # 方法1: 热号TOP6
            freq = self._red_freq(100)
            top6 = [n for n, _ in sorted(freq.items(), key=lambda x: -x[1])[:6]]
            hits = len(set(top6) & set(actual))
            results['heat_map']['matches'].append(hits)

            # 方法2: 活跃号TOP6
            last_30 = train[-30:]
            freq_10 = Counter()
            for r in last_30[-10:]:
                for n in r['red']:
                    freq_10[int(n)] += 1
            active6 = sorted(freq_10.items(), key=lambda x: -x[1])[:6]
            active6_nums = [n for n, _ in active6]
            hits2 = len(set(active6_nums) & set(actual))
            results['active']['matches'].append(hits2)

            # 方法3: 遗漏号回补 - 选遗漏最大但接近均值的6个
            last_seen = {}
            for j, rec in enumerate(reversed(train)):
                for r in rec['red']:
                    n = int(r)
                    if n not in last_seen:
                        last_seen[n] = j
            omissions = {n: last_seen.get(n, len(train)) for n in self.RED_RANGE}
            avg_om = sum(omissions.values()) / 33
            omission_candidates = sorted(omissions.items(), key=lambda x: -abs(x[1] - avg_om))
            cold6 = [n for n, _ in omission_candidates[:6]]
            hits3 = len(set(cold6) & set(actual))
            results['omission_rev']['matches'].append(hits3)

            # 方法4: 区间平衡
            recent_zones = []
            for r in train[-10:]:
                z = {'一区': 0, '二区': 0, '三区': 0}
                for n in r['red']:
                    ni = int(n)
                    if 1 <= ni <= 11: z['一区'] += 1
                    elif 12 <= ni <= 22: z['二区'] += 1
                    else: z['三区'] += 1
                recent_zones.append(z)
            avg_zones = {z: sum(d[z] for d in recent_zones)/10 for z in ['一区','二区','三区']}
            need_per_zone = {z: max(0, round(2 - avg_zones[z])) for z in avg_zones}
            zone_picked = []
            for z, need in sorted(need_per_zone.items(), key=lambda x: x[1]):
                if z == '一区':
                    pool = range(1, 12)
                elif z == '二区':
                    pool = range(12, 23)
                else:
                    pool = range(23, 34)
                candidates = sorted(pool, key=lambda n: -freq.get(n, 0))
                for n in candidates:
                    if n not in zone_picked and len(zone_picked) < 6:
                        zone_picked.append(n)
                        need -= 1
                        if need <= 0:
                            break
            while len(zone_picked) < 6:
                for n in range(1, 34):
                    if n not in zone_picked:
                        zone_picked.append(n)
                        break
            hits4 = len(set(zone_picked[:6]) & set(actual))
            results['zone_balance']['matches'].append(hits4)

        # 统计命中率
        print(f"\n{'─'*50}")
        print(f"{'方法':20s} {'平均命中':>10s} {'≥3红占比':>10s} {'≥4红占比':>10s}")
        print(f"{'─'*50}")

        for method, data in results.items():
            matches = data['matches']
            avg = sum(matches) / len(matches)
            gt3 = sum(1 for m in matches if m >= 3) / len(matches) * 100
            gt4 = sum(1 for m in matches if m >= 4) / len(matches) * 100
            data['avg_hits'] = avg
            data['hit_rate_3'] = gt3
            data['hit_rate_4'] = gt4
            names = {'heat_map': '①历史热度', 'active': '②短期活跃', 
                     'omission_rev': '③遗漏回补', 'zone_balance': '④区间平衡'}
            print(f"{names.get(method, method):20s} {avg:>8.2f}个   {gt3:>7.1f}%    {gt4:>7.1f}%")

        self.data = self.data  # 恢复
        return results

    def backtest_combined(self, periods=100):
        """
        综合投票回测 — 5种方法投票选号
        """
        if periods > self.N - 310:
            periods = self.N - 310

        test_data = self.data[-(periods + 300):]
        test_start = 300

        print(f"\n{'#'*60}")
        print(f"  综合投票回测 — 近{periods}期")
        print(f"{'#'*60}")

        hit_counts = []
        blue_hits = []

        for i in range(test_start, len(test_data)):
            train = test_data[:i]
            self.data = train
            actual_red = self._to_int(test_data[i]['red'])
            actual_blue = self._to_int(test_data[i]['blue'])

            # 综合投票
            self._silent = True
            rec = self.get_recommendation(period=100)
            self._silent = False
            hits = len(set(rec['red']) & set(actual_red))
            hit_counts.append(hits)
            blue_hit = 1 if rec['blue'] in actual_blue else 0
            blue_hits.append(blue_hit)

        avg_hits = sum(hit_counts) / len(hit_counts)
        gt3 = sum(1 for h in hit_counts if h >= 3) / len(hit_counts) * 100
        gt4 = sum(1 for h in hit_counts if h >= 4) / len(hit_counts) * 100
        gt5 = sum(1 for h in hit_counts if h >= 5) / len(hit_counts) * 100
        blue_rate = sum(blue_hits) / len(blue_hits) * 100

        print(f"\n{'='*50}")
        print(f"  📊 综合投票结果")
        print(f"{'='*50}")
        print(f"  平均红球命中: {avg_hits:.2f}个")
        print(f"  ≥3红: {gt3:.1f}%")
        print(f"  ≥4红: {gt4:.1f}%")
        print(f"  ≥5红: {gt5:.1f}%")
        print(f"  蓝球命中率: {blue_rate:.1f}%")
        print(f"  测试期数: {len(hit_counts)}")

        # 命中分布
        dist = Counter(hit_counts)
        print(f"\n  命中分布:")
        for k in sorted(dist):
            print(f"    命中{k}个: {dist[k]:4d}期 ({dist[k]/len(hit_counts)*100:.1f}%)")

        self.data = self.data  # 恢复
        return {
            'avg_hits': avg_hits,
            'hit_ge3': gt3,
            'hit_ge4': gt4,
            'hit_ge5': gt5,
            'blue_rate': blue_rate,
            'distribution': dict(dist),
            'total': len(hit_counts)
        }


def main():
    """命令行使用示例"""
    import sys
    data_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ssq_data.json'

    analyzer = SSQAnalyzer(data_path)

    # 1. 单期分析示例
    if len(sys.argv) > 2:
        issue = sys.argv[2]
        analyzer.analyze_single(issue)
    else:
        # 最近一期分析
        last_issue = analyzer.data[-1]['issue']
        print(f"\n分析最近一期: {last_issue}")
        analyzer.get_heat_map(period=100)
        analyzer.track_trend(period=30)
        analyzer.analyze_omission()
        analyzer.check_zone_ratio(last_n=10)
        analyzer.analyze_sum_value(last_n=10)
        analyzer.get_recommendation(period=100)

    # 2. 回测（默认100期）
    print("\n\n" + "="*60)
    print("  开始回测...")
    print("="*60)

    analyzer.backtest_individual_methods(periods=100)
    analyzer.backtest_combined(periods=100)


if __name__ == '__main__':
    main()
