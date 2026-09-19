#!/usr/bin/env bash
# 前台单独启动 api (调试用, Ctrl+C 退出)
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] || { echo ".env 不存在, 先执行 ./scripts/setup.sh"; exit 1; }
[ -x .venv/bin/python ] || { echo ".venv 不存在, 先执行 ./scripts/setup.sh"; exit 1; }
set -a; source .env; set +a
export PYTHONPATH="$PWD/backend:$PWD/backend/package"
exec .venv/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port "${API_PORT:-8000}" --reload --reload-dir backend/server --reload-dir backend/package
