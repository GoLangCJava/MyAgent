#!/bin/bash
# 兼容旧入口, 实际走 setup.sh (本地启动, 不用 docker)
set -e
cd "$(dirname "$0")/.." || exit 1
echo "Init Deep Platform (本地启动模式)..."
./scripts/setup.sh
echo ""
echo "启动: ./scripts/start.sh"
echo "前端: http://localhost:5173  admin/admin123"
echo "文档: http://localhost:8000/docs"
echo "就绪: http://localhost:8000/api/system/ready"
