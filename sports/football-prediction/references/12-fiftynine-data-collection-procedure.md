# 59itou.com 竞足逐场数据采集流程（v1.3）

> 本文件记录了从59itou竞彩足球页面逐场采集完整详情数据的标准化流程。
> 适用于：每日预测、定时任务前的手动采集、复盘数据准备。
> 2026-05-31 编 / v1.3 新增URL参数Tab切换+阵容Tab含伤停+国际赛排名规则

---

## ⚠️ 八维完整性铁规

**每场采集完成后、开始分析前，必须逐项确认以下8类数据均已到位。缺一不可，严禁跳过。**

| # | 数据维度 | 来源Tab | 验证内容 |
|:-:|:---------|:--------|:---------|
| 1️⃣ | **欧赔** | 欧指Tab | 百家平均(初/最新)、竞彩赔率、概率转换(%)、**指数变化段**(升/降公司数) |
| 2️⃣ | **亚盘** | 亚指Tab | 赢盘率、盘口变化(初→最新)、水位(高/低水公司数)、凯利指数 |
| 3️⃣ | **H2H历史交锋** | 战绩Tab → 两队交锋段 | 近N场比分记录（无记录则标注"暂无"） |
| 4️⃣ | **近期战绩** | 战绩Tab | 主客近10场胜负/进球、主客场拆解、等级战绩 |
| 5️⃣ | **阵容** | 阵容Tab | 首发阵型(如4-2-3-1)、首发身价、平均年龄（未出可标注"未出"） |
| 6️⃣ | **伤停/情报** | 情报Tab + 阵容Tab→预计伤停段 | 情报Tab内容（空也视为已查，标注"无"） |
| 7️⃣ | **排名** | 排名Tab | 积分榜排名、主场/客场排名、状态特征 |
| 8️⃣ | **大小球/进球分布** | 亚指Tab → 大小球子Tab | 大小球盘口(2.25/2.5/3球等)、欧指Tab总进球分布 |

### 执行规则
- 采集完成后保存数据文件，**逐项打勾确认**
- 任何一项缺失 → **不准进入分析步骤**，必须返回补齐
- 情报Tab为空是有效结果，标注"情报Tab空"即可
- ⚠️ **伤停数据可能隐藏在阵容Tab**（"预计伤停以及影响"段落），需额外提取
- ⚠️ **国际友谊赛/跨联赛比赛无联赛排名**，使用FIFA世界排名替代
- **阵容+排名** 是与欧赔/亚盘/战绩/H2H同权重的强制项

---

## 一、整体流程

```
列表页 → 展开目标日期 → 点击场次"分析" → 详情页 →
  ├── 战绩Tab（默认，含近10场/H2H/赛程/综合实力）
  ├── 欧指Tab（核心数据，30+公司初始vs最新对比）
  ├── 亚指Tab → 盘口/凯利/大小球 子Tab
  ├── 阵容Tab（首发阵型/身价 + 伤停信息）
  ├── 情报Tab（伤停信息，可能为空）
  └── 排名Tab（积分榜/主场客场排名/状态特征）
```

**铁规**：逐场串行，采完1场再采下一场，严禁并行。

---

## 二、列表页操作

### 2.1 导航到竞彩足球列表页

```javascript
// ⚠️ 站号数字（如455、223）可能变化，从列表页URL自动获取
browser_navigate(url='https://kt.59itou.com/jingcai/')
// 进入详情页后站号可从URL提取：const station = location.pathname.split('/')[1];
```

### 2.2 展开目标日期Tab

59itou的日期列表默认只展开第一个，后面的日期被折叠（`display:none`）。展开方法：

```javascript
var allSpans = document.querySelectorAll('span');
var targetSpan = null;
for(var i=0; i<allSpans.length; i++) {
  if(allSpans[i].textContent.trim() === '5-31') {  // 替换为实际日期
    targetSpan = allSpans[i];
    break;
  }
}
var dateDiv = targetSpan.closest('.matchtit');
dateDiv.click();
```

> **注意**：不能直接用 `browser_click` 点击Tab文本，必须通过 `browser_console` 执行JS `click()`。

### 2.3 获取match列表数据（可选）

```javascript
var matchlist = dateDiv.nextElementSibling;
var items = matchlist.querySelectorAll('.matchitem');
```

每个matchitem包含：
- `.matchitem_tit p:first-child` — 场次编号（7001）
- `.saishi` — 联赛
- `.team_host span` — 主队排名
- `.team span` — 队名
- `.rang0` — 不让球赔率（胜/平/负）
- `.ranggreen` — 让球赔率（胜/平/负），让球数在文本中
- `.gotoMatchbtn` — "分析"按钮

### 2.4 点击"分析"进入详情页

```javascript
var item = items[0];  // 目标场次
var btn = item.querySelector('.gotoMatchbtn');
btn.click();
```

