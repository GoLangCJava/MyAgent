#!/usr/bin/env bash
# 停止本地启动的所有服务
# 用法: ./scripts/stop.sh [api|worker|web]
cd "$(dirname "$0")/.." || exit 1

TARGET="${1:-all}"

stop_by_pidfile() {
  local f="$1" name="$2"
  if [ ! -f "$f" ]; then echo "$name 未运行"; return; fi
  local pid
  pid=$(cat "$f")
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null || true
    echo "$name 已停止 (pid $pid)"
  else
    echo "$name pid 已失效, 清理"
  fi
  rm -f "$f"
}

case "$TARGET" in
  all)
    stop_by_pidfile logs/api.pid api
    for f in logs/worker-*.pid; do
      [ -e "$f" ] || continue
      stop_by_pidfile "$f" "$(basename "$f" .pid)"
    done
    stop_by_pidfile logs/web.pid web
    ;;
  api)    stop_by_pidfile logs/api.pid api ;;
  worker)
    for f in logs/worker-*.pid; do
      [ -e "$f" ] || { echo "worker 未运行"; break; }
      stop_by_pidfile "$f" "$(basename "$f" .pid)"
    done
    ;;
  web)    stop_by_pidfile logs/web.pid web ;;
  *)      echo "用法: $0 [all|api|worker|web]"; exit 1 ;;
esac
