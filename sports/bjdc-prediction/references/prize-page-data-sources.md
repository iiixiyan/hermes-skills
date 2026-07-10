# 北单赛果数据源 — Prize Page 采集指南

## 数据源优先级

### 🥇 okooko 北单开奖页（首选）
```
URL: https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo={期号}
参数说明:
  - LotteryType=WDL → 让球胜平负（北单主彩种）
  - LotteryType=Score → 比分
  - LotteryType=TotalGoals → 总进球
  - LotteryType=OverUnder → 上下盘单双
  - LotteryType=HalfFull → 半全场
  - LotteryNo={5位数字期号} 如26067

采集方式:
  curl -s "https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo=26067" \
    -H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36' \
    -H 'Referer: https://www.okooo.com/' | iconv -f GBK -t UTF-8//IGNORE

HTML解析:
  - 每场比赛在 <tr> 中，含序号、主队(让球)、客队、比分(含半场)、赛果(主/平/客)、SP
  - 赛果编码：主=让胜 ✅  平=让平 ➖  客=让负 ❌
  - SP值在 <span class="gray9"> 中
```

### 🥈 59itou Prize API（备用）
```
URL: https://apic.jindianle.com/api/match/prizeList?platform=koudai_mobile&_prt=https&ver=20180101000000&lotteryId=45
采集方式:
  curl -s "https://apic.jindianle.com/api/match/prizeList?platform=koudai_mobile&_prt=https&ver=20180101000000&lotteryId=45" \
    -H 'User-Agent: Mozilla/5.0' -H 'Referer: https://kt.59itou.com/'

响应结构:
  d.data.{日期(yyyy-MM-dd)}.{场次ID} = {homeTeam, guestTeam, fullScore, halfScore, handicap, spfPrize, leagueName}

注意事项:
  - 按销售日期(date_key)分组，非比赛日期
  - 晚场比赛(22:00~06:00)的赛果可能出现在次日date_key下
  - 部分日期的赛果数据可能为空（未发布或延迟）
  - 北单lotteryId=45，竞足lotteryId=90
```

### 🥉 新浪API（仅竞足，不适用于北单）
```
竞足赛果: https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=jczqMatches&gameTypes=spf&date=YYYY-MM-DD&isAll=1&dpc=1
注意: 只含竞足(lotteryId=90)，不含北单(lotteryId=45)数据
```

## 期号 ↔ 销售日期对照

北单期号（如26067）对应的是销售日期，非比赛日期。同一期号可能覆盖多个比赛日（22:00~次日06:00的晚场）。

常用期号范围（2026年6月）：
- 26060~26068 为6月中下旬北单期号
- 通过okoko页面的 `<a class="changeNav">` 链接可获取相邻期号

## 复盘工作流（推荐）

```
1. 从 ~/.hermes/predictions/beidan/{日期}.md 读取预测
2. 确定预测对应的是哪个期号（根据预测生成日期反查）
3. 用okoko采集对应期号的全部赛果
4. 逐场对比预测 vs 实际
5. 计算：方向偏重命中率、双选覆盖命中率、按联赛分组统计
```

## 已知问题

- okoko返回GBK编码，需iconv转UTF-8
- 59itou prize API对近期日期返回空数据（赛果未发布）
- 晚场比赛日期归属：22:00后开赛的视为次日的比赛（因彩票销售日分组）
- **⚡ okokoo prize page 可能出现部分场次结果空白** — 同一期号中，较早场次(23:55~02:40)有赛果，较晚场次(02:55~06:00)仍空白。即使比赛已结束15+小时也可能未更新。这是因为prize page在一次生成后不动态更新，后续发布的赛果需要重新请求页面。**复盘时若发现部分场次空白，应重试采集（间隔数小时后再次请求同一URL），或换用59itou备用API补充**
