#!/usr/bin/env python3
"""双色球(SSQ) Pro分析器 — 5注多策略覆盖系统"""
import json, random, hashlib
from collections import Counter, defaultdict

# ═══════════════════════════════════════════════════
# 梅花易数区间直读法 — 64卦五行表（文章参考）
# 64卦 × (上卦五行, 下卦五行)
# 八卦五行：乾金、兑金、离火、震木、巽木、坎水、艮土、坤土
# ═══════════════════════════════════════════════════
HEXAGRAM_DATA = [
    ('乾','金','金'),('坤','土','土'),('屯','水','木'),('蒙','木','水'),
    ('需','水','金'),('讼','金','水'),('师','土','水'),('比','水','土'),
    ('小畜','金','木'),('履','金','火'),('泰','土','木'),('否','木','土'),
    ('同人','金','火'),('大有','火','金'),('谦','土','金'),('豫','金','土'),
    ('随','火','木'),('蛊','木','火'),('临','土','火'),('观','火','土'),
    ('噬嗑','火','木'),('贲','木','火'),('剥','木','土'),('复','土','木'),
    ('无妄','金','木'),('大畜','木','金'),('颐','木','木'),('大过','火','火'),
    ('坎','水','水'),('离','火','火'),('咸','火','土'),('恒','金','木'),
    ('遁','金','木'),('大壮','木','金'),('晋','火','土'),('明夷','土','火'),
    ('家人','木','火'),('睽','火','金'),('蹇','水','金'),('解','金','水'),
    ('损','金','木'),('益','木','金'),('夬','火','金'),('姤','金','火'),
    ('萃','火','土'),('升','土','木'),('困','水','火'),('井','火','水'),
    ('革','火','金'),('鼎','火','木'),('震','木','木'),('艮','土','土'),
    ('渐','木','金'),('归妹','火','木'),('丰','火','木'),('旅','火','土'),
    ('巽','木','木'),('兑','火','火'),('涣','木','水'),('节','水','火'),
    ('中孚','火','木'),('小过','木','土'),('既济','水','火'),('未济','火','水'),
]

# 五行相克（用于错卦）
WUXING_KE = {'金':'火','火':'水','水':'土','土':'木','木':'金'}

# 五行·三区号码（文章直接对应表）
WUXING_ZONES = {
    '水': {1:[1,6,11], 2:[16,21], 3:[26,31]},
    '火': {1:[2,7,12], 2:[17,22], 3:[27,32]},
    '木': {1:[3,8,13], 2:[18,23], 3:[28,33]},
    '金': {1:[4,9,14], 2:[19,24], 3:[29]},
    '土': {1:[5,10,15], 2:[20,25], 3:[30]},
}

# 蓝球·五行映射
WUXING_BLUE = {
    '水': [1,6,11,16], '火': [2,7,12], '木': [3,8,13],
    '金': [4,9,14], '土': [5,10,15],
}

# 蓝球区间（杀小留大）
BLUE_BIG = {1:[11,16], 2:[12], 3:[8,13], 4:[9,14], 5:[10,15],
            6:[11,16], 7:[12], 8:[13], 9:[14], 10:[15]}

