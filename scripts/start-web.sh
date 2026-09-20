#!/usr/bin/env bash
# 前台单独启动 web (调试用, Ctrl+C 退出)
cd "$(dirname "$0")/.." || exit 1
cd web || exit 1
[ -d node_modules ] || { echo "node_modules 不存在, 先执行 ./scripts/setup.sh"; exit 1; }
export VITE_API_BASE="http://localhost:${API_PORT:-8000}"
exec npm run dev -- --port "${WEB_PORT:-5173}"
