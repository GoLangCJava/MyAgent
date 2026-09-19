#!/usr/bin/env bash
# 查看本地服务状态
cd "$(dirname "$0")/.." || exit 1

show() {
  local f="$1" name="$2"
  if [ -f "$f" ] && kill -0 "$(cat "$f")" 2>/dev/null; then
    echo "$name 运行中 ✅ (pid $(cat "$f"))"
  else
    echo "$name 未运行 ❌"
  fi
}

show logs/api.pid api
for f in logs/worker-*.pid; do
  [ -e "$f" ] || { echo "worker 未运行 ❌"; break; }
  show "$f" "$(basename "$f" .pid)"
done
show logs/web.pid web

echo ""
echo "--- api 健康检查 ---"
curl -s --max-time 5 http://localhost:${API_PORT:-8000}/api/system/ready || echo "api 无响应"
echo ""
