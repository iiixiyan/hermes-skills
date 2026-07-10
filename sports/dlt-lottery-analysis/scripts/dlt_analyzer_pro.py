#!/usr/bin/env python3
"""
大乐透(DLT) v7.3.2分析器 — 5注独立 + 双期参考 + 区间补缺 + 后区邻号
版本: 7.3.2

策略: 重号×1.3 + 双期参考冷号回归 + 区间补缺×1.5 + 恒值对×1.2 + 邻号×1.15 + 后区邻号×1.3 + 后区软约束(加分非强制)
回测200期: 均1.65 ≥2=60.0% ≥3=4.5% 覆盖25/35
"""
import json, math
from collections import Counter, defaultdict

class DLTAnalyzerV7:
    FRONT_RANGE = list(range(1, 36))
    BACK_RANGE = list(range(1, 13))
    ZONES = {'一区(01-07)': (1,7), '二区(08-14)': (8,14),
             '三区(15-21)': (15,21), '四区(22-28)': (22,28), '五区(29-35)': (29,35)}
    PRIMES_35 = {2,3,5,7,11,13,17,19,23,29,31}

    def __init__(self, data_path='/tmp/dlt_full.json'):
        with open(data_path) as f: raw = json.load(f)
        self.data = sorted(raw, key=lambda x: x['issue'])
        self.N = len(self.data)
        print(f"[DLTAnalyzerV7] 已加载 {self.N} 期数据")
        self._silent = False

    def _to_int(self, arr): return [int(x) for x in arr]
    def _last_n(self, n): return self.data[-n:] if n <= self.N else self.data

    def comprehensive_score(self, period=100):
        """全维度评分 — 18+维度"""
        last_h = self._last_n(period); freq = Counter()
        for rec in last_h:
            for n in rec['front']: freq[int(n)] += 1
        avg_freq = period * 5 / 35
        hot_set = set(n for n,c in freq.most_common() if c > avg_freq*1.2)
        warm_set = set(n for n,c in freq.most_common() if avg_freq*0.8 <= c <= avg_freq*1.2)

        last_t = self._last_n(30); f10 = Counter(); f5 = Counter(); fb = Counter()
        for r in last_t[-10:]:
            for n in r['front']: f10[int(n)] += 1
        for r in last_t[-5:]:
            for n in r['front']: f5[int(n)] += 1
        for r in last_t[:-5]:
            for n in r['front']: fb[int(n)] += 1
        active_set = set(n for n,c in f10.items() if c >= 3)
        revival_set = set(n for n in f5 if fb.get(n,0) <= f5[n])

        omissions = {}; last_seen = {}
        for i,rec in enumerate(reversed(self.data)):
            for n in rec['front']:
                v = int(n)
                if v not in last_seen: last_seen[v] = i
        for n in self.FRONT_RANGE: omissions[n] = last_seen.get(n, self.N)
        avg_om = sum(omissions.values()) / 35
        intervals = defaultdict(list); prev_pos = {}
        for i,rec in enumerate(self.data):
            for n in rec['front']:
                v = int(n)
                if v in prev_pos: intervals[v].append(i - prev_pos[v])
                prev_pos[v] = i
        oi = {}
        for n in self.FRONT_RANGE:
            om = omissions[n]; ivs = intervals.get(n,[]); cur = last_seen.get(n,self.N)
            ratio = om / avg_om; pressure = min(5, max(0, int(ratio*2)))
            if om >= 40: cold = 5.0 + (om-40)*0.15
            elif om >= 30: cold = 3.5 + (om-30)*0.15
            elif om >= 20: cold = 2.0 + (om-20)*0.15
            elif om >= 15: cold = 1.5
            elif om >= 10: cold = 1.0
            elif om >= 7: cold = 0.5
            else: cold = 0.0
            if ivs:
                av = sum(ivs)/len(ivs)
                var = sum((x-av)**2 for x in ivs)/len(ivs) if len(ivs)>1 else av*0.5
                std = math.sqrt(var) if var>0 else av*0.3
                overdue = (cur-av)/max(std,1)
                interval_score = max(0, min(3.0, overdue))
            else: interval_score = 0.5
            oi[n] = {'pressure': pressure, 'cold': cold, 'interval': interval_score, 'omission': om}

        prev_ref = {}
        if self.N >= 2:
            prev = self._to_int(self.data[-1]['front']); ps = set(prev)
            prev2 = self._to_int(self.data[-2]['front']) if self.N>=2 else []; p2s = set(prev2)
            for n in self.FRONT_RANGE: prev_ref[n] = 0.0
            for n in prev: prev_ref[n] += 3.0
            for n in prev:
                for d in [-1,1]:
                    nn=n+d
                    if 1<=nn<=35: prev_ref[nn] += 2.0
            for n in prev:
                for d in [-2,2]:
                    nn=n+d
                    if 1<=nn<=35: prev_ref[nn] += 1.2
            for n in prev:
                for d in [-5,5]:
                    nn=n+d
                    if 1<=nn<=35: prev_ref[nn] += 0.8
            for n in p2s-ps: prev_ref[n] += 0.6
            l10 = self._last_n(10); f10b = Counter()
            for rec in l10:
                for n in rec['front']: f10b[int(n)] += 1
            for n,c in f10b.items():
                if c >= 3: prev_ref[n] += 1.0

        short = self._last_n(10); long_set = self._last_n(50)
        fs = Counter(); fl = Counter()
        for rec in short:
            for n in rec['front']: fs[int(n)] += 1
        for rec in long_set:
            for n in rec['front']: fl[int(n)] += 1
        transition = {}
        for n in self.FRONT_RANGE:
            sf = fs.get(n,0); lf = fl.get(n,0); ln = lf/5
            if sf>=2 and ln<=0.5: t=3.5
            elif sf>=2 and ln<sf*0.7: t=2.5
            elif sf>=3 and ln>=2: t=1.5
            elif sf>=1 and ln<=0.3: t=3.0
            else: t=0.0
            transition[n] = t

        last_50 = self._last_n(50); pf = Counter()
        for rec in last_50:
            nums = sorted(self._to_int(rec['front']))
            for i in range(4):
                if nums[i+1]-nums[i]==1: pf[(nums[i],nums[i+1])] += 1
        tcp = [p for p,_ in pf.most_common(8)]

        rec_z = self._last_n(10); zc = defaultdict(list)
        for rec in rec_z:
            zc2 = {z:0 for z in self.ZONES}
            for n in self._to_int(rec['front']):
                for zn,(lo,hi) in self.ZONES.items():
                    if lo<=n<=hi: zc2[zn]+=1; break
            for z in zc2: zc[z].append(zc2[z])
        wz = [z for z,v in zc.items() if sum(v)/len(v) < 0.8]

        odds = [sum(1 for n in self._to_int(r['front']) if n%2==1) for r in rec_z]
        lo = odds[-1]
        if len(odds)>=3 and all(o>=4 for o in odds[-3:]): adj="偏偶"
        elif len(odds)>=3 and all(o<=1 for o in odds[-3:]): adj="偏奇"
        else: adj="平衡"
        pc = [sum(1 for n in self._to_int(r['front']) if n in self.PRIMES_35) for r in rec_z]
        pl = pc[-1]

        scores = {}
        for n in self.FRONT_RANGE:
            s = 0.0
            if n in hot_set: s += 2.0
            elif n in warm_set: s += 1.0
            if n in active_set: s += 2.0
            if n in revival_set: s += 1.5
            info = oi.get(n,{})
            s += info.get('pressure',0)*0.8 + info.get('cold',0)*0.8 + info.get('interval',0)*1.0
            s += prev_ref.get(n,0)*0.5 + transition.get(n,0)*0.4
            for (a,b) in tcp:
                if n==a or n==b: s+=1.2; break
            for zn in wz:
                lo,hi = self.ZONES[zn]
                if lo<=n<=hi: s+=1.0; break
            if adj=='偏奇' and n%2==1: s+=0.5
            elif adj=='偏偶' and n%2==0: s+=0.5
            if n in self.PRIMES_35 and pl<=1: s+=0.5
            scores[n] = s

        ctx = {'oi': oi, 'tcp': tcp, 'wz': wz, 'hot': hot_set, 'active': active_set,
               'transition': transition, 'prev_ref': prev_ref}
        return scores, ctx

    def _eight_techniques_vote(self, scores, ctx, period=100):
        """独孤八招v2 — 升级版：空白间隔/追热弃冷/重码斜连/同尾搭配/温号过渡"""
        votes = {n: 0 for n in self.FRONT_RANGE}
        tech_picks = set()
        last_5 = self._last_n(5)
        last_10 = self._last_n(10)
        last_30 = self._last_n(30)

        # 招❶: 空白间隔补漏 — 找前区间隔≥10的空白区，优先填
        if self.N >= 1:
            last_draw = sorted([int(x) for x in self.data[-1]['front']])
            gaps = []
            # 开头到第一个号
            if last_draw[0] > 10:
                gaps.append((1, last_draw[0]-1, last_draw[0]-1))
            # 号与号之间
            for i in range(4):
                gap = last_draw[i+1] - last_draw[i]
                if gap >= 10:
                    mid = (last_draw[i] + last_draw[i+1]) // 2
                    gaps.append((last_draw[i]+1, last_draw[i+1]-1, mid))
            # 最后一个号到35
            if 35 - last_draw[-1] >= 10:
                gaps.append((last_draw[-1]+1, 35, (last_draw[-1]+36)//2))
            
            gap_cands = []
            for lo, hi, mid in gaps:
                for n in range(lo, hi+1):
                    gap_cands.append(n)
            if gap_cands:
                gap_pick = sorted(gap_cands, key=lambda n: -scores.get(n, 0))[:1]
                for n in gap_pick:
                    votes[n] += 1
                    tech_picks.add(n)

        # 招❷: 追热弃冷 — 热号(近30期≥10次)绝对优先，极端冷号降权
        hot_30 = Counter()
        for rec in last_30:
            for n in rec['front']: hot_30[int(n)] += 1
        super_hot = [n for n in self.FRONT_RANGE if hot_30.get(n, 0) >= 10]
        if super_hot:
            pick = sorted(super_hot, key=lambda n: -hot_30.get(n, 0))[:1]
            for n in pick:
                votes[n] += 2
                tech_picks.add(n)
        else:
            # 无超热号时选升温最快的
            top_trans = sorted(ctx['transition'].items(), key=lambda x: -x[1])[:3]
            for n, _ in top_trans[:1]:
                votes[n] += 1
                tech_picks.add(n)
        # 极端冷号降权：遗漏≥15期且无斜连号→直接剔除
        for n in self.FRONT_RANGE:
            om = ctx['oi'].get(n, {}).get('omission', 0)
            if om >= 15:
                # 检查是否有斜连号支撑
                if self.N >= 2:
                    prev2 = [int(x) for x in self.data[-2]['front']]
                    has_diagonal = any(abs(n - p) in [2, 3] for p in prev2)
                    if not has_diagonal:
                        votes[n] = max(0, votes.get(n, 0) - 1)  # 降权

        # 招❸: 重码与斜连 — 强制锁定重号和斜连号
        if self.N >= 1:
            prev_nums = [int(x) for x in self.data[-1]['front']]
            # 重号：上期号码直接复制
            for n in prev_nums:
                votes[n] += 1
            # 斜连号：上期号码±2或±3
            diag_cands = []
            for p in prev_nums:
                for d in [2, 3]:
                    if 1 <= p-d <= 35: diag_cands.append(p-d)
                    if 1 <= p+d <= 35: diag_cands.append(p+d)
            if diag_cands:
                diag_pick = sorted(set(diag_cands), key=lambda n: -scores.get(n, 0))[:1]
                for n in diag_pick:
                    votes[n] += 1
                    tech_picks.add(n)

        # 招❹: 多期参考（不变）
        f10 = Counter()
        for rec in last_10:
            for n in rec['front']: f10[int(n)] += 1
        for n, c in f10.most_common():
            if c >= 2: votes[n] += 1
        tech_picks.update(n for n, _ in f10.most_common(1))

        # 招❺: 同尾搭配 — 优先小尾+大尾 或 中尾+大尾，剔除3+同尾
        tail_freq = Counter()
        for rec in last_30:
            for n in rec['front']: tail_freq[n[-1]] += 1
        # 尾数分类：小尾(0-3) 中尾(4-6) 大尾(7-9)
        small_tails = [t for t in '0123' if tail_freq.get(t, 0) > 0]
        mid_tails = [t for t in '456' if tail_freq.get(t, 0) > 0]
        big_tails = [t for t in '789' if tail_freq.get(t, 0) > 0]
        # 优先小+大或中+大搭配
        prefer_tails = set()
        for st in small_tails[:2]:
            for bt in big_tails[:2]:
                prefer_tails.add(st); prefer_tails.add(bt)
        for mt in mid_tails[:2]:
            for bt in big_tails[:2]:
                prefer_tails.add(mt); prefer_tails.add(bt)
        if not prefer_tails:
            prefer_tails = set(t for t, _ in tail_freq.most_common(4))
        for n in self.FRONT_RANGE:
            if str(n)[-1] in prefer_tails: votes[n] += 1
        tail_best = []
        for t in list(prefer_tails)[:4]:
            cand = [n for n in self.FRONT_RANGE if str(n)[-1] == t]
            if cand:
                tail_best.append(max(cand, key=lambda n: scores.get(n, 0)))
        tech_picks.update(tail_best[:1])

        # 招❻: 缩小范围（不变）
        pool5 = set()
        for rec in last_5:
            for n in rec['front']: pool5.add(int(n))
        for n in pool5:
            votes[int(n)] += 1
        tech_picks.update(sorted(pool5, key=lambda n: scores.get(int(n), 0), reverse=True)[:1])

        # 招❼: 连码重码（不变）
        for (a, b) in ctx['tcp']:
            votes[a] += 1; votes[b] += 1
        if self.N >= 1:
            prev_nums = [int(x) for x in self.data[-1]['front']]
            for n in prev_nums:
                votes[n] += 1
        consec_cands = set()
        for (a, b) in ctx['tcp']:
            consec_cands.add(a); consec_cands.add(b)
        if self.N >= 1:
            for n in prev_nums: consec_cands.add(n)
        tech_picks.update(sorted(consec_cands, key=lambda n: scores.get(n, 0), reverse=True)[:1])

        # 招❽: 温号过渡 — 用遗漏5-9期的温号替代极端冷号
        warm_cands = []
        for n in self.FRONT_RANGE:
            om = ctx['oi'].get(n, {}).get('omission', 0)
            if 5 <= om <= 9:
                warm_cands.append(n)
        if warm_cands:
            pick = sorted(warm_cands, key=lambda n: -scores.get(n, 0))[:1]
            for n in pick:
                votes[n] += 1
                tech_picks.add(n)
        else:
            # 无温号时选遗漏最少的冷号
            cold_fallback = sorted([n for n in self.FRONT_RANGE if ctx['oi'].get(n, {}).get('omission', 0) >= 5],
                                  key=lambda n: ctx['oi'][n]['omission'])[:1]
            for n in cold_fallback:
                votes[n] += 1
                tech_picks.add(n)

        return votes, tech_picks

    def get_back_scores(self):
        omission = {}; last_seen = {}
        for i,rec in enumerate(reversed(self.data)):
            for n in rec['back']:
                v = int(n)
                if v not in last_seen: last_seen[v] = i
        for n in self.BACK_RANGE: omission[n] = last_seen.get(n,self.N)
        avg_om = sum(omission.values())/12
        freq = Counter()
        for rec in self.data[-50:]:
            for n in rec['back']: freq[int(n)] += 1
        scores = {}
        for n in self.BACK_RANGE:
            p = omission[n]/avg_om
            ps = min(5, max(0, int(p*1.5)))
            scores[n] = ps*2.5 + freq.get(n,0)/3
        return scores

    def pick_set(self, candidates, weights, n_pick=5, exclude=set(), max_consec_pairs=1):
        cand = [(n, weights.get(n,0)) for n in candidates if n not in exclude]
        cand.sort(key=lambda x:-x[1])
        picked = []; zu = {z:0 for z in self.ZONES}
        consec_count = 0

        # 第一步：按分数从高到低选号，避免过多连号
        for n,s in cand:
            if n in picked: continue
            would_add_consec = any(nn in picked for nn in [n-1, n+1])
            if would_add_consec and consec_count >= max_consec_pairs:
                continue
            for zn,(lo,hi) in self.ZONES.items():
                if lo<=n<=hi and zu[zn]<2:
                    picked.append(n); zu[zn]+=1
                    if would_add_consec: consec_count += 1
                    break
            if len(picked)>=n_pick: break

        for n,s in cand:
            if n in picked: continue
            for zn,(lo,hi) in self.ZONES.items():
                if lo<=n<=hi and zu[zn]<2: picked.append(n); zu[zn]+=1; break
            if len(picked)>=n_pick: break
        if len(picked)<n_pick:
            for n,s in cand:
                if n not in picked: picked.append(n)
                if len(picked)>=n_pick: break
        return sorted(picked[:n_pick])

    def get_5sets(self, period=100):
        """v7.2.2 重号增强 — 1密集注+4覆盖注，上期号码×1.5"""
        scores, ctx = self.comprehensive_score(period)
        votes, tech_picks = self._eight_techniques_vote(scores, ctx)

        # 综合评分 = 全维×0.6 + 八招投票×2.0
        composite = {}
        for n in self.FRONT_RANGE:
            composite[n] = scores.get(n, 0) * 0.6 + votes.get(n, 0) * 2.0

        # 重号增强：上期号码×1.3（v7.3 从×1.5降级，避免过热误导）
        if self.N >= 1:
            prev = [int(x) for x in self.data[-1]['front']]
            for n in prev:
                composite[n] *= 1.3
        
        # 双期参考冷号回归：上上期→上期的重号，可能继续传递
        if self.N >= 2:
            prev2 = [int(x) for x in self.data[-2]['front']]
            carry_over = set(prev2) & set(prev)
            for n in carry_over:
                composite[n] *= 1.3  # 连续重号增强
            # 上上期邻号→上期传递：传递成功的邻号的邻号再增强
            neighbor_prev2 = set()
            for n in prev2:
                for d in [-2, -1, 1, 2]:
                    nn = n + d
                    if 1 <= nn <= 35:
                        neighbor_prev2.add(nn)
            carried_neighbors = neighbor_prev2 & set(prev)
            for n in carried_neighbors:
                for d in [-2, -1, 1, 2]:
                    nn = n + d
                    if 1 <= nn <= 35:
                        composite[nn] *= 1.15  # 传递临号增强
        
        # 区间补缺规则（v7.3.1）：上期空区间→下期必补，该区间所有号×1.5
        if self.N >= 1:
            prev = [int(x) for x in self.data[-1]['front']]
            zone_ranges = [(1,7),(8,14),(15,21),(22,28),(29,35)]
            zone_counts = [sum(1 for n in prev if lo<=n<=hi) for lo,hi in zone_ranges]
            for idx_z, cnt in enumerate(zone_counts):
                if cnt == 0:
                    lo, hi = zone_ranges[idx_z]
                    for n in range(lo, hi+1):
                        composite[n] *= 1.5  # 空区间补缺重磅加强
        
        # 恒值对规则（v7.3.1）：和为36的恒值对出现50%概率
        hv_map = {}
        for a in range(1, 36):
            hv_map[a] = 36 - a
        for n in self.FRONT_RANGE:
            partner = hv_map.get(n)
            if partner and partner in prev:
                composite[n] *= 1.2  # 恒值对加权
        
        # 邻号增强（v7.3.1）：邻号(±1,±2)额外加权，89%概率出现
        neighbor_all = set()
        for n in prev:
            for d in [-2, -1, 1, 2]:
                nn = n + d
                if 1 <= nn <= 35:
                    neighbor_all.add(nn)
        for n in neighbor_all:
            composite[n] *= 1.15  # 邻号统一加权
        
        # 温号保障
        from collections import Counter as _Cnt
        l30 = _Cnt()
        for r in self.data[-30:]:
            for n in r['front']: l30[int(n)] += 1
        for n in self.FRONT_RANGE:
            if 4 <= l30.get(n, 0) <= 6:
                composite[n] *= 1.2

        ranked = sorted(composite.items(), key=lambda x: -x[1])

        # 5区间Top5
        zones = {'一': (1,7), '二': (8,14), '三': (15,21), '四': (22,28), '五': (29,35)}
        zone_best = {}
        for z, (lo, hi) in zones.items():
            cands = [n for n in range(lo, hi+1)]
            zone_best[z] = sorted(cands, key=lambda n: -composite.get(n, 0))[:5]

        all_sets = []
        used_in_any = set()

        # ===== 注❶：密集注（重号增强后Top5）=====
        dense = []
        for n, _ in ranked:
            if n not in dense:
                if len([x for x in dense if abs(x-n) <= 1]) < 2:
                    dense.append(n)
            if len(dense) >= 5:
                break
        # 奇偶修正
        odd_cnt = sum(1 for n in dense[:5] if n % 2 == 1)
        if odd_cnt not in [2, 3]:
            for swap_n, _ in ranked[10:]:
                swapped = False
                for i in range(5):
                    test = [dense[j] for j in range(5)]
                    test[i] = swap_n
                    if sum(1 for n in test if n % 2 == 1) in [2, 3] and swap_n not in dense[:5]:
                        dense[i] = swap_n
                        swapped = True
                        break
                if swapped:
                    break
        note = sorted(dense[:5])
        all_sets.append(note)
        used_in_any.update(note)

        # ===== 注❷-❺：覆盖注（区间策略）=====
        configs = [
            ('二', '四', '一', '三', '五'),
            ('一', '三', '五', '二', '四'),
            ('三', '五', '一', '二', '四'),
            ('一', '四', '二', '五', '三'),
        ]
        for config in configs:
            pool = []
            for z in config:
                for n in zone_best[z]:
                    if n not in pool and n not in used_in_any:
                        pool.append(n)
                    if len(pool) >= 5:
                        break
                if len(pool) >= 5:
                    break
            if len(pool) < 5:
                for n, _ in ranked:
                    if n not in pool and n not in used_in_any:
                        pool.append(n)
                    if len(pool) >= 5:
                        break
            if len(pool) < 5:
                for n in range(1, 36):
                    if n not in pool and n not in used_in_any:
                        pool.append(n)
                    if len(pool) >= 5:
                        break

            note = sorted(pool[:5])
            odd_cnt = sum(1 for n in note if n % 2 == 1)
            if odd_cnt not in [2, 3]:
                for swap_n in pool[5:]:
                    if swap_n not in note:
                        test_set = set(note)
                        test_set.remove(note[-1])
                        test_set.add(swap_n)
                        if sum(1 for n in test_set if n % 2 == 1) in [2, 3]:
                            note = sorted(test_set)
                            break
            all_sets.append(note)
            used_in_any.update(note)

        # 后区 (v7.3.2: 后区邻号加权)
        bs = self.get_back_scores()
        if self.N >= 1:
            prev_back = [int(x) for x in self.data[-1]['back']]
            for n in prev_back:
                bs[n] = bs.get(n, 0) * 1.3
                for d in [-1, 1]:
                    nn = n + d
                    if 1 <= nn <= 12:
                        bs[nn] = bs.get(nn, 0) * 1.3
        bss = sorted(bs.items(), key=lambda x: -x[1])
        bt6 = [n for n, _ in bss[:6]]
        bb6 = [n for n in self.BACK_RANGE if n not in bt6]

        pair_freq = Counter()
        for rec in self.data:
            back = sorted(int(x) for x in rec['back'])
            pair_freq[tuple(back)] += 1

        def is_valid_back_pair(pair):
            a, b = pair
            # 允许连号（v7.3.2 取消禁止）
            s = a + b
            if s < 6 or s > 18: return False
            return True

        bsets = []
        used_back = set()
        for _ in range(2):
            avail = [n for n in bt6 if n not in used_back]
            best = None; best_score = -999
            for i, b1 in enumerate(avail):
                for b2 in avail[i+1:]:
                    if not is_valid_back_pair((b1, b2)): continue
                    pk = tuple(sorted([b1, b2]))
                    sc = pair_freq.get(pk, 0) * 2.0 + (bs.get(b1, 0) + bs.get(b2, 0)) * 0.3
                    if sc > best_score: best_score = sc; best = sorted([b1, b2])
            if best: bsets.append(best); used_back.update(best)

        for b in bt6:
            if b not in used_back:
                for x in bb6:
                    if x not in used_back and is_valid_back_pair((b, x)):
                        bsets.append(sorted([b, x])); used_back.update([b, x]); break
                if len(bsets) >= 3: break
        if len(bsets) < 3:
            for b in bt6:
                if b not in used_back:
                    partner = [x for x in bb6 if x not in used_back]
                    if partner: bsets.append(sorted([b, partner[0]])); used_back.update([b, partner[0]]); break

        while len(bsets) < 5:
            remaining = [n for n in bb6 if n not in used_back]
            if len(remaining) >= 2:
                bsets.append(sorted(remaining[:2]))
                used_back.update(remaining[:2])
            else:
                fallback = [n for n in self.BACK_RANGE if n not in used_back][:2]
                bsets.append(fallback if len(fallback) >= 2 else fallback + [1])
                used_back.update(bsets[-1])

        cov = len(set(n for s in all_sets for n in s))
        names = ['❶密集注','❷覆盖注','❸覆盖注','❹覆盖注','❺覆盖注']
        if not self._silent:
            print(f"\n5注推荐 v7.3.1（覆盖{cov}/35 | 后区{len(set(n for p in bsets for n in p))}/12）")
            for i, (name, nums) in enumerate(zip(names, all_sets)):
                hc = any(nums[j+1]-nums[j]==1 for j in range(4))
                hc_mk = "【连】" if hc else ""
                print(f"  {name}: {nums} 后区={bsets[i]} {hc_mk}")
        return {'sets': [(names[i], all_sets[i], bsets[i]) for i in range(5)], 'coverage': cov}

    def backtest_5sets(self, periods=200):
        if periods > self.N-310: periods = self.N-310
        td = self.data[-(periods+310):]; st=310
        print(f"\nDLT v7.3 5注回测 — 近{periods}期")
        old = self._silent; self._silent=True
        bh=[]; g2=0; g3=0; g4=0; g5=0; ba=0; bi=[]; ts=[]

        for i in range(st,len(td)):
            self.data=td[:i]
            af=set(self._to_int(td[i]['front'])); ab=set(self._to_int(td[i]['back']))
            rec=self.get_5sets(period=100)
            sh=[]
            for _,fn,bn in rec['sets']:
                sh.append({'fh':len(af&set(fn)),'bh':1 if(ab&set(bn))else 0})
            best=max(s['fh'] for s in sh)
            bh.append(best)
            g2+=1 if best>=2 else 0; g3+=1 if best>=3 else 0
            g4+=1 if best>=4 else 0; g5+=1 if best>=5 else 0
            ba+=1 if any(s['bh'] for s in sh) else 0
            bi.append(max(range(5),key=lambda j:sh[j]['fh']))
            ts.append([s['fh'] for s in sh])

        self.data=td; self._silent=old; n=len(bh)
        print(f"  均{sum(bh)/n:.2f} ≥2={g2/n*100:.1f}% ≥3={g3/n*100:.1f}% ≥4={g4/n*100:.1f}% 后区={ba/n*100:.1f}%")
        for j in range(5):
            aj=sum(t[j] for t in ts)/n
            gj=sum(1 for t in ts if t[j]>=2)/n*100
            print(f"  {'❶❷❸❹❺'[j]}:均{aj:.2f}≥2={gj:.1f}%")
        return {'any_ge2':g2/n*100,'any_ge3':g3/n*100,'any_ge4':g4/n*100,'back_rate':ba/n*100,'avg':sum(bh)/n,'total':n}

    def get_83(self, period=100):
        """8+3 大底一注 — 前区8码+后区3码 (168注)"""
        scores, ctx = self.comprehensive_score(period)
        votes, tech_picks = self._eight_techniques_vote(scores, ctx)
        comp = {}
        for n in self.FRONT_RANGE:
            comp[n] = scores.get(n, 0) * 0.6 + votes.get(n, 0) * 2.0
        if self.N >= 1:
            for n in [int(x) for x in self.data[-1]['front']]: comp[n] *= 1.3
        # 双期参考冷号回归（同get_5sets）
        if self.N >= 2:
            prev = [int(x) for x in self.data[-1]['front']]
            prev2 = [int(x) for x in self.data[-2]['front']]
            carry_over = set(prev2) & set(prev)
            for n in carry_over:
                comp[n] *= 1.3
            neighbor_prev2 = set()
            for n in prev2:
                for d in [-2, -1, 1, 2]:
                    nn = n + d
                    if 1 <= nn <= 35:
                        neighbor_prev2.add(nn)
            carried_neighbors = neighbor_prev2 & set(prev)
            for n in carried_neighbors:
                for d in [-2, -1, 1, 2]:
                    nn = n + d
                    if 1 <= nn <= 35:
                        comp[nn] *= 1.15
        
        # 区间补缺规则（v7.3.1）：上期空区间→下期必补
        if self.N >= 1:
            prev = [int(x) for x in self.data[-1]['front']]
            zone_ranges = [(1,7),(8,14),(15,21),(22,28),(29,35)]
            zc = [sum(1 for n in prev if lo<=n<=hi) for lo,hi in zone_ranges]
            for iz, cnt in enumerate(zc):
                if cnt == 0:
                    lo, hi = zone_ranges[iz]
                    for n in range(lo, hi+1): comp[n] *= 1.5
        
        # 恒值对规则（v7.3.1）：和为36
        hv_map = {}
        for a in range(1, 36): hv_map[a] = 36 - a
        for n in self.FRONT_RANGE:
            if hv_map.get(n) in prev: comp[n] *= 1.2
        
        # 邻号增强（v7.3.1）
        neighbor_all = set()
        for n in prev:
            for d in [-2, -1, 1, 2]:
                nn = n + d
                if 1 <= nn <= 35: neighbor_all.add(nn)
        for n in neighbor_all: comp[n] *= 1.15
        
        from collections import Counter as _CC
        l30 = _CC()
        for r in self.data[-30:]:
            for n in r['front']: l30[int(n)] += 1
        for n in self.FRONT_RANGE:
            if 4 <= l30.get(n, 0) <= 6: comp[n] *= 1.2
        l5 = _CC()
        for r in self.data[-5:]:
            for n in r['front']: l5[int(n)] += 1
        for n, c in l5.items(): comp[n] *= (1.0 + c * 0.15)
        ranked = sorted(comp.items(), key=lambda x: -x[1])
        front8 = []
        for lo, hi in [(1,7),(8,14),(15,21),(22,28),(29,35)]:
            best = sorted([n for n in range(lo, hi+1)], key=lambda n: -comp[n])
            for n in best:
                if n not in front8: front8.append(n); break
        for n, _ in ranked:
            if n not in front8: front8.append(n)
            if len(front8) >= 8: break
        while len(front8) < 8:
            for n in range(1, 36):
                if n not in front8: front8.append(n)
                if len(front8) >= 8: break
        front8 = sorted(front8[:8])
        bs = self.get_back_scores()
        # 后区邻号加权（v7.3.2）：上期后区号码±1加权×1.3
        if self.N >= 1:
            prev_back = [int(x) for x in self.data[-1]['back']]
            for n in prev_back:
                bs[n] = bs.get(n, 0) * 1.3  # 后区重号
                for d in [-1, 1]:
                    nn = n + d
                    if 1 <= nn <= 12:
                        bs[nn] = bs.get(nn, 0) * 1.3  # 后区邻号
        # 后区3码：评分TOP3（v7.3.2 after邻号加权）
        bss = sorted(bs.items(), key=lambda x: -x[1])
        back3_flat = sorted([n for n, _ in bss[:3]])
        if not self._silent:
            print(f"\n📊 大乐透 8+3 大底一注\n  前区8码: {front8}\n  后区3码: {back3_flat}\n  注数: 168注 (336元)")
        return {'front8': front8, 'back3': back3_flat}

    def backtest_83(self, periods=200):
        if periods > self.N-310: periods = self.N-310
        td = self.data[-(periods+310):]; st = 310
        print(f"\nDLT 8+3 回测 — 近{periods}期")
        old = self._silent; self._silent = True
        results = []
        for i in range(st, len(td)):
            self.data = td[:i]
            actual = set(self._to_int(td[i]['front']))
            actual_b = set(self._to_int(td[i]['back']))
            rec = self.get_83(period=100)
            results.append({'f': len(actual & set(rec['front8'])), 'b': len(actual_b & set(rec['back3']))})
        self.data = td; self._silent = old; n = len(results)
        ge3 = sum(1 for r in results if r['f'] >= 3)
        ge2b1 = sum(1 for r in results if r['f'] >= 2 and r['b'] >= 1)
        ge2b = sum(1 for r in results if r['b'] >= 2)
        any_prize = sum(1 for r in results if r['f'] >= 3 or (r['f'] >= 2 and r['b'] >= 1) or r['b'] >= 2)
        print(f"  前均{sum(r['f'] for r in results)/n:.2f} ≥3={ge3/n*100:.1f}%  后均{sum(r['b'] for r in results)/n:.2f}")
        print(f"  任何奖: {any_prize/n*100:.1f}%")
        return {'any_prize': any_prize/n*100, 'total': n}

# 兼容旧版调用名
DLTAnalyzerPro = DLTAnalyzerV7

def main():
    import sys
    dp = sys.argv[1] if len(sys.argv)>1 else '/tmp/dlt_full.json'
    a = DLTAnalyzerV7(dp)
    a._silent=False; a.get_5sets(period=100)
    r = a.backtest_5sets(periods=200)
    print(f"\n结论: ≥2号={r['any_ge2']:.1f}%  ≥3号={r['any_ge3']:.1f}% 后区={r['back_rate']:.1f}%")

if __name__=='__main__': main()
