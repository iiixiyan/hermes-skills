# 数据源对比速查（Data Source Comparison）

> 2026-06-16 对六个数据源的实际探查和对比结果。
> 用途：当某个数据源不可用时，快速判断启用哪个降级方案。

## 数据源总览

| 数据源 | 接口类型 | 需要浏览器? | 速率 | 编码 | 防盗链 |
|:-------|:---------|:-----------|:-----|:-----|:-------|
| 🥇 新浪API | REST JSON | ❌ | ~150ms/请求 | UTF-8 纯JSON | 无（直连OK） |
| 🥇 竞彩官方API | REST JSON | ❌ | ~200ms/请求 | UTF-8 纯JSON | 要求 Android UA + Referer |
| 🥇 59itou API(apic.jindianle.com) | REST JSON | ❌ | ~100ms/请求 | UTF-8 纯JSON | 无（直连OK） |
| 🥈 59itou.com(浏览器) | SSR/Vant UI | ✅ Chromium | ~10s/场 | UTF-8 | 反爬\"嗨！欢迎到店\"页面 |
| 🥉 okooo.com | API+HTML | ❌ curl即可 | ~500ms/请求 | GBK → UTF-8转码 | 阿里云WAF(需UA+Referer) |
| 🥉 sports-skills CLI | CLI脚本 | ❌ | 超时20s+ | — | 超时不稳定 |
| 🏅 Xiaohongshu SSR | SSR嵌入 | ✅ Chromium | ~8s/页 | UTF-8 | 无API，数据在window.__SETUP_SERVER_STATE__ |

## 各数据源能提供什么

### 🥇 新浪API（推荐首选 — 竞足）
```
接口: mix.lottery.sina.com.cn/gateway/index/entry
参数: format=json&cat1=<接口名>&<其他参数>

可用接口:
- jczqMatches          → 比赛列表+SPF/RQSPF/BF+赛程+赛果+比分+开奖SP
- footballMatchOddsEuro → 53家公司欧赔初赔+即赔（可计算百家平均+升降家数）
- footballMatchOddsAsia → 17家公司亚盘初盘+即盘（可统计升降盘+高/低水家数）
- footballMatchDetail   → 比赛详情（FIFA排名、天气、轮次、阶段、是否中立）
- footballMatchOddsEuroChange → 欧赔走势图数据（时间序列）

优点: 纯净JSON，一次性可取53家公司欧赔，竞足数据最全
缺点: 参数名(__call__/__verno__/__version__)尚未完全探查
      北单数据不可用（仅竞足lotteryId=90）
```

### 🥇 竞彩官方API（推荐 — 赛果+SPF）
```
接口: webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry
参数: method=concern(赛程+SPF) / method=result(赛果+比分)
      matchBeginDate/matchEndDate(日期范围批量，赛果查询专用)
      pageNo/pageSize(分页)

优点: 官方数据，日期范围批量可一次取多天赛果
      支持按队名维度过滤赛果
返回: sectionsNo999(全场比分), sectionsNo1(半场比分)
      h/d/a(主胜/平局/客胜SP), matchStatus(完赛/延期等)
      matchId(竞彩官方matchId)
缺点: 需 Android UA + Referer 头
      matchId不与59itou matchId同体系（需用户额外映射）
```

### 🥇 59itou API（推荐 — FIFA排名+SP+让球数）
```
接口: apic.jindianle.com/gateway/...
可用功能:
- selectlist → 球队列表+FIFA排名（直取FIFA排名，全量球队）
- /jczq/prize/ → 竞足开奖结果（赛果+SP+让球SP）
- /danchang/prize/ → 北单开奖结果

优点: 速度最快(~100ms)，无防盗链
缺点: 接口URL未完全文档化
      不提供欧赔/亚盘数据
```

### 🥈 59itou.com 浏览器（兜底 — 阵容/伤停/H2H/战绩明细）
```
URL: kt.59itou.com/{prefix}/match3/?matchid=X&lotteryId=90&lottery_style=jczq
可用Tab: 阵容/战绩/欧指/亚指/排名/盈亏 (6Tab)
不能提供的: 无（全覆盖，但需浏览器）

已知问题:
- 反爬\"嗨！欢迎到店\"页面（仅替换title，DOM数据通常仍可提取）
- 前缀负载均衡（需循环尝试：379→37→175→378→456→784→454→937）
- SSL证书不匹配(*.honghuoshop.com) 需 `--ignore-certificate-errors`
- 竞足/北单不可混用（lotteryId: 90 vs 45）
- 赛后亚指Tab仅在≤24h内可用
```

