"""DLT v8.0 大乐透8+3大底一注 更新到正式脚本"""
import json, sys
from collections import Counter
sys.path.insert(0, '/root/.hermes/skills/sports/dlt-lottery-analysis/scripts')
from dlt_analyzer_pro import DLTAnalyzerV7

# 读取当前脚本
with open('dlt_analyzer_pro.py') as f:
    code = f.read()

# 添加8+3方法
add_method = '''
    def get_83(self, period=100):
        """8+3 大底一注 — 前区8码+后区3码 (168注)"""
        scores, ctx = self.comprehensive_score(period)
        votes, tech_picks = self._eight_techniques_vote(scores, ctx)
        comp = {}
        for n in self.FRONT_RANGE:
            comp[n] = scores.get(n, 0) * 0.6 + votes.get(n, 0) * 2.0
        
        # 三重增强
        if self.N >= 1:
            for n in [int(x) for x in self.data[-1]['front']]:
                comp[n] *= 1.5
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
        
        # 前8号: 各区保底1号 + Top评分补满
        front8 = []
        zones = [(1,7),(8,14),(15,21),(22,28),(29,35)]
        for lo, hi in zones:
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
        
        # 后3号: Top 3
        bs = self.get_back_scores()
        b_ranked = sorted(bs.items(), key=lambda x: -x[1])
        back3 = sorted([n for n, _ in b_ranked[:3]])
        
        if not self._silent:
            print(f"\\n📊 大乐透 8+3 大底一注")
            print(f"  前区8码: {front8}")
            print(f"  后区3码: {back3}")
            print(f"  注数: 8选5×3选2 = 56×3 = 168注 (336元)")
        
        return {'front8': front8, 'back3': back3, 'composite': comp}

    def backtest_83(self, periods=200):
        """回测8+3策略"""
        if periods > self.N-310: periods = self.N-310
        td = self.data[-(periods+310):]; st = 310
        print(f"\\nDLT 8+3 回测 — 近{periods}期")
        old = self._silent; self._silent = True
        results = []
        for i in range(st, len(td)):
            self.data = td[:i]
            actual = set(self._to_int(td[i]['front']))
            actual_b = set(self._to_int(td[i]['back']))
            rec = self.get_83(period=100)
            f_hits = len(actual & set(rec['front8']))
            b_hits = len(actual_b & set(rec['back3']))
            results.append({'f': f_hits, 'b': b_hits})
        self.data = td; self._silent = old
        n = len(results)
        
        # 各奖级条件
        ge3 = sum(1 for r in results if r['f'] >= 3)
        ge2b1 = sum(1 for r in results if r['f'] >= 2 and r['b'] >= 1)
        ge1b2 = sum(1 for r in results if r['f'] >= 1 and r['b'] >= 2)
        ge2b = sum(1 for r in results if r['b'] >= 2)
        any_prize = sum(1 for r in results if r['f'] >= 3 or (r['f'] >= 2 and r['b'] >= 1) or r['b'] >= 2)
        
        print(f"  前区均{sum(r['f'] for r in results)/n:.2f} ≥3={ge3/n*100:.1f}%")
        print(f"  后区均{sum(r['b'] for r in results)/n:.2f} ≥1={sum(1 for r in results if r['b']>=1)/n*100:.1f}%")
        print(f"  任何奖(前≥3/前2+后1/后≥2): {any_prize/n*100:.1f}%")
        
        return {'any_prize': any_prize/n*100, 'ge3_front': ge3/n*100, 'total': n}
'''

# Insert before the main() function
insert_point = code.rfind('\ndef main():')
new_code = code[:insert_point] + add_method + code[insert_point:]

with open('dlt_analyzer_pro.py', 'w') as f:
    f.write(new_code)

print("8+3 methods added to dlt_analyzer_pro.py")
print("Testing...")
