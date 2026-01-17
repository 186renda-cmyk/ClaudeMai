import urllib.request
import json
import xml.etree.ElementTree as ET
import os

# ================= 配置区域 =================
# 百度站长平台提供的 API 接口地址
API_URL = "http://data.zz.baidu.com/urls?site=https://claudemai.top&token=MkpV4it8Aq1PaVbS"
SITEMAP_FILE = "sitemap.xml"
# ===========================================

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

def submit_to_baidu():
    # 动态获取 URL 列表
    url_list = get_urls_from_sitemap()
    
    if not url_list:
        print("❌ URL 列表为空，停止提交")
        return

    print(f"🚀 正在向百度搜索资源平台提交 {len(url_list)} 个 URL...")
    
    # 准备数据：每行一个 URL
    data = '\n'.join(url_list).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            API_URL, 
            data=data, 
            headers={
                'Content-Type': 'text/plain',
                'User-Agent': 'curl/7.12.1',
                'Host': 'data.zz.baidu.com'
            }
        )

        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            result = response.read().decode('utf-8')
            result_json = json.loads(result)

            if status_code == 200:
                print(f"✅ 提交成功!")
                print(f"   - 成功推送数量: {result_json.get('success', 0)}")
                print(f"   - 当天剩余额度: {result_json.get('remain', '未知')}")
                if 'not_same_site' in result_json:
                    print(f"   ⚠️ 注意: 有 {len(result_json['not_same_site'])} 个链接非本站链接")
                if 'not_valid' in result_json:
                    print(f"   ⚠️ 注意: 有 {len(result_json['not_valid'])} 个链接不合法")
                
                print("--------------------------------")
                for url in url_list:
                    print(f"  - {url}")
                print("--------------------------------")
            else:
                print(f"⚠️ 提交可能遇到问题。状态码: {status_code}")
                print(result)

    except urllib.error.HTTPError as e:
        print(f"❌ HTTP 错误: {e.code} {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ 发生未知错误: {str(e)}")

if __name__ == "__main__":
    submit_to_baidu()