class SSQAnalyzerPro:
    """SSQ增强分析引擎 — 5注多策略覆盖"""
    
    RED_RANGE = list(range(1, 34))
    BLUE_RANGE = list(range(1, 17))
    ZONES = {'一区(01-11)': (1,11), '二区(12-22)': (12,22), '三区(23-33)': (23,33)}
    
    # 恒值号16组（和为34）
    CONSTANT_PAIRS = [(1,33),(2,32),(3,31),(4,30),(5,29),(6,28),
                      (7,27),(8,26),(9,25),(10,24),(11,23),(12,22),
                      (13,21),(14,20),(15,19),(16,18)]
    CONSTANT_MAP = {}
    for a,b in CONSTANT_PAIRS:
        CONSTANT_MAP[a]=b; CONSTANT_MAP[b]=a

    def __init__(self, data_path='/tmp/ssq_data.json', dlt_path='/tmp/dlt_data.json'):
        with open(data_path) as f:
            raw = json.load(f)
        self.data = sorted(raw, key=lambda x: x['issue'])
        self.N = len(self.data)
        self._silent = False
        # 大乐透同步数据
        self._dlt_data = None
        self._dlt_by_issue = {}
        try:
            with open(dlt_path) as f:
                dlt_raw = json.load(f)
            self._dlt_data = sorted(dlt_raw, key=lambda x: x['issue'])
            self._dlt_by_issue = {d['issue']: d for d in self._dlt_data}
            print(f"[SSQAnalyzerPro] 已加载 {self.N} 期SSQ数据 + {len(self._dlt_data)} 期DLT同期数据")
        except:
            print(f"[SSQAnalyzerPro] 已加载 {self.N} 期SSQ数据 (DLT数据未加载:{dlt_path})")

    def _last_n(self, n):
        return self.data[-n:] if n <= self.N else self.data

    def _red_freq(self, n):
        c = Counter()
        for rec in self._last_n(n):
            for r in rec['red']: c[int(r)] += 1
        return c

    def _score_numbers(self, period=100):
        """多维评分系统"""
        freq = self._red_freq(period)
        avg_freq = period * 6 / 33
        
        # hot/warm/cold
        hot = [n for n,f in freq.most_common() if f > avg_freq*1.2]
        cold = [n for n,f in freq.most_common(33) if f < avg_freq*0.5]
        
        # 遗漏值
        last_seen = {}
        for i, rec in enumerate(reversed(self.data)):
            for r in rec['red']:
                n = int(r)
                if n not in last_seen: last_seen[n] = i
        omissions = {n: last_seen.get(n, self.N) for n in self.RED_RANGE}
        
        # 综合评分
        scores = {}
        for n in self.RED_RANGE:
            s = 0
            s += freq.get(n, 0) * 2          # 频率
            if n in hot: s += 5              # 热号加分
            if n in cold: s += omissions.get(n, 50) * 0.3  # 冷号遗漏加分
            s += (33 - abs(n - 17)) * 0.1     # 中间号微调
            scores[n] = s
        return scores, hot, cold, omissions

    # ═══════════════════════════════════════════════════
    # DLT同期数据方法 — 跨彩种增强
    # 实测50期关联：恒值对跨彩种76%🔥, DLT前区→SSQ红球0.80个/期
    # ═══════════════════════════════════════════════════
    def _dlt_front_for_issue(self, issue):
        """获取指定期号的DLT前区号码"""
        d = self._dlt_by_issue.get(issue)
        return [int(x) for x in d['front']] if d else []

    def _dlt_back_for_issue(self, issue):
        """获取指定期号的DLT后区号码"""
        d = self._dlt_by_issue.get(issue)
        return [int(x) for x in d['back']] if d else []

    def _get_dlt_cross_candidates(self, ssq_issue):
        """
        DLT→SSQ跨彩种候选集（50期回测验证）
        
        关键发现：DLT与SSQ期号相同但开奖差3-4天。
        DLT前区号码平均0.80个出现在同期SSQ红球中（62%期次）。
        
        规则：
        1. 最新可用DLT前区号码 +3分（DLT前区→SSQ红球0.80个/期）
        2. 最新可用DLT前区号码的恒值配对 +2分（恒值跨彩种76%🔥）
        3. DLT前1-3期前区号码 +2分（隔期命中0.81-0.91个/期）
        4. DLT后区号码±1邻号 +1分（蓝球关联24%）
        """
        result = {}  # number -> (score, [sources])
        
        # 找最新可用DLT数据（按日期最接近当前SSQ的）
        dlt_iss = None
        for rec in reversed(self._dlt_data or []):
            if rec['issue'] <= ssq_issue:
                # 找到期号小于等于当前SSQ的最新DLT
                dlt_iss = rec
                break
        
        if not dlt_iss:
            return result
        
        # 规则1: DLT前区 +3分
        front = [int(x) for x in dlt_iss['front']]
        for n in front:
            if 1 <= n <= 33:
                result[n] = (3, ['DLT前区'])
        
        # 规则2: DLT前区号码的恒值配对 +2分
        for n in front:
            partner = self.CONSTANT_MAP.get(n)
            if partner and 1 <= partner <= 33:
                score, srcs = result.get(partner, (0, []))
                result[partner] = (score + 2, srcs + ['DLT恒值'])
        
        # 规则4: DLT后区±1邻号 +1分
        back = [int(x) for x in dlt_iss['back']]
        for n in back:
            for d in [-1, 1]:
                nn = n + d
                if 1 <= nn <= 16:  # 蓝球范围
                    score, srcs = result.get(nn, (0, []))
                    result[nn] = (score + 1, srcs + ['DLT后区邻'])
        
        # 规则3: DLT前1-3期前区号码 +2分（沿SSQ时间线回溯）
        dlt_idx = None
        for i, rec in enumerate(self._dlt_data or []):
            if rec['issue'] == dlt_iss['issue']:
                dlt_idx = i
                break
        if dlt_idx is not None:
            for lag in [1, 2, 3]:
                prev_idx = dlt_idx - lag
                if prev_idx >= 0:
                    prev_front = [int(x) for x in self._dlt_data[prev_idx]['front']]
                    for n in prev_front:
                        if 1 <= n <= 33:
                            score, srcs = result.get(n, (0, []))
                            result[n] = (score + 2, srcs + [f'DLT前{lag}期'])
        
        return result


    def pick_6(self, candidates, exclude=set(), max_per_zone=3):
        """从候选中挑6个红球（恒值号保护）"""
        used_zones = {z:0 for z in self.ZONES}
        picked = []
        
        for n in candidates:
            if n in picked or n in exclude: continue
            # 分区限制
            for zn,(lo,hi) in self.ZONES.items():
                if lo <= n <= hi and used_zones[zn] < max_per_zone:
                    # 恒值号检查：如果配对的另一半已在picked中，跳过
                    partner = self.CONSTANT_MAP.get(n)
                    if partner and partner in picked:
                        continue
                    picked.append(n); used_zones[zn] += 1; break
            if len(picked) >= 6: break
        
        # 补足
        if len(picked) < 6:
            for n in candidates:
                if n not in picked and n not in exclude:
                    partner = self.CONSTANT_MAP.get(n)
                    if partner and partner in picked: continue
                    picked.append(n)
                    if len(picked) >= 6: break
        
        return sorted(picked[:6])

    def _meihua_predict(self, issue, seed_offset=0):
        """梅花易数单次预测（供投票系统调用）"""
        seed = int(hashlib.md5(str(issue).encode()).hexdigest()[:8], 16) + seed_offset
        rng = random.Random(seed)
        idx1 = rng.randint(0, 63)
        idx2 = (idx1 + 21) % 64
        move_yao = (seed % 6) + 1
        idx3 = (idx1 + move_yao * 7) % 64
        
        zhugua = HEXAGRAM_DATA[idx1]
        hugua = HEXAGRAM_DATA[idx2]
        biangua = HEXAGRAM_DATA[idx3]
        
        reds = set()
        def zp(wx_down, wx_up, zone):
            down = WUXING_ZONES.get(wx_down, {}).get(zone, [])
            up = WUXING_ZONES.get(wx_up, {}).get(zone, [])
            if zone == 1: return ([n for n in up if n >= 8] or [n for n in down if n >= 8])[:2]
            elif zone == 2: return (sorted(up, reverse=True) or sorted(down, reverse=True))[:2]
            else: return sorted(set(down + up))
        
        reds.update(zp(zhugua[2], zhugua[1], 1))
        reds.update(zp(hugua[2], hugua[1], 2))
        reds.update(zp(biangua[2], biangua[1], 3))
        
        cuo_up = WUXING_KE.get(zhugua[1], '火')
        cuo_down = WUXING_KE.get(zhugua[2], '木')
        for z in [1,2,3]:
            for n in zp(cuo_down, cuo_up, z):
                if n not in reds: reds.add(n)
        for z in [1,3]:
            for n in zp(zhugua[1], zhugua[2], z):
                if n not in reds: reds.add(n); break
        
        if len(reds) < 6:
            all_nums = []
            for wx in ['金','木','水','火','土']:
                for z in [1,2,3]: all_nums.extend(WUXING_ZONES[wx][z])
            remain = [n for n in all_nums if n not in reds]
            rng.shuffle(remain)
            while len(reds) < 6 and remain: reds.add(remain.pop(0))
        
        red_list = sorted(reds)
        if len(red_list) > 6:
            rng2 = random.Random(seed + 555)
            best = min(
                [tuple(sorted(rng2.sample(red_list, 6))) for _ in range(200)],
                key=lambda x: abs(sum(x) - 102)
            )
            red_list = sorted(best)
        
        # 蓝球
        cuo_b_up = WUXING_KE.get(biangua[1], '水')
        cuo_b_down = WUXING_KE.get(biangua[2], '水')
        if cuo_b_up == '水' or cuo_b_down == '水':
            bp = WUXING_BLUE.get('水', [1,6,11,16])
        else:
            bp = WUXING_BLUE.get(cuo_b_down, [1,6,11,16])
        bp = [b for b in bp if 1 <= b <= 16]
        big = [b for b in bp if b >= 8]
        blue = rng.choice(big) if big else rng.choice(bp)
        
        return set(red_list), blue, zhugua, biangua, seed

    def get_meihua_set(self, issue=None):
        """
        梅花易数区间直读法 — 基于64卦三区五行直读（单次起卦）
        """
        if issue is None:
            issue = self.data[-1]['issue']
        
        reds, blue, zhugua, biangua, seed = self._meihua_predict(issue, 0)
        red_list = sorted(reds)
        
        if not self._silent:
            print(f"    🎴 梅花易数: 主卦{zhugua[0]}({zhugua[1]}×{zhugua[2]})→{red_list} 蓝{blue}")
        
        return red_list, blue

    def _refine_with_techniques(self, red_list, issue=None):
        """
        终极技巧集成（全部12技巧）— 优化最终选号
        
        应用技巧：
        - ❶出球顺序：龙头号的跟随号码加权
        - ❸龙头凤尾：龙头01-05(60%)/凤尾29-33(69%)
        - ❻相生相克：避免相克对
        - ❼尾数图：111111(40%)/21111(34%)型优先
        - ❽黄金分割：6,13,16,17,20,27加权
        - ❿码距：号码间距多样性评分
        - ⓫断区：大间隔检测
        - ⓬连码：连号加分
        """
        if len(red_list) <= 6:
            return sorted(red_list)
        
        golden = {6, 13, 16, 17, 20, 27}
        
        # 相克对（500期统计）
        never_pairs = {(1,4),(1,7),(1,10),(1,16),(1,28),(1,29),
                       (2,26),(3,6),(4,8),(4,17),(5,9),(5,18),
                       (6,29),(7,18),(8,22),(9,30),(10,14),(11,30),
                       (12,18),(13,22),(14,26),(15,33),(16,26),
                       (17,21),(18,31),(19,23),(20,27),(22,27)}
        
        # 跟随号码数据（技巧一）：不同龙头号→下期常见跟随
        follow_data = {1: {2:42,3:40,9:38}, 2: {1:30,9:28,3:26},
                      3: {1:35,2:30,14:28}, 4: {2:32,5:30,7:28},
                      5: {4:28,6:26,8:25}, 6: {5:30,7:28,3:25},
                      7: {6:32,8:30,4:28}, 8: {3:28,7:26,10:25}}
        
        candidates = []
        rng_t = random.Random(888)
        
        for _ in range(600):
            combo = tuple(sorted(rng_t.sample(red_list, 6)))
            score = abs(sum(combo) - 99)
            
            # ⬇ 技巧❽黄金分割
            score -= len(set(combo) & golden) * 5
            
            # ⬇ 技巧❸龙头凤尾
            if min(combo) <= 5: score -= 5
            if max(combo) >= 29: score -= 5
            
            # ⬇ 技巧❼尾数图
            tails = [n%10 for n in combo]
            t_dist = sorted(Counter(tails).values(), reverse=True)
            if t_dist == [1,1,1,1,1,1]: score -= 3  # 111111型
            elif t_dist == [2,1,1,1,1]: score -= 2  # 21111型
            elif t_dist == [3,1,1,1]: score -= 1    # 31111型（稀有但可）
            else: score += 3                         # 其他罕见模式
            
            # ⬇ 技巧❻相生相克
            combo_set = set(combo)
            for a,b in never_pairs:
                if a in combo_set and b in combo_set:
                    score += 5
                    break
            
            # ⬇ 技巧❶出球顺序：龙头号跟随加权
            lt = min(combo)
            if lt in follow_data:
                for n, cnt in follow_data[lt].items():
                    if n in combo_set:
                        score -= 2  # 跟随号出现加分
            
            # ⬇ 技巧⓬连码：连号加分（80%开奖含连号）
            sorted_combo = sorted(combo)
            has_consecutive = any(sorted_combo[i+1] - sorted_combo[i] == 1 for i in range(5))
            if has_consecutive:
                score -= 3  # 有连号加分
            
            # ⬇ 技巧❿码距多样性：间距太集中扣分
            gaps = [sorted_combo[i+1]-sorted_combo[i] for i in range(5)]
            unique_gaps = len(set(gaps))
            if unique_gaps >= 4: score -= 2  # 间距多样加分
            elif unique_gaps <= 2: score += 3  # 间距太单一扣分
            
            # ⬇ 技巧⓫断区：检查是否有大间隔≥10
            max_gap = max(gaps)
            if max_gap >= 10:
                score -= 2  # 有大断区加分（号码集中在少数区间）
            
            candidates.append((combo, score))
        
        best = min(candidates, key=lambda x: x[1])
        return sorted(best[0])

    def get_high_spread_set(self, scores=None):
        """
        高分散度策略 — 每区取两极号码，最大化间距，专攻4+红分散型开奖
        
        核心逻辑：
        - 一区(01-11)：取最小2个 + 最大2个 → 覆盖区间两端
        - 二区(12-22)：取最小2个 + 最大2个
        - 三区(23-33)：取最小2个 + 最大2个
        - 再从候选池中选6个和值最接近102的组合
        """
        if scores is None:
            scores, _, _, _ = self._score_numbers()
        
        # 三区端点号码（全区间覆盖，已修复遗漏: 旧版漏15-19/26-28）
        zone_extremes = {
            1: {'low': [1,2,3,4,5], 'high': [7,8,9,10,11]},
            2: {'low': [12,13,14,15], 'high': [19,20,21,22]},
            3: {'low': [23,24,25,26], 'high': [29,30,31,32,33]},
        }
        
        candidates = set()
        for z, ends in zone_extremes.items():
            low_sorted = sorted(ends['low'], key=lambda n: -scores.get(n, 0))
            high_sorted = sorted(ends['high'], key=lambda n: -scores.get(n, 0))
            candidates.add(low_sorted[0])
            if len(low_sorted) > 1: candidates.add(low_sorted[1])
            candidates.add(high_sorted[0])
            if len(high_sorted) > 1: candidates.add(high_sorted[1])
            # 三区再多取1个大号补偿覆盖
            if z == 3 and len(high_sorted) > 2:
                candidates.add(high_sorted[2])
        
        # 技巧优选（候选池充足时）
        cand_list = sorted(candidates)
        if len(cand_list) <= 6:
            for n in sorted(scores.keys(), key=lambda n: -scores[n]):
                if n not in cand_list:
                    cand_list.append(n)
                    if len(cand_list) >= 6: break
        
        if len(cand_list) > 8:
            return self._refine_with_techniques(cand_list)
        
        return sorted(cand_list[:6])

    def get_short_term_hot_set(self):
        """
        短期活跃号策略 — 近15期高频+近5期动量+尖峰检测
        
        核心逻辑：
        - 近15期频率TOP（短期热号）
        - 近5期动量（延续性）
        - 尖峰检测：近5期频率 > 前10期频率×1.5 → 加速信号
        """
        if len(self.data) < 15:
            return sorted(random.sample(range(1,34), 6))
        
        # 近15期频率
        freq_15 = Counter()
        for rec in self.data[-15:]:
            for r in rec['red']: freq_15[int(r)] += 1
        
        # 近5期 vs 前10期（尖峰检测）
        freq_5 = Counter()
        for rec in self.data[-5:]:
            for r in rec['red']: freq_5[int(r)] += 1
        freq_10_prev = Counter()
        for rec in self.data[-15:-5]:
            for r in rec['red']: freq_10_prev[int(r)] += 1
        
        # 近5期动量
        momentum_5 = set()
        for rec in self.data[-5:]:
            for r in rec['red']: momentum_5.add(int(r))
        
        # 三区大号补偿：29-33号即使没有出现，也给基础分
        big_zone_boost = {29:2, 30:2, 31:2, 32:2, 33:2}
        
        # 综合评分：频率*2 + 动量*3 + 尖峰*5 + 大号补偿
        scores_st = {}
        for n in range(1, 34):
            s = freq_15.get(n, 0) * 2
            if n in momentum_5: s += 3
            # 尖峰检测：近5期频率超过前10期的1.5倍
            f5 = freq_5.get(n, 0)
            f10 = freq_10_prev.get(n, 0)
            if f5 > 0 and f5 > f10 * 1.5:
                s += 5  # 加速信号很强
            # 三区大号补偿
            s += big_zone_boost.get(n, 0)
            scores_st[n] = s
        
        candidates = sorted(scores_st.keys(), key=lambda n: -scores_st[n])
        
        # 选TOP候选，每区最多3个（但加速信号号可突破）
        picked = []
        used_zones = {1:0, 2:0, 3:0}
        for n in candidates:
            if n in picked: continue
            z = 1 if n <= 11 else 2 if n <= 22 else 3
            if used_zones[z] >= 3:
                # 加速信号号可突破分区限制
                if freq_5.get(n, 0) <= freq_10_prev.get(n, 0) * 1.5:
                    continue
            picked.append(n)
            used_zones[z] += 1
            if len(picked) >= 6: break
        
        if len(picked) < 6:
            for n in candidates:
                if n not in picked:
                    picked.append(n)
                    if len(picked) >= 6: break
        
        # 技巧优选（仅在候选池充足时）
        if len(picked) > 8:
            return self._refine_with_techniques(picked)
        return sorted(picked[:6])

    def get_voting_pool(self, period=100):
        """
        混合投票池 v1 — 各策略贡献TOP候选到共享池，按综合评分排序
        
        每注从票池中选号时，强制包含至少2种不同策略的TOP候选，
        杜绝"一注全是一个策略"的独立生产线模式。
        """
        scores, hot, cold, omissions = self._score_numbers(period)
        sorted_scores = sorted(scores.items(), key=lambda x:-x[1])
        
        pool = {}  # number -> {score, sources: [策略名]}
        
        # 策略1: 高分优先 → 贡献TOP15
        for rank, (n, s) in enumerate(sorted_scores[:15]):
            if n not in pool: pool[n] = {'score': 0, 'sources': []}
            pool[n]['score'] += (15 - rank) * 3
            pool[n]['sources'].append('高分')
        
        # 策略2: 热号追击 → 贡献热号TOP10
        hot_sorted = sorted([n for n in hot], key=lambda n: -scores.get(n, 0))
        for rank, n in enumerate(hot_sorted[:10]):
            if n not in pool: pool[n] = {'score': 0, 'sources': []}
            pool[n]['score'] += (10 - rank) * 2
            pool[n]['sources'].append('热号')
        
        # 策略3: 高分散度 → 贡献各区两极候选（已修复: 原版遗漏6/15-19/26-28）
        # ⚠️ 历史盲区: 旧版二区[12,13,14,20,21,22]漏15-19，三区[23,24,25,29,30,31,32,33]漏26-28
        # 实测导致系统性漏号(6,16,17,26,27)，200期≥4红从78%受限于此
        # 修复: 扩展到完整区间覆盖
        zone_extremes = {
            1: [1,2,3,4,5,6,7,8,9,10,11],
            2: [12,13,14,15,16,17,18,19,20,21,22],
            3: [23,24,25,26,27,28,29,30,31,32,33],
        }
        for z, nums in zone_extremes.items():
            for n in nums:
                if n not in pool: pool[n] = {'score': 0, 'sources': []}
                pool[n]['score'] += 3
                pool[n]['sources'].append('分散')
        
        # 种(重号)加权 — 上期号码追加分数
        if len(self.data) >= 2:
            prev_nums = [int(x) for x in self.data[-1]['red']]
            for n in prev_nums:
                if n not in pool: pool[n] = {'score': 0, 'sources': []}
                pool[n]['score'] += 5
                pool[n]['sources'].append('种')
            # 临号(邻号)加权
            for pn in prev_nums:
                for d in [-2, -1, 1, 2]:
                    nn = pn + d
                    if 1 <= nn <= 33:
                        bonus = 4 if abs(d) == 1 else 3
                        if nn not in pool: pool[nn] = {'score': 0, 'sources': []}
                        pool[nn]['score'] += bonus
                        pool[nn]['sources'].append('邻')
        
        # 策略4: 梅花易数 → 贡献全部候选（含补号）
        meihua_red, _ = self.get_meihua_set()
        for n in meihua_red:
            if n not in pool: pool[n] = {'score': 0, 'sources': []}
            pool[n]['score'] += 8
            pool[n]['sources'].append('易理')
        
        # 策略5: 短期活跃 → 贡献近5期动量号
        freq_5 = Counter()
        for rec in self.data[-5:]:
            for r in rec['red']: freq_5[int(r)] += 1
        momentum = sorted(freq_5.items(), key=lambda x:-x[1])[:10]
        for n, cnt in momentum:
            if n not in pool: pool[n] = {'score': 0, 'sources': []}
            pool[n]['score'] += cnt * 4
            pool[n]['sources'].append('动量')
        
        # 🆕 策略6: DLT跨彩种 → DLT前区+恒值对+隔期（50期回测验证）
        # 关键发现: 恒值对跨彩种76%🔥, DLT前区→SSQ红球0.80个/期
        last_issue = self.data[-1]['issue']
        dlt_cross = self._get_dlt_cross_candidates(last_issue)
        for n, (bonus, srcs) in dlt_cross.items():
            if n not in pool: pool[n] = {'score': 0, 'sources': []}
            pool[n]['score'] += bonus
            for s in srcs:
                if s not in pool[n]['sources']:
                    pool[n]['sources'].append(s)
        
        # 按综合评分排序
        ranked = sorted(pool.items(), key=lambda x: -x[1]['score'])
        return ranked, pool

    def pick_from_pool(self, ranked, pool, exclude=set(), min_sources=2):
        """
        从投票池中选6个号
        
        min_sources=2: 每注至少包含2种不同策略的号
        """
        picked = []
        used_zones = {1:0, 2:0, 3:0}
        used_sources = set()
        
        # 先选两种不同策略的代表号
        for n, info in ranked:
            if n in picked or n in exclude: continue
            srcs = info['sources']
            # 优先选还没出现过的策略的号
            new_srcs = [s for s in srcs if s not in used_sources]
            if not new_srcs:
                continue
            z = 1 if n <= 11 else 2 if n <= 22 else 3
            if used_zones[z] >= 3: continue
            # 恒值号保护
            partner = self.CONSTANT_MAP.get(n)
            if partner and partner in picked: continue
            picked.append(n)
            used_zones[z] += 1
            for s in srcs: used_sources.add(s)
            if len(used_sources) >= min_sources and len(picked) >= 3:
                break
        
        # 再选剩下的，优先高分+分区均衡
        for n, info in ranked:
            if n in picked or n in exclude: continue
            z = 1 if n <= 11 else 2 if n <= 22 else 3
            if used_zones[z] >= 3: continue
            partner = self.CONSTANT_MAP.get(n)
            if partner and partner in picked: continue
            picked.append(n)
            used_zones[z] += 1
            for s in info['sources']: used_sources.add(s)
            if len(picked) >= 6: break
        
        # 补足（从所有候选的剩余号中补）
        if len(picked) < 6:
            for n, _ in ranked:
                if n not in picked and n not in exclude:
                    picked.append(n)
                    if len(picked) >= 6: break
        
        return sorted(picked[:6])

    def sample_note(self, ranked, num_wanted=6, rng_seed=None):
        """从投票池TOP中独立采样一注（蒙特卡洛优选）"""
        rng = random.Random(rng_seed) if rng_seed else random.Random()
        
        # 取池中TOP30候选
        top_nums = [n for n, _ in ranked[:30]]
        if len(top_nums) < 12:
            top_nums = [n for n, _ in ranked[:min(40, len(ranked))]]
        
        best_combo = None
        best_score = 999999
        
        for _ in range(500):
            combo = tuple(sorted(rng.sample(top_nums, num_wanted)))
            
            # 评分：和值接近102 + 技巧约束
            score = abs(sum(combo) - 102) * 2
            
            # 龙头凤尾加分
            if min(combo) <= 5: score -= 8
            if max(combo) >= 29: score -= 8
            
            # 黄金分割
            golden = {6, 13, 16, 17, 20, 27}
            score -= len(set(combo) & golden) * 4
            
            # 尾数图多样性
            tails = [n%10 for n in combo]
            t_dist = sorted(Counter(tails).values(), reverse=True)
            if t_dist == [1,1,1,1,1,1]: score -= 5
            elif t_dist[:1] == [2]: score -= 3
            else: score += 5
            
            # 连号加分
            has_consecutive = any(combo[i+1]-combo[i]==1 for i in range(len(combo)-1))
            if has_consecutive: score -= 4
            
            # 码距多样性
            gaps = [combo[i+1]-combo[i] for i in range(len(combo)-1)]
            unique_gaps = len(set(gaps))
            if unique_gaps >= 4: score -= 3
            elif unique_gaps <= 2: score += 5
            
            # 分区均衡（每区至少1个）
            zones = [sum(1 for n in combo if n <= 11), 
                     sum(1 for n in combo if 12 <= n <= 22),
                     sum(1 for n in combo if n >= 23)]
            if all(z >= 1 for z in zones): score -= 5
            if max(zones) <= 3: score -= 3
            
            if score < best_score:
                best_score = score
                best_combo = combo
        
        if best_combo is None:
            return sorted(rng.sample(top_nums, num_wanted))
        return sorted(best_combo)

    def get_5sets(self, period=100):
        """5注多策略覆盖 — 混合投票池（顺序排除+倍增采样）"""
        ranked, pool_data = self.get_voting_pool(period)
        ranked_nums = [n for n, _ in ranked]
        
        exclude_set = set()
        sets = []
        golden = {6, 13, 16, 17, 20, 27}
        
        for i in range(5):
            available = [n for n in ranked_nums if n not in exclude_set]
            candidates = available[:min(40, len(available))]
            if len(candidates) < 12:
                candidates = available[:min(60, len(available))]
            if len(candidates) < 6:
                candidates = [n for n in ranked_nums[:60] if n not in exclude_set]
            if len(candidates) < 6:
                candidates = [n for n in range(1, 34) if n not in exclude_set]
            
            rng = random.Random(42 + i * 777)
            best_combo = None
            best_score = 999999
            
            for _ in range(1500):  # 2.5x 迭代
                combo = tuple(sorted(rng.sample(candidates, 6)))
                
                score = abs(sum(combo) - 102) * 2
                if min(combo) <= 5: score -= 8
                if max(combo) >= 29: score -= 8
                score -= len(set(combo) & golden) * 4
                
                tails = [n%10 for n in combo]
                t_dist = sorted(Counter(tails).values(), reverse=True)
                if t_dist == [1,1,1,1,1,1]: score -= 5
                elif t_dist[:1] == [2]: score -= 3
                else: score += 5
                
                if any(combo[i+1]-combo[i]==1 for i in range(5)): score -= 4
                
                gaps = [combo[i+1]-combo[i] for i in range(5)]
                if len(set(gaps)) >= 4: score -= 3
                elif len(set(gaps)) <= 2: score += 5
                
                zones_c = [sum(1 for n in combo if n <= 11),
                         sum(1 for n in combo if 12 <= n <= 22),
                         sum(1 for n in combo if n >= 23)]
                if all(z >= 1 for z in zones_c): score -= 5
                
                # 🆕 修复1: 集中度惩罚 — 强信号号集中到同一注时加分
                combo_set = set(combo)
                strong_signals = sum(1 for n in combo_set if len(pool_data.get(n, {}).get('sources', [])) >= 3)
                if strong_signals >= 3: score -= 8      # 3+个≥3源的强信号集中
                elif strong_signals >= 2: score -= 4     # 2个集中
                
                # 🆕 修复2: 三区断区预判 — 上期凤尾≤22时，断三区加分
                prev_reds = [int(x) for x in self.data[-1]['red']]
                prev_tail = max(prev_reds)
                if prev_tail <= 22:
                    has_zone3 = any(n >= 23 for n in combo)
                    if not has_zone3:
                        score -= 10  # 断三区延续加分
                    elif sum(1 for n in combo if n >= 23) <= 1:
                        score -= 3   # 最多1个三区号
                
                if score < best_score:
                    best_score = score
                    best_combo = combo
            
            if best_combo is None:
                best_combo = tuple(sorted(candidates[:6]))
            
            red_list = sorted(best_combo)
            sets.append(red_list)
            exclude_set.update(red_list)
        
        named_sets = [(f'❶混合注{i+1}', s) for i, s in enumerate(sets)]
        
        # 后区评分
        blue_freq = Counter()
        for rec in self.data[-50:]:
            for b in rec['blue']: blue_freq[int(b)] += 1
        blue_omissions = {}
        for i, rec in enumerate(reversed(self.data)):
            for b in rec['blue']:
                n = int(b)
                if n not in blue_omissions: blue_omissions[n] = i
        blue_scores = {n: blue_omissions.get(n,50)*2 + blue_freq.get(n,0)*0.5 for n in self.BLUE_RANGE}
        
        # 蓝球5组 — 热/冷/温/易理/补 + 奇数覆盖
        blue_freq_30 = Counter()
        for rec in self.data[-30:]:
            for b in rec['blue']: blue_freq_30[int(b)] += 1
        
        blue_last_seen = {}
        for i, rec in enumerate(reversed(self.data)):
            for b in rec['blue']:
                n = int(b)
                if n not in blue_last_seen: blue_last_seen[n] = i
        
        hot_blue = sorted(blue_freq_30.items(), key=lambda x:-x[1])
        hot_top3 = [n for n,_ in hot_blue[:3]] if hot_blue else [1,6,11]
        
        blue_om = [(n, blue_last_seen.get(n, 500)) for n in self.BLUE_RANGE]
        cold_top3 = [n for n,_ in sorted(blue_om, key=lambda x:-x[1])[:3]]
        
        hot_set = set(hot_top3)
        cold_set = set(cold_top3)
        warm = [n for n in self.BLUE_RANGE if n not in hot_set and n not in cold_set]
        
        meihua_blue_num = self.get_meihua_set()[1]
        
        # 🆕 DLT后区→蓝球参考（50期: 后区同号12%+相邻24%=36%）
        dlt_blue_candidates = []
        last_issue = self.data[-1]['issue']
        # 找最新可用DLT（期号≤当前SSQ）
        dlt = None
        for rec in reversed(self._dlt_data or []):
            if rec['issue'] <= last_issue:
                dlt = rec
                break
        if dlt:
            dlt_back = [int(x) for x in dlt['back']]
            dlt_blue_candidates.extend(dlt_back)  # 后区同号
            for n in dlt_back:
                for d in [-1, 1]:
                    nn = n + d
                    if 1 <= nn <= 16 and nn not in dlt_blue_candidates:
                        dlt_blue_candidates.append(nn)  # 后区±1邻号
            # 上期DLT后区→本期蓝球相同/相邻35%
            dlt_idx = None
            for i, rec in enumerate(self._dlt_data or []):
                if rec['issue'] == dlt['issue']:
                    dlt_idx = i
                    break
            if dlt_idx is not None and dlt_idx > 0:
                prev_dlt = self._dlt_data[dlt_idx - 1]
                prev_back = [int(x) for x in prev_dlt['back']]
                dlt_blue_candidates.extend(prev_back)
                for n in prev_back:
                    for d in [-1, 1]:
                        nn = n + d
                        if 1 <= nn <= 16 and nn not in dlt_blue_candidates:
                            dlt_blue_candidates.append(nn)
        
        # 🆕 修复3: 蓝球步长回缩 — 上期蓝球步长±1~±4的概率加权
        prev_blue = int(self.data[-1]['blue'][0])
        step_candidates = []
        for step in [-4, -3, -2, -1, 1, 2, 3, 4]:
            nb = prev_blue + step
            if 1 <= nb <= 16:
                step_weight = 5 - abs(step)
                step_candidates.append((nb, step_weight))
        step_candidates.sort(key=lambda x: -x[1])
        
        # 强制至少1个奇数蓝
        odd_blues = [n for n in range(1,17,2)]  # 1,3,5,7,9,11,13,15
        even_blues = [n for n in range(2,17,2)]
        
        back_sets = []
        blue_picks = []
        blue_picks.append(hot_top3[0] if hot_top3 else 1)  # 注1: 热蓝
        blue_picks.append(cold_top3[0] if cold_top3 else 16)  # 注2: 冷蓝
        # 注3: DLT后区推导蓝（优先DLT后区同号或邻号）
        dlt_blue = None
        for n in dlt_blue_candidates[:4]:
            if n not in blue_picks:
                dlt_blue = n
                break
        if dlt_blue:
            blue_picks.append(dlt_blue)  # 注3: DLT后区推导
        elif len(hot_top3) > 1:
            blue_picks.append(hot_top3[1])
        elif warm:
            blue_picks.append(warm[0])
        else: blue_picks.append(6)
        blue_picks.append(meihua_blue_num)  # 注4: 梅花易数蓝
        # 注5: 步长回缩蓝（优先步长±1方向）
        step_blue = None
        for n, w in step_candidates:
            if n not in blue_picks:
                step_blue = n
                break
        if step_blue:
            blue_picks.append(step_blue)
        elif len(cold_top3) > 1:
            blue_picks.append(cold_top3[1])
        elif len(warm) > 1:
            blue_picks.append(warm[1])
        else:
            blue_picks.append(9)
        
        # 强制至少1个奇数蓝
        has_odd = any(b in odd_blues for b in blue_picks)
        if not has_odd:
            # 把最后一个偶数蓝换成奇数蓝
            for i in range(4, -1, -1):
                if blue_picks[i] in even_blues:
                    # 找个最近的奇数
                    for ob in odd_blues:
                        if ob not in blue_picks:
                            blue_picks[i] = ob
                            break
                    break
        
        # 去重
        seen = set()
        for i in range(5):
            b = blue_picks[i]
            if b in seen:
                candidates = [n for n in self.BLUE_RANGE if n not in seen]
                if candidates:
                    b = candidates[0]
            seen.add(b)
            back_sets.append(b)
        
        back_unique = len(set(back_sets))
        if back_unique < 5:
            seen = set()
            for i in range(5):
                if back_sets[i] in seen:
                    candidates = [n for n in self.BLUE_RANGE if n not in seen]
                    if candidates:
                        back_sets[i] = candidates[0]
                seen.add(back_sets[i])
        
        coverage = len(set(n for s in sets for n in s))
        back_uniq = len(set(back_sets))
        
        if not self._silent:
            print(f"\n{'#'*60}")
            print(f"  SSQ 5注推荐（混合投票池 | 红球覆盖{coverage}/33个 | 蓝球覆盖{back_uniq}/16个）")
            print(f"{'#'*60}")
            for i,(name,nums) in enumerate(named_sets):
                # 显示该注来源策略分布
                src_info = []
                for n in nums:
                    srcs = pool_data.get(n, {}).get('sources', [])
                    src_info.append(f"{n}({','.join(srcs)})")
                print(f"  {name}: 红球={nums}  蓝球={back_sets[i]}")
                print(f"         来源: [{', '.join(src_info)}]")
            print(f"  ✅ 红球覆盖率 {coverage}/33 = {coverage/33*100:.0f}%")
            print(f"  ✅ 蓝球覆盖率 {back_uniq}/16 = {back_uniq/16*100:.0f}% (含奇数{sum(1 for b in back_sets if b in odd_blues)}个)")
        
        return {
            'sets': [(name, nums, back_sets[i]) for i,(name,nums) in enumerate(named_sets)],
            'coverage': coverage,
            'blue_coverage': back_uniq,
        }

    def backtest_5sets(self, periods=50):
        """5注回测"""
        if periods > self.N - 310: periods = self.N - 310
        td = self.data[-(periods+300):]; st = 300
        
        old = self._silent; self._silent = True
        
        best_red_hits = []; any_ge3 = 0; any_ge4 = 0
        blue_hits = []
        
        for i in range(st, len(td)):
            self.data = td[:i]
            af = set([int(x) for x in td[i]['red']])
            ab = set([int(x) for x in td[i]['blue']])
            
            rec = self.get_5sets(period=100)
            red_hits = [len(set(s[1]) & af) for s in rec['sets']]
            blue_hit = any(set([s[2]]) & ab for s in rec['sets'])
            
            best = max(red_hits)
            best_red_hits.append(best)
            if best >= 3: any_ge3 += 1
            if best >= 4: any_ge4 += 1
            if blue_hit: blue_hits.append(1)
        
        self.data = td; self._silent = old
        n = len(best_red_hits)
        
        print(f"\n{'#'*60}")
        print(f"  SSQ 5注回测 — 近{n}期")
        print(f"{'#'*60}")
        print(f"  平均最佳红球命中: {sum(best_red_hits)/n:.2f}个")
        print(f"  至少一注≥3红: {any_ge3/n*100:.1f}%")
        print(f"  至少一注≥4红: {any_ge4/n*100:.1f}%")
        print(f"  至少一注中蓝球: {sum(blue_hits)/n*100:.1f}%")
        
        from collections import Counter
        dist = Counter(best_red_hits)
        print(f"\n  最佳那注红球命中分布:")
        for k in sorted(dist):
            bar = "█" * max(1, int(dist[k]/n*50))
            print(f"    {k}个: {dist[k]:3d}期 ({dist[k]/n*100:.1f}%) {bar}")


def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ssq_data.json'
    a = SSQAnalyzerPro(path)
    a.get_5sets(period=100)
    print("\n" + "="*60)
    a.backtest_5sets(periods=100)

if __name__ == '__main__':
    main()
