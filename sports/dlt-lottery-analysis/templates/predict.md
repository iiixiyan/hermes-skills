# 大乐透预测模板 v8.0

## 8+3大底一注（每日预测模式）

```bash
cd ~/.hermes/skills/sports/dlt-lottery-analysis/scripts
python3 -c "
from dlt_analyzer_pro import DLTAnalyzerV7
a = DLTAnalyzerV7('/tmp/dlt_full.json')
a._silent = False
rec = a.get_83(period=100)
print(f'前区8码: {rec[\"front8\"]}')
print(f'后区3码: {rec[\"back3\"]}')
print(f'168注 (336元)')
"
```

## 5注独立模式（选号分析备用）

```bash
cd ~/.hermes/skills/sports/dlt-lottery-analysis/scripts
python3 -c "
from dlt_analyzer_pro import DLTAnalyzerV7
a = DLTAnalyzerV7('/tmp/dlt_full.json')
a._silent = False
a.get_5sets(period=100)
"
```

## 8+3回测

```bash
cd ~/.hermes/skills/sports/dlt-lottery-analysis/scripts
python3 -c "
from dlt_analyzer_pro import DLTAnalyzerV7
a = DLTAnalyzerV7('/tmp/dlt_full.json')
a.backtest_83(200)
"
```

## 下载最新数据

```bash
curl -sL --max-time 60 "https://ghproxy.net/https://raw.githubusercontent.com/yangxb919/lottery-data/main/data/dlt.json" -o /tmp/dlt_full.json
```
