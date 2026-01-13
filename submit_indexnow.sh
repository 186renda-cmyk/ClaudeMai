#!/bin/bash

# ================= 配置区域 =================
HOST="claudemai.top"
KEY="556648788f2744d0b45ccdf47d3abbb6"
KEY_LOCATION="https://${HOST}/${KEY}.txt"
# ===========================================

# 构建 JSON 数据
JSON_DATA=$(cat <<EOF
{
  "host": "${HOST}",
  "key": "${KEY}",
  "keyLocation": "${KEY_LOCATION}",
  "urlList": [
    "https://${HOST}/",
    "https://${HOST}/blog/",
    "https://${HOST}/blog/what-is-claude.html",
    "https://${HOST}/blog/claude-vs-chatgpt-coding.html",
    "https://${HOST}/blog/claude-usage-limits-guide.html",
    "https://${HOST}/legal.html"
  ]
}
EOF
)

echo "🚀 正在向 IndexNow 提交 URL..."
echo "--------------------------------"

# 发送 POST 请求
curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" -X POST "https://www.bing.com/indexnow" \
     -H "Content-Type: application/json; charset=utf-8" \
     -d "$JSON_DATA"

echo "--------------------------------"
echo "✅ 提交完成！(200 或 202 表示成功)"