> matchID 自动从URL中获取，不需要预知。

### 2.5 从详情页返回列表页

```javascript
browser_navigate(url='https://kt.59itou.com/455/jingcai/')
```

列表页会重新加载，5-30默认展开。直接导航比 `browser_back` 更可靠。

---

## 三、详情页数据采集

### 3.1 8Tab概览

| Tab | 采集方式 | 核心内容 | 优先级 |
|:---|:---------|:---------|:-----:|
| 战绩（默认） | innerText | 近10场/H2H/赛程/综合实力 | ⭐⭐⭐ |
| 欧指 | 切换Tab→innerText | 30+公司赔率/概率/变化/赔付 | ⭐⭐⭐ |
| 亚指 | 切换Tab→innerText | 盘口/凯利/大小球 | ⭐⭐⭐ |
| 阵容 | 切换Tab→innerText | 首发/阵型/替补+伤停 | ⭐⭐ |
| 情报 | 切换Tab→innerText | 伤停/新闻（可能为空） | ⭐⭐ |
| 排名 | 切换Tab→innerText | 积分榜/状态特征/赛季对比 | ⭐⭐ |

**统一采集方式**：`browser_console(expression='document.body.innerText')`
- ✅ 用innerText而非snapshot，避免截断（392行限制）
- ⚠️ 切换Tab后等待500-800ms再提取，确保动态内容加载完毕

### 3.2 Tab切换的两种方式

#### 方式A：JS点击Tab元素（默认方式）

```javascript
var tabs = document.querySelectorAll('[role="tab"]');
for(var i=0; i<tabs.length; i++) {
  if(tabs[i].textContent.trim() === '欧指') {
    tabs[i].click();
    break;
  }
}
// 等待500ms后提取
```

#### 方式B：URL参数直接跳转（推荐用于首次进入详情页）

**2026-06-17验证：59itou详情页URL格式为 `https://kt.59itou.com/{station}/match3/?current_tab={tab}&matchid={match_id2}&lotteryId=90`**

其中：
- `{station}` = 站号，从列表页URL的pathname自动提取（如223、455）
- `{match_id2}` = 59itou API返回的 `match_id2` 字段（如2589461、2680453）
- `lotteryId=90` = 竞足（固定）

