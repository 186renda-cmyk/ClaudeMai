import urllib.request
import json
import sys

# ================= 配置区域 =================
HOST = "claudemai.top"
KEY = "556648788f2744d0b45ccdf47d3abbb6"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
# 需要提交的 URL 列表
URL_LIST = [
    f"https://{HOST}/",
    f"https://{HOST}/legal.html"
]
# ===========================================

# IndexNow API 端点 (Bing 和 Yandex 共享数据，提交给其中一个即可)
ENDPOINT = "https://www.bing.com/indexnow"

def submit_to_indexnow():
    print(f"🚀 正在向 IndexNow 提交 {len(URL_LIST)} 个 URL...")
    
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": URL_LIST
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
                for url in URL_LIST:
                    print(f"  - {url}")
                print("--------------------------------")
            elif status_code == 202:
                print(f"✅ 请求已接受! (202 Accepted - 正在处理中)")
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
