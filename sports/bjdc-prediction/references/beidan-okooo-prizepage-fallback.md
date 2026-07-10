# okoko Prize Page 兜底采集指南

## 场景
59itou prize page (`/883/danchang/prize/`) 某批次（如126070）尚未发布时，使用okooo兜底获取北单赛果。

## 批次编号映射

| 系统 | 格式 | 示例 |
|:----|:----|:----|
| 59itou | 1260xx | 126069, 126070 |
| okoko | 260xx | 26069, 26070 |

**规则**：后两位数字一致。59itou 126069 = okoko 26069。

## 采集命令

```bash
curl -s "https://vxbf.okooo.com/kaijiang/sport.php?LotteryType=WDL&LotteryNo=26069" \
  -H 'User-Agent: Mozilla/5.0 (Linux; Android 14)' \
  2>/dev/null | iconv -f GBK -t UTF-8 2>/dev/null
```

## 解析方法

okooo页面使用team名称缩写（如"AC奥"、"克罗地"、"民主刚"），结果以文字标识：
- `客` = 让负（客队方向）
- `平` = 让平（走水）
- `主` = 让胜（主队方向）

## 检查可用批次

页面中 `<a class="changeNav">` 标签列表显示所有可用期号：
```python
# 从HTML提取可用期号
import re
available = re.findall(r'LotteryNo=(\d+)', html)
```

## 局限性
- team名称截断（"AC奥"、"克罗地"等），需要与预测数据模糊匹配
- 比分不直接显示，仅显示方向（主/平/客）
- 未开赛比赛显示空白结果
