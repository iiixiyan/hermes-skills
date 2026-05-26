# 腾讯文档 Skill — Hermes 安装说明

## 安装方式

此 skill 从官方 zip 包安装：https://cdn.addon.tencentsuite.com/static/tencent-docs.zip

```bash
curl -sLO "https://cdn.addon.tencentsuite.com/static/tencent-docs.zip"
unzip tencent-docs.zip -d ~/.hermes/skills/tencent-docs/
```

## 环境变量

在 `~/.hermes/.env` 中设置：

```
TENCENT_DOCS_TOKEN=<your_token>
```

## 关于 setup.sh

此 skill 自带的 `setup.sh` 是为"龙虾"(Lobster)平台的 mcporter MCP 客户端设计的，**不适用于 Hermes**。Hermes 直接通过 SKILL.md 和 references 中的文档提供能力，无需运行 setup.sh。

## 支持的文档类型

| 类型 | doc_type | 说明 |
|------|----------|------|
| 文档（MDX） | smartcanvas | ⭐⭐⭐ 首选，排版美观 |
| Excel 表格 | sheet | ⭐⭐⭐ 数据表格 |
| 幻灯片 | slide | ⭐⭐⭐ 演示文稿 |
| 思维导图 | mind | ⭐⭐⭐ 知识图谱 |
| 流程图 | flowchart | ⭐⭐⭐ 流程展示 |
| Word 文档 | doc | ⭐⭐ 传统格式 |
| 收集表 | form | ⭐⭐ 表单收集 |
| 智能表格 | smartsheet | ⭐⭐⭐ 高级结构化表格 |
| HTML 演示 | smartpage | ⭐⭐⭐ 网页演示 |

## Token 来源

从 https://docs.qq.com/scenario/open-claw.html 页面登录 QQ/微信获取 Token。
