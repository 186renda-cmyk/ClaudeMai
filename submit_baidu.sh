#!/bin/bash

# ================= 配置区域 =================
API_URL="http://data.zz.baidu.com/urls?site=https://claudemai.top&token=MkpV4it8Aq1PaVbS"
# ===========================================

# 构建 URL 列表字符串 (换行符分隔)
URLS=$(cat <<EOF
https://claudemai.top/
https://claudemai.top/blog/
https://claudemai.top/blog/what-is-claude.html
https://claudemai.top/blog/claude-vs-chatgpt-coding.html
https://claudemai.top/blog/claude-usage-limits-guide.html
https://claudemai.top/legal.html
EOF
)

echo "🚀 正在向百度搜索资源平台提交 URL..."
echo "--------------------------------"

# 发送 POST 请求
curl -H 'Content-Type:text/plain' --data-binary "${URLS}" "${API_URL}"

echo ""
echo "--------------------------------"
echo "✅ 提交完成！(success 字段表示成功数量)"
