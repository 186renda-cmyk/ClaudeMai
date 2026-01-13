import urllib.request
import json

# ================= 配置区域 =================
# 百度站长平台提供的 API 接口地址
API_URL = "http://data.zz.baidu.com/urls?site=https://claudemai.top&token=MkpV4it8Aq1PaVbS"

# 需要提交的 URL 列表
URL_LIST = [
    "https://claudemai.top/",
    "https://claudemai.top/blog/",
    "https://claudemai.top/blog/what-is-claude.html",
    "https://claudemai.top/blog/claude-vs-chatgpt-coding.html",
    "https://claudemai.top/blog/claude-usage-limits-guide.html",
    "https://claudemai.top/legal.html"
]
# ===========================================

def submit_to_baidu():
    print(f"🚀 正在向百度搜索资源平台提交 {len(URL_LIST)} 个 URL...")
    
    # 准备数据：每行一个 URL
    data = '\n'.join(URL_LIST).encode('utf-8')
    
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