### 🥉 okooo.com（降级 — 赛果查询）
```
接口: vxbf.okooo.com/kaijiang/sport.php
参数: LotteryType=SportteryScore(比分)/SportteryWDL(让球SP)/SportteryNWDL(胜负SP)
      LotteryNo=YYYY-MM-DD

优点: curl直接可用（非浏览器），赛果+SP都有
      比59itou prize page简单（无需切batch）
缺点: 阿里云WAF（需Mozilla/5.0+Referer头）
      GBK编码需转码（iconv -f GBK -t UTF-8）
      只有比分结果和SP，无赔率/欧指数据
```

### 🆕 球探体育 titan007（推荐 — 基本盘结构化数据）

```
URL: info.titan007.com/analysis/{schedule_id}cn.htm
入口: live.titan007.com/oldIndexall.aspx（找到比赛行→点击"析"）
类型: SSR分析页，浏览器导航获取
速率: ~3s/页
编码: GB2312（浏览器自动处理）
防盗链: 无（浏览器直连OK）

可提供数据:
- 杯赛积分排名（分组完整排名表+积分+净胜球）
- 数据对比（近N场胜率/场均进球/场均角球/场均黄牌，主客分流）
- 阵容情况（球员名+缺阵原因，结构化表格）
- 球员上一场出场评分（号码/位置/首发/评分，详细到每个球员）
- 对赛往绩（H2H完整记录，含盘口/水位/胜负/让球/大小球）
- 近期战绩（每场明细，含对手/比分/半场/角球/盘口/赔率均值）
- 天气/场地信息

与天天盈球互补: titan007提供结构化量化数据，天天盈球提供散文定性分析
详见 references/titan007-data-source.md
```

### 🏅 Xiaohongshu SSR（仅供内容参考 — 非数据源）
```
URL: 小红书世界杯页面
数据存储: window.__SETUP_SERVER_STATE__['worldcup-calendar-1-13776']
特点: Ditto SSR，数据在服务器端渲染到页面
      window.__SETUP_SERVER_STATE__ 包含赛程数据
      无公共API可调用（仅事件追踪有API）
用途: 只能做赛程/赛事信息的补充参考，不能用于欧指分析
```

## 数据源选择决策树

### 竞足赛前 / 预测场景

```
开始
├─ 需要欧赔53家百家平均?           → 新浪API footballMatchOddsEuro
├─ 需要亚盘17家盘口+水位?          → 新浪API footballMatchOddsAsia
├─ 需要百家平均+升降家数?          → 新浪API footballMatchOddsEuro（自己算均值）
├─ 需要SPF赔率（赛前）?            → 新浪API jczqMatches 或 竞彩官方API method=concern
├─ 需要FIFA排名?                   → 59itou API selectlist 或 新浪API footballMatchDetail
├─ 需要阵容/阵型/身价?             → ❌ 无API → 59itou浏览器阵容Tab
├─ 需要伤停情报?                   → ❌ 无API → 59itou浏览器情报Tab+阵容Tab伤停段
├─ 需要H2H历史交锋?                → ❌ 无API → 59itou浏览器战绩Tab
└─ 需要近10场战绩明细（含对手名）? → 竞彩官方API method=result(按队名) → 59itou浏览器战绩Tab
```

### 竞足赛果 / 复盘场景

```
开始
├─ 需要赛果+比分+半全场?           → 竞彩官方API method=result(日期范围批量)
├─ 需要SPF开奖SP?                  → 新浪API jczqMatches(含开奖SP)
├─ 需要赛果（两个API都挂了）?       → okooo → 59itou prize page
└─ 需要欧指复盘数据?                → 新浪API footballMatchOddsEuro
```

### 北单场景

```
北单数据 → 全部走 59itou浏览器（北单无API替代）
  ├─ 比赛列表+matchID  → kt.59itou.com/883/danchang/
  ├─ 详情全Tab          → lotteryId=45&lottery_style=dc
  └─ 开奖结果+SP        → kt.59itou.com/danchang/prize/
```

## 关键经验

1. **新浪API vs 59itou浏览器 速度差异**：API 150ms/请求 vs 浏览器10s/场 ≈ 60倍差距
2. **新浪API的参数盲区**：`__caller__`、`__verno__`、`__version__` 参数意义未完全探明，部分请求可能因缺参数返回空
3. **竞彩官方API的matchId不通用**：竞彩官方matchId与59itou matchId是两套体系。跨源比较时需用比赛日期+对阵双方来桥接
4. **sports-skills CLI不可靠**：20s+超时，不适合作为正式数据源
5. **59itou浏览器反爬为\"有限影响\"**：标题被替换但DOM数据仍在，不必一见到\"嗨！欢迎到店\"就放弃
