import urllib.request
import json
import sys
import xml.etree.ElementTree as ET
import os

# ================= 配置区域 =================
HOST = "claudemai.top"
KEY = "556648788f2744d0b45ccdf47d3abbb6"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP_FILE = "sitemap.xml"
# ===========================================

# IndexNow API 端点 (Bing 和 Yandex 共享数据，提交给其中一个即可)
ENDPOINT = "https://www.bing.com/indexnow"

def get_urls_from_sitemap():
    url_list = []
    try:
        # 获取脚本所在目录的绝对路径，确保能找到 sitemap.xml
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sitemap_path = os.path.join(script_dir, SITEMAP_FILE)
        
        if not os.path.exists(sitemap_path):
            print(f"❌ 找不到 sitemap 文件: {sitemap_path}")
            return []
            
        tree = ET.parse(sitemap_path)
        root = tree.getroot()
        
        # 处理 namespace
        # sitemap.xml 通常有 namespace, 例如: {http://www.sitemaps.org/schemas/sitemap/0.9}
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}')[0] + '}'
            
        for url in root.findall(f'{namespace}url'):
            loc = url.find(f'{namespace}loc')
            if loc is not None and loc.text:
                url_list.append(loc.text.strip())
                
        print(f"📄 从 sitemap.xml 提取到 {len(url_list)} 个 URL")
        return url_list
    except Exception as e:
        print(f"❌ 解析 sitemap.xml 失败: {str(e)}")
        return []

def submit_to_indexnow():
    # 动态获取 URL 列表
    url_list = get_urls_from_sitemap()
    
    if not url_list:
        print("❌ URL 列表为空，停止提交")
        return

    print(f"🚀 正在向 IndexNow 提交 {len(url_list)} 个 URL...")
    
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            ENDPOINT, 
            data=data, 
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            if status_code == 200:
                print(f"✅ 提交成功! (200 OK)")
                print("--------------------------------")
                for url in url_list:
                    print(f"  - {url}")
                print("--------------------------------")
            elif status_code == 202:
                print(f"✅ 请求已接受! (202 Accepted - 正在处理中)")
                print("--------------------------------")
                for url in url_list:
                    print(f"  - {url}")
                print("--------------------------------")
            else:
                print(f"⚠️ 提交可能遇到问题。状态码: {status_code}")
                print(response.read().decode('utf-8'))

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP 错误: {e.code} {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ 发生未知错误: {str(e)}")

if __name__ == "__main__":
    submit_to_indexnow()
