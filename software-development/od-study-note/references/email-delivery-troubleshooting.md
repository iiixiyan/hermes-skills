# 华为OD邮件发送问题排查

## SMTP配置

- 发件人：clawgirl@163.com
- 收件人：suijiong@huawei.com
- SMTP：smtp.163.com:465（SSL）
- 密码：硬编码在 `od_daily_push.py` 的 SMTP 字典中

## 已知问题：163→huawei.com 被拦截

### 现象
- `od_daily_push.py` 运行日志显示 `✅ 邮件已发送 → suijiong@huawei.com`
- 163 SMTP 日志返回 250 OK（服务器接受转发了）
- 但用户反馈**没有收到**邮件
- 发往 163 本域（clawgirl@163.com）的测试邮件能正常收到

### 可能原因

| 原因 | 说明 | 排查方式 |
|------|------|----------|
| 华为企业邮箱网关拦截 | 163.com 的发件人 SPF/DKIM 可能不被华为信任 | 发测试邮件确认 |
| 短时间批量发送 | 一次补发 29 封可能触发频率限制 | 分批发，间隔 10秒+ |
| 进了垃圾邮件 | 华为邮箱可能将外域邮件归入垃圾箱 | 让用户检查垃圾箱 |
| 内容触发拦截 | HTML 邮件中的链接/图片/关键词触发规则 | 先发纯文本测试 |

### 排查步骤

```python
import smtplib, ssl
from email.mime.text import MIMEText

SMTP = {"host":"smtp.163.com","port":465,
        "user":"clawgirl@163.com","pass":"GM2upq3ihqWVXEG7"}

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL(SMTP["host"], SMTP["port"], context=ctx, timeout=15) as s:
    s.login(SMTP["user"], SMTP["pass"])
    
    # 测试1：极简纯文本到华为
    m1 = MIMEText("连通性测试", "plain", "utf-8")
    m1["From"] = SMTP["user"]
    m1["To"] = "suijiong@huawei.com"
    m1["Subject"] = "Hermes 连通测试"
    s.sendmail(SMTP["user"], ["suijiong@huawei.com"], m1.as_string())
    
    # 测试2：同时发往163本域作对比
    m2 = MIMEText("对比测试", "plain", "utf-8")
    m2["From"] = SMTP["user"]
    m2["To"] = "clawgirl@163.com"
    m2["Subject"] = "Hermes 对比测试"
    s.sendmail(SMTP["user"], ["clawgirl@163.com"], m2.as_string())
```

### 临时解决方案

1. 让用户检查华为邮箱的**垃圾邮件文件夹**
2. 将 clawgirl@163.com 添加到华为邮箱的白名单
3. 如果长期收不到，考虑：
   - 改用企业邮箱（如阿里企业邮、腾讯企业邮）发送
   - 通过微信发送文档链接 + 内容概览替代邮件
   - 将脚本改为通过邮件 API（如 SendCloud）发送
