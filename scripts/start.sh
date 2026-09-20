#!/usr/bin/env bash
# 一键本地启动: api + worker + web, 全部后台运行
# 用法: ./scripts/start.sh [api|worker|web]   (不带参数=全部启动)
# 环境变量: WORKERS=N  worker 数量(默认 1), API_PORT(默认 8000), WEB_PORT(默认 5173)
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"

TARGET="${1:-all}"
WORKERS="${WORKERS:-1}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

[ -f .env ] || { echo ".env 不存在, 先执行 ./scripts/setup.sh"; exit 1; }
[ -x .venv/bin/python ] || { echo ".venv 不存在, 先执行 ./scripts/setup.sh"; exit 1; }
mkdir -p logs

# 加载 .env (代码不读 dotenv 文件, 必须导出到环境)
set -a; source .env; set +a
# Key 缺失告警 (模型调用会失败, 但服务仍可启动)
if [ -z "${SILICONFLOW_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "⚠️  警告: .env 里没有任何模型 API Key, 聊天调用将失败, 请先编辑 .env 填入 SILICONFLOW_API_KEY"
fi
export PYTHONPATH="$ROOT/backend:$ROOT/backend/package"
export VITE_API_BASE="http://localhost:${API_PORT}"

is_running() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

start_api() {
  if is_running logs/api.pid; then echo "api 已在运行 (pid $(cat logs/api.pid)), 跳过"; return; fi
  nohup .venv/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port "$API_PORT" \
    > logs/api.log 2>&1 &
  echo $! > logs/api.pid
  echo "api 已启动, pid $!, 日志 logs/api.log"
}

start_worker() {
  for i in $(seq 1 "$WORKERS"); do
    if is_running "logs/worker-$i.pid"; then echo "worker-$i 已在运行, 跳过"; continue; fi
    nohup .venv/bin/python -m server.worker_main \
      > "logs/worker-$i.log" 2>&1 &
    echo $! > "logs/worker-$i.pid"
    echo "worker-$i 已启动, pid $!, 日志 logs/worker-$i.log"
  done
}

start_web() {
  if is_running logs/web.pid; then echo "web 已在运行 (pid $(cat logs/web.pid)), 跳过"; return; fi
  if [ ! -d web/node_modules ]; then echo "web/node_modules 不存在, 先执行 ./scripts/setup.sh"; return 1; fi
  (
    cd web || exit 1
    nohup npm run dev -- --port "$WEB_PORT" > ../logs/web.log 2>&1 &
    echo $! > ../logs/web.pid
  )
  echo "web 已启动, pid $(cat logs/web.pid), 日志 logs/web.log"
}

case "$TARGET" in
  all)    start_api; start_worker; start_web ;;
  api)    start_api ;;
  worker) start_worker ;;
  web)    start_web ;;
  *)      echo "用法: $0 [all|api|worker|web]"; exit 1 ;;
esac

# 健康检查 (只在启动 api 时做)
if [ "$TARGET" = "all" ] || [ "$TARGET" = "api" ]; then
  echo "等待 api 就绪..."
  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:${API_PORT}/api/system/ready" >/dev/null 2>&1; then
      echo "api 就绪 ✅"
      break
    fi
    sleep 2
  done
  curl -s "http://localhost:${API_PORT}/api/system/ready" || echo "api 暂未就绪, 请看 logs/api.log"
  echo ""
fi

echo ""
echo "前端: http://localhost:${WEB_PORT}  账号 admin / admin123"
echo "文档: http://localhost:${API_PORT}/docs"
echo "停止: ./scripts/stop.sh   状态: ./scripts/status.sh"
