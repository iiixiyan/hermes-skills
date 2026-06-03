# 北单月度复盘 Cron Prompt 模板（每月1日06:00）

## 时间
每月1日06:00 CST — 对上个月（上月1日至上月最后一天）的全部北单预测进行深度复盘。

## 前置操作
加载 `bjdc-prediction` skill（skill_view + 所有引用文件）。

## 执行流程

### 第1步：获取上月全部预测数据
用 session_search 搜索上月北单预测cron输出（job ID: 99da379ec645），分批次读取。

关键搜索词：`北单预测` `bjdc` `05月`（替换为对应月份）`cron` `晚场` `精选`

输出文件路径：`/root/.hermes/cron/output/99da379ec645/{日期}_22-*-*.md`

从每个文件中提取：
- 精选推荐场次（星级≥4的）
- 低信号/普通场次
- 放弃场次
- 信号统计数据

### 第2步：获取上月实际赛果
从北单开奖结果页 `https://kt.59itou.com/danchang/prize/` 采集实际赛果。

**批次切换方法**：页面顶部有`.prizenav p`元素（6位批次代码如126061, 126058, 126057, 126056），点击 `<p>` 元素切换批次。

**匹配ID提取（JS方法）**：
```javascript
// 提取当前批次所有比赛的matchID和结果
var all = document.querySelectorAll('a');
var result = [];
for(var i=0; i<all.length; i++){
  if(all[i].textContent.trim() === '析'){
    var parentDiv = all[i].parentElement;
    var grandparent = parentDiv ? parentDiv.parentElement : null;
    var matchId = grandparent ? grandparent.id : '';
    var spans = parentDiv.querySelectorAll('span');
    var matchNum = '';
    for(var j=0; j<spans.length; j++){
      if(spans[j].textContent.match(/周[一二三四五六日]\d+/)){
        matchNum = spans[j].textContent.trim(); break;
      }
    }
    var pTags = parentDiv.querySelectorAll('p');
    var league = '', home = '', away = '';
    var b = parentDiv.querySelector('b');
    var score = b ? b.textContent.trim() : '';
    for(var j=0; j<pTags.length; j++){
      var cls = pTags[j].className || '';
      if(cls.includes('liansai')) league = pTags[j].textContent.trim();
      else if(cls.includes('textr')) home = pTags[j].textContent.trim();
      else if(cls.includes('textl')) away = pTags[j].textContent.trim();
    }
    if(matchId) result.push({num: matchNum, id: matchId, league: league,
      home: home, score: score, away: away});
  }
}
return JSON.stringify({count: result.length, matches: result});
```

**批次覆盖**：必须遍历所有可见批次（通常4个批次，共150-200场比赛）。

**北单结果判定**：
- 从innerText中提取让球选项的SP信息（如`(-1)胜 2.96`）
- 让球数 = `(±N)` 括号内数字
- 标准比分（如`3-1`）→ 计算实际让球胜平负

### 第3步：命中率统计
对精选推荐场次（星级≥4星）做逐场对照：
- 让球方向是否命中
- 进球数预测是否命中
- 信号一致性检查

统计字段：
| 日期 | 精选数 | 方向命中 | 命中率 | 最佳信号 | 最差信号 |

### 第4步：联赛分区统计
| 联赛 | 场次 | 推荐命中 | 命中率 | 信号趋势 | 升级/降级建议 |

### 第5步：信号月度表现
| 信号 | 月度触发 | 月度准确率 | 环比(vs周度) | 操作 |

### 第6步：系统偏差诊断
识别新增的系统性偏差：
- 信号在特定条件下的失效率
- 联赛特异性变化
- 新出现的诱上/阻上案例

### 第7步：深度反向优化 skill
基于以上发现更新 bjdc-prediction skill：
1. 信号准确率表更新（月度触发次数+准确率+环比变化）
2. 联赛分级更新（固化/有效/禁用）
3. 新规则写入（偏重判定、联赛特性警告、操作规则）
4. 增量版本号（如5.0.0）
5. 更新日志行追加

### 第8步：git push 同步
```bash
cd /root/.hermes/skills
git add sports/bjdc-prediction/SKILL.md sports/bjdc-prediction/references/
git commit -m "bjdc-prediction vX.X.X: N月月度复盘
- 总体命中率X%
- 关键发现..."
git push
```

## 输出格式

### 📊 北单月度复盘（N月）
#### ① 总体覆盖统计
Cron覆盖率、总场次、精选数、放弃数。

#### ② 精选推荐命中率
每日分布+月度汇总+关键案例（✅正确/❌错误）。

#### ③ 联赛分区统计
每个联赛的月度命中率+趋势。

#### ④ 信号月度表现
环比周度数据、升降级操作。

#### ⑤ 系统偏差诊断
新增偏差+对应新增规则。

#### ⑥ Skill更新内容
文件修改列表+版本号+git commit hash。

## 参考
- `skill_view('59itou-data-fetch')` — prize page采集方法
- `skill_view('bjdc-prediction')` — 完整技能文档
- `references/11-review-insights.md` — 复盘经验库