```javascript
// 从零构建详情页URL进入（无需先加载列表页）
const station = location.pathname.split('/')[1] || '223';
const matchId2 = '2680453';  // 从59itou API获取
const tab = 'odds';  // history|odds|handicap|lineup|info|rank
window.location.href = `https://kt.59itou.com/${station}/match3/?current_tab=${tab}&matchid=${matchId2}&lotteryId=90`;
```

参数速查：

| Tab名 | current_tab值 | 用途 |
|:-----|:------------|:-----|
| 战绩 | history | 近10场/H2H/赛程/综合实力（默认） |
| 欧指 | odds | 百家平均+指数变化+各公司赔率 |
| 亚指 | handicap | 盘口+水位+升降盘统计 |
| 阵容 | lineup | 首发/阵型/替补+伤停 |
| 情报 | info | 伤停/新闻（可能为空） |
| 排名 | rank | 积分榜/状态特征 |

**特点对比**：
- 方式A（JS点击）：适合已在详情页时切换Tab
- 方式B（URL直接）：适合首次进入详情页，更可靠，且无需依赖JS事件绑定

### 3.3 战绩Tab（默认加载）

进入详情页后默认在战绩Tab，直接提取innerText。

**数据提取要点**：
- 近10场战绩：主客胜/平/负场次统计
- 主客战绩：区分主客场
- 等级战绩：对阵强队/弱队表现
- 主/客队近10场详细记录（赛事/日期/对手/比分/亚指）
- 两队交锋记录（H2H、历史比分）
- 近期赛程（过去/未来）
- 综合实力：数字对比（如 47 vs 53）

### 3.4 欧指Tab

切换到欧指Tab提取：

**核心数据段**：
- **概率转换**：`79% ↑  胜  14% ↓  平  7% ↓  负`（↑上升↓下降）
- **指数变化（关键）**：`0家升 胜 21家降 | 22家升 平 1家降 | 22家升 负 0家降`
  - 格式：`[升公司数]家 选项 [降公司数]家`
  - 这是因子4b/12/13判断的入口
- **赔付控制**：`12家控胜 15家控平 15家控负`
- **总进球分布**：近20轮0-1球/2-3球/4-6球/7+球场次统计
- **半全场**：主客半全场分布
- **常见比分**：主客20场最常出现比分及次数
- **典型指数表**：30-35家公司初始vs最新赔率（百家平均/竞彩/威廉/立博/Bet365/澳彩等）

### 3.5 亚指Tab + 子Tab

默认显示盘口（让球盘）数据：
- 亚盘赢盘率（主客近10场）
- 盘位水位升降（升/降盘公司数、高水/低水公司数）
- 盘口走势（澳彩初盘）
- **典型亚盘表**：每家公司初始盘口→最新盘口

**切换子Tab获取凯利和大小球**：

```javascript
// 子Tab是 <p> 元素，非 role="tab"
var allPs = document.querySelectorAll('p');
for(var i=0; i<allPs.length; i++) {
  if(allPs[i].textContent.trim() === '大小球') {
    allPs[i].click();
    break;
  }
}
```

**大小球子Tab**：公司名 + 大球/初盘/小球 → 大球/最新盘/小球

### 3.6 阵容Tab

```javascript
// 切换方式同上（role="tab" 或 URL参数 current_tab=lineup）
var tabs = document.querySelectorAll('[role="tab"]');
for(var i=0; i<tabs.length; i++) {
  if(tabs[i].textContent.trim() === '阵容') { tabs[i].click(); break; }
}
// 等待500ms后提取
```

阵容Tab包含：
- **阵容概览**：首发身价、平均年龄、平均身高
- **首发11人名单 + 阵型**（如4-3-3、4-4-2、3-4-2-1等）
- **替补名单**及换人时间
- **教练姓名**
- **⚠️ 伤停数据**：在"预计伤停以及影响"段落，包含球员名、身价、状态（待定/伤缺）、影响值（缺阵vs出场的胜平负记录）
- ⚠️ 比赛离得远时阵容未发布，标注"阵容未出"
- ⚠️ 国际友谊赛阵容通常在赛前1h发布

### 3.7 情报Tab

可能为空，标注"情报Tab空"即可。
**如果情报Tab为空，仍需从阵容Tab提取"预计伤停以及影响"段作为伤停数据来源。**

### 3.8 排名Tab

切换到排名Tab提取：
- **赛季排名对比**：本赛季/上赛季/前赛季三栏对照
- **战绩连续状态特征**：主客队连胜/连败/不败/不胜（历史+当前）
- **联赛特征统计**：联赛整体胜/平/负比例，主客队均进球
- **完整积分榜**：排名/队名/赛/胜/平/负/进/失/积分
- 排名可能分主客场子表

**⚠️ 国际友谊赛/杯赛无联赛排名**：苏格兰VS库拉索这类比赛，排名Tab只显示"赛事特征统计"和"赛事介绍"。使用FIFA世界排名替代（已在比赛头部标注如[世43]）。

---

## 四、数据提取映射表

| 数据项 | 来源 | 提取方式 |
|:-------|:-----|:---------|
| 竞彩赔率 | 欧指Tab→竞彩官方行 | `竞彩官方  2.96/3.02/2.17` |
| 百家平均 | 欧指Tab→百家平均行 | `百家平均  2.93/3.06/2.37` |
| 指数变化 | 欧指Tab→指数变化段 | `X家升/Y家降` |
| 赔付控制 | 欧指Tab→赔付控制段 | `N家控制胜/平/负` |
| 概率转换 | 欧指Tab→概率转换段 | `X% ↑/↓` |
| 让球数 | 列表页 `.rang0`/`.ranggreen` | `0`、`-1`、`+1`、`-2` |
| 让球赔率 | 列表页 `.ranggreen` | `胜1.52 平3.65 负5.10` |
| 盘口数据 | 亚指Tab | 初始/最新盘口+水位 |
| 大小球 | 亚指Tab→大小球子Tab | `2.25球`等 |
| 凯利 | 亚指Tab→凯利子Tab | 凯利指数+赔付率 |
| H2H | 战绩Tab→两队交锋段 | 历史比分 |
| 综合实力 | 战绩Tab→综合实力段 | 实力数值 |
| 赢盘率 | 亚指Tab | 主客近10场赢盘% |
| 联赛排名 | 排名Tab | 完整积分榜 |
| 伤停 | 阵容Tab→预计伤停段 | 球员/状态/影响 |

---

## 五、常见问题与处理

### Q1: Tab点击后数据没变化？
**原因**：JS异步加载延迟。**解决**：等待500-800ms再提取，或用URL参数跳转替代。

### Q2: 日期Tab折叠看不到比赛？
**原因**：matchlist被隐藏（display:none）。**解决**：先JS点击 .matchtit 展开。

### Q3: 欧指Tab"指数变化"段缺失？
**解决**：重新加载页面或重切Tab。该段是因子4b识别的关键数据，不可跳过。

### Q4: snapshot内容被截断？
**解决**：用 `browser_console(expression='document.body.innerText')` 替代snapshot。

### Q5: `let` 重复声明报错？
**解决**：用 `var` 或外层包 `(function(){...})()`。

### Q6: Vant UI tab点击无效？
**解决**：改用URL参数 `current_tab=handicap|odds|rank|lineup|info|history` 直接跳转。

### Q7: 情报Tab为空，没有伤停数据？
**解决**：检查阵容Tab的"预计伤停以及影响"段——伤停数据可能只在那里。

### Q8: 国际友谊赛没有排名和阵容？
**解决**：排名用FIFA世界排名（比赛头部显示）；阵容标注"未出(友谊赛赛前1h公布)"。

---

## 六、采集流程速查表

```
┌─────────────────────────┐
│  browser_navigate(列表页) │
├─────────────────────────┤
│  JS展开目标日期Tab        │  ← span→.closest('.matchtit').click()
├─────────────────────────┤
│  JS点击"分析"按钮        │  ← .gotoMatchbtn.click()
├─────────────────────────┤
│  确认进入详情页           │  ← URL含matchid & lotteryId=90
├─────────────────────────┤
│  采集战绩Tab (默认)      │
├─────────────────────────┤
│  JS切至欧指Tab+等待      │  ← [role="tab"] 或 ?current_tab=odds
├─────────────────────────┤
│  采集欧指 (含指数变化)    │
├─────────────────────────┤
│  JS切至亚指Tab+等待      │  ← 或 ?current_tab=handicap
├─────────────────────────┤
│  采集亚指 → 切换大小球子Tab│
├─────────────────────────┤
│  JS切至阵容Tab+等待      │  ← 或 ?current_tab=lineup
├─────────────────────────┤
│  提取阵容+伤停信息        │  ← "预计伤停以及影响"段
├─────────────────────────┤
│  JS切至情报Tab+等待      │  ← 确认是否为空
├─────────────────────────┤
│  JS切至排名Tab+等待      │  ← 或 ?current_tab=rank
├─────────────────────────┤
│  八维完整性确认           │  ← 缺一不可，跳过不补禁止分析
├─────────────────────────┤
│  browser_navigate(列表页) │  ← 回到列表页 → 下一场
└─────────────────────────┘
```

---

## 七、赛果数据获取（复盘用）

复盘需要获取实际赛果时，按以下优先级：

**🥇 首选：竞彩官方API（2026-06-17验证可用）**

```bash
curl -s 'https://webapi.sporttery.cn/gateway/uniform/fb/getMatchDataPageListV1.qry?method=result&pageSize=20&matchBeginDate=YYYY-MM-DD&matchEndDate=YYYY-MM-DD' \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36' \
  -H 'Referer: https://webapi.sporttery.cn/' \
  -H 'Accept: application/json, text/plain, */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Origin: https://webapi.sporttery.cn'
