# CodeFun2000 平台访问指南

> 2026-07-02 探索记录 | 用于华为OD备考辅助访问

## 平台信息

| 项目 | 值 |
|:-----|:----|
| 网址 | https://codefun2000.com |
| 框架 | Hydro v5.0.0-beta.18 |
| 登录方式 | 微信扫码（主）+ 密码登录（隐藏备用）|
| 题库覆盖 | 华为等大厂笔试真题，与华为OD备考相关 |
| 备案号 | 京ICP备2025123107号-1 |

## 登录方式

### 方案A：微信扫码（主方式）

1. 访问 `https://codefun2000.com/login`
2. 点击「WeChatLogin」按钮 → 显示微信二维码
3. 用户用手机微信扫码 → 页面自动跳转/刷新 → 登录完成

**⚠️ 已知问题（浏览器自动化中）：**

| 问题 | 表现 | 原因 |
|:----|:-----|:------|
| 二维码ticket过期 | 用户扫码后提示"无法打开" | WeChat临时ticket有效期短（~2分钟），扫码前已过期 |
| 登录回调查失败 | 扫码后页面变空白然后重刷，未登录 | 微信开放平台回调在自动化浏览器中可能失败 |
| 弹窗不响应 | 点击WeChatLogin按钮时页面无变化 | 按钮是SPA组件，有时click事件不触发 |

**自动化中的处理方法：**
1. 刷新页面获取新ticket → 下载二维码图片 → 通过微信发送给用户扫码
2. 如扫码后页面变空白 → 导航回首页检查登录状态
3. 重复获取二维码（每次刷新ticket刷新）最多2-3次

### 方案B：密码登录（隐藏备用）

该平台隐藏有密码登录表单，默认不显示。通过JavaScript激活：

```javascript
// 显示隐藏的密码登录面板
document.getElementById('pagePasswordLogin').style.display = 'block';
```

激活后的表单：
- **Username** (`uname`) — 用户名字段
- **Password** (`password`) — 密码字段
- **Remember me** — 记住登录状态复选框
- **Login** — 提交按钮

**适用场景：** 微信扫码连续失效时，改用密码登录。

## 页面结构

```
/login 页面：
├── heading "Login"
├── WeChatLogin button  — 默认选中，显示微信二维码
├── Sign Up button      — 切换到注册表单
│   ├── 用户名输入框
│   └── "下一步：显示微信二维码" 按钮
├── QR code image (#qrcode) — src指向mp.weixin.qq.com临时ticket
└── #pagePasswordLogin  (默认display:none)
    ├── Username 输入框
    ├── Password 输入框
    ├── Remember me 复选框
    └── Login 提交按钮
```

## 与华为OD备考的关联

- CodeFun2000 收录了大量华为OD笔试真题（含华为AI方向、非AI方向）
- 该平台可与 `od-study-note` skill 配合使用：登录后查看/提交华为OD真题
- 需要登录后才能查看个人提交记录、收藏题目、查看解题代码
