# GitHub 资源下载：代理方案

## 场景
服务器无法直接连接 GitHub（`github.com` / `objects.githubusercontent.com` 超时 exit=28），
但需要下载 GitHub 上的二进制发布包或仓库代码。

## 可用代理

### ghproxy.net（已验证可用）
```bash
# 下载 GitHub Release 二进制
curl -sL "https://ghproxy.net/https://github.com/<owner>/<repo>/releases/download/<tag>/<asset>" -o <output>

# 下载 GitHub 仓库 ZIP
curl -sL "https://ghproxy.net/https://github.com/<owner>/<repo>/archive/main.zip" -o repo.zip

# 安装 pip 包
pip install "https://ghproxy.net/https://github.com/<owner>/<repo>/archive/main.zip"
# 或 pipx
pipx install "https://ghproxy.net/https://github.com/<owner>/<repo>/archive/main.zip"
```

### 已验证其他方式不可用
- 直接连接 `github.com` → 超时 exit=28
- `raw.githubusercontent.com` → 超时
- Jina Reader → 超时

## 已知限制
- 部分 CDN 域名（如 `objects.githubusercontent.com`）可能返回 404 或超时
- 大文件下载时仍有超时风险（已测试 3.4MB 二进制成功，8MB 二进制需 300s 超时配置）
- arxiv.org 等学术网站同样不可达

## 替代策略
当 ghproxy 也不可用时：
1. 尝试使用 Gitee 镜像（如 `gitee.com/mirrors/XXX`）
2. 从其他中国 CDN 服务获取
3. 告知用户需手动下载并上传至服务器
