# okoko开奖页赛果查询指南

> 唯一权威赛果数据源。2026-06-24验证：新浪API footballMatchDetail和竞彩官方API method=result均有延迟/不完整问题。

## URL格式

```
https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo={SALE_DATE}
```

- `LotteryNo` = **销售日期**（不是比赛日期！）
- 凌晨比赛(<10:00 CST)归入前一个销售日

## 调用模板

```bash
curl -s "https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo=2026-06-23" \
  -H 'User-Agent: Mozilla/5.0' -H 'Referer: https://www.okooo.com/' \
  | iconv -f GBK -t UTF-8//IGNORE 2>/dev/null
```

## 解码

返回GBK编码HTML，必须用 `iconv -f GBK -t UTF-8//IGNORE` 转码。

## HTML结构

赛果在 `<td>` 表格中，字段顺序：

| 列 | 内容 | 示例 |
|:--:|:-----|:-----|
| 1 | 编号(前缀=星期) | 045(周二#45) |
| 2 | 主队 | 葡萄牙 |
| 3 | VS | VS |
| 4 | 客队 | 乌兹别 |
| 5 | 比分+半场 | 5:0半场3:0 |
| 6 | SP | 5:015.00 |

编号前缀含义：1=周一 2=周二 3=周三 4=周四 5=周五 6=周六 7=周日

## Python解析

```python
from html.parser import HTMLParser
import subprocess

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td=False;self.td_data='';self.row=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='td':self.in_td=True;self.td_data=''
        if tag=='tr':self.row=[]
    def handle_endtag(self,tag):
        if tag=='td'and self.in_td:
            self.row.append(self.td_data.strip())
            self.in_td=False
        if tag=='tr'and self.row and any(c.strip()for c in self.row):
            self.rows.append(list(self.row));self.row=[]
    def handle_data(self,data):
        if self.in_td:self.td_data+=data

cmd = f"curl -s 'https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=SportteryScore&LotteryNo=2026-06-23' -H 'User-Agent: Mozilla/5.0' -H 'Referer: https://www.okooo.com/' | iconv -f GBK -t UTF-8//IGNORE 2>/dev/null"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
parser = P(); parser.feed(result.stdout)
for r in parser.rows:
    print('|'.join(r))
```

## 更新速度

- 比赛结束后约1-2小时更新
- 先出比分，再出SP值

## 其他数据源（不可靠）

| 数据源 | 问题 |
|:-------|:-----|
| 新浪API footballMatchDetail score1/score2 | 比赛刚结束时可能返回不完整数据；只能做参考，最终以okooo为准 |
| 竞彩官方API method=result | 延迟1-4小时仍显示"待开奖"，sectionsNo999为空 |

## 实战排错流程

1. **先查okooo** —— 用正确销售日期
2. 如果okooo没有/为空 —— 等1-2小时后重试
3. 如果急需 —— 新浪API footballMatchDetail score1/score2可做临时参考，但标记"okooo未确认"  
