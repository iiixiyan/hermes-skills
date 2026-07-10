#!/usr/bin/env python3
"""
微信公众号草稿箱推送脚本 — 直接推送 gzh-design 排好的 HTML。
用法：
  python3 scripts/publish_draft.py <排版.html> [封面图.png]
  
依赖：
  pip install requests Pillow

环境变量：
  WECHAT_APPID    微信公众号 AppID
  WECHAT_APPSECRET    微信公众号 AppSecret
"""
import requests, json, os, sys
from pathlib import Path

APPID = os.environ.get("WECHAT_APPID")
APPSECRET = os.environ.get("WECHAT_APPSECRET")

if not APPID or not APPSECRET:
    print("❌ 请设置环境变量 WECHAT_APPID 和 WECHAT_APPSECRET")
    print("   在 ~/.hermes/.env 中添加：")
    print("   WECHAT_APPID=你的AppID")
    print("   WECHAT_APPSECRET=你的AppSecret")
    sys.exit(1)

def get_token():
    resp = requests.get(
        f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}",
        timeout=10
    )
    result = resp.json()
    if "access_token" not in result:
        print(f"❌ Token 获取失败: {result}")
        errcodes = {40164: "IP 不在白名单，登录 mp.weixin.qq.com → 设置 → IP白名单 添加服务器IP", 40125: "AppSecret 错误，检查是否完整（32位）"}
        print(f"   {errcodes.get(result.get('errcode'), '')}")
        sys.exit(1)
    return result["access_token"]

def upload_cover(token, cover_path):
    if not os.path.exists(cover_path):
        print("   ⚠️ 封面图不存在，跳过")
        return ""
    print("   🖼️ 上传封面图...")
    with open(cover_path, "rb") as f:
        resp = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
            files={"media": f},
            timeout=30
        )
    result = resp.json()
    media_id = result.get("media_id", "")
    if media_id:
        print(f"   ✅ 封面上传成功")
    else:
        print(f"   ⚠️ 封面上传失败: {result}")
    return media_id

def create_draft(token, html_content, thumb_media_id, title, digest, author):
    draft_data = {
        "articles": [{
            "title": title,
            "content": html_content,
            "author": author,
            "digest": digest,
            "thumb_media_id": thumb_media_id,
            "show_cover_pic": 1 if thumb_media_id else 0,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    json_data = json.dumps(draft_data, ensure_ascii=False).encode("utf-8")
    resp = requests.post(url, data=json_data, timeout=30)
    return resp.json()

def main():
    html_path = sys.argv[1] if len(sys.argv) > 1 else ""
    cover_path = sys.argv[2] if len(sys.argv) > 2 else ""
    
    if not html_path:
        print("❌ 请指定排版 HTML 文件路径")
        print("   用法: python3 publish_draft.py <排版.html> [封面图.png]")
        sys.exit(1)
    
    if not os.path.exists(html_path):
        print(f"❌ HTML 文件不存在: {html_path}")
        sys.exit(1)
    
    # 读取 HTML
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    print(f"📄 读取 HTML: {len(html_content)} 字符")
    
    # 获取 token
    print("📡 获取 access_token...")
    token = get_token()
    print("✅ 获取成功")
    
    # 上传封面
    thumb_media_id = upload_cover(token, cover_path)
    
    # 提取标题和摘要
    title = os.path.basename(html_path).split("_排版")[0].replace("-", " ").title()
    digest = ""
    
    # 作者名
    author = os.environ.get("WECHAT_AUTHOR", "")
    
    # 创建草稿
    print("📤 创建草稿...")
    result = create_draft(token, html_content, thumb_media_id, title, digest, author)
    
    if result.get("media_id"):
        print(f"\n✅ 发布成功！")
        print(f"📌 草稿 ID: {result['media_id']}")
        print(f"🔗 登录 mp.weixin.qq.com → 草稿箱 查看并发布")
    else:
        print(f"\n❌ 发布失败: {result}")

if __name__ == "__main__":
    main()