```

**优点**：纯净JSON（GBK或UTF-8），包含半全场比分、matchStatus（11=已完成）
**⚠️ 注意**：必须带完整5个浏览器头，缺一触发EdgeOne WAF返回HTTP 567

**🥈 备选：新浪API带dpc=1**

```bash
curl -s 'https://mix.lottery.sina.com.cn/gateway/index/entry?format=json&__caller__=wap&__version__=1.0.0&__verno__=10000&cat1=jczqMatches&gameTypes=spf&date=YYYY-MM-DD&isAll=1&dpc=1'
```

返回SP开奖+赛果，但可能有延迟（赛果数据当日无法立即获取）

**🥉 兜底：澳客(okooo)开奖结果页面**
```
URL:    https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo=YYYY-MM-DD
例:     https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo=2026-05-30
```

**注意**（踩坑记录）：
- ⚠️ 该站点使用**阿里云WAF**防护，裸curl/browser_navigate会被405拦截
- ✅ 必须加 `User-Agent: Mozilla/5.0` 和 `Referer: https://www.okooo.com/` 头
- ✅ 编码为GBK，需 `iconv -f GBK -t UTF-8` 转码
- 查询参数 `LotteryType` 可选：`SportteryScore`(比分)、`SportteryWDL`(让球胜平负)、`SportteryNWDL`(胜平负)、`SportteryTotalGoals`(总进球)、`SportteryHalfFull`(半全场)
- 返回：序号、主客队（缩写）、全场比分、半场比分、中奖SP

**备用**：`https://kt.59itou.com/jingcai/prize/`（仅当okooo不可达时）

详细流程见 `references/03-review-experience.md` §赛果查询。

---

## 八、本流程验证记录

| 验证场次 | 日期 | 状态 | 备注 |
|:---------|:----|:----:|:-----|
| 7001 冈山VS浦和 | 2026-05-31 | ✅ | 首次验证，所有Tab数据完整采集 |
| 6003 京都VS柏 | 2026-05-30 | ✅ | 验证阵容Tab含伤停、URL参数切换 |
| 6005 赫尔辛基VS玛丽港 | 2026-05-30 | ✅ | 验证亚指Tab子Tab切换、排名积分榜 |
