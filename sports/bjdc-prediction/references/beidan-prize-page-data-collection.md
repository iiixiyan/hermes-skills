# 北单Prize Page数据采集指南

## 数据源

### 1. okooo北单赛果页（推荐）
```
URL: https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo={期号}
编码: GBK → UTF-8 (需 iconv 转换)
```

采集命令：
```bash
curl -s "https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo=26068" \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36' \
  -H 'Referer: https://www.okooo.com/' | iconv -f GBK -t UTF-8//IGNORE
```

### 2. 59itou北单API（赛前列表）
```
URL: https://apic.jindianle.com/api/match/selectlist?platform=koudai_mobile&_prt=https&ver=20180101000000&hide_more=0&single_support=2&lotteryId=45
```

## 关键发现

### 北单与竞足盘口差异
同一场比赛在北单和竞足中让球数可能完全不同：
- 雅罗vs赫尔火花: 竞足让+1，北单让0
- 玛丽港vs赫尔辛基: 竞足让+1，北单让+2

**必须从北单价盘获取让球数据，禁止用竞足盘口替代。**

### 北单期号与比赛池
- 北单26068期共24场比赛
- 包含竞足球池(1-11场) + 北单独有比赛(12-24场如冰岛超、巴西乙等)
- 所有北单让球均为整数，无半球盘

## 赛果提取
赛果文字：fontred">X where X=主/客/平
让球数据：<cite>(数字)</cite>
SP数据：gray9">数字
