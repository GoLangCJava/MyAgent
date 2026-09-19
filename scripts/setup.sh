#!/usr/bin/env bash
# 一键准备本地运行环境: 检查依赖 -> 生成 .env -> 建 venv 装后端依赖 -> 装前端依赖 -> 检查 PG/Redis
set -e
cd "$(dirname "$0")/.." || exit 1

echo "=== 1/5 检查基础依赖 ==="
command -v python3 >/dev/null || { echo "缺 python3, 请先安装 Python 3.10+"; exit 1; }
python3 -c "import sys; assert sys.version_info >= (3, 10), 'Python 需 3.10+, 当前 %s' % sys.version" || exit 1
command -v npm >/dev/null || { echo "缺 npm, 请先安装 Node.js 18+"; exit 1; }
echo "python: $(python3 --version), node: $(node --version 2>/dev/null || echo 未知)"

echo "=== 2/5 配置 .env ==="
if [ ! -f .env ]; then
  cp .env.template .env
  echo ".env 已从模板生成, 请编辑填入 SILICONFLOW_API_KEY"
else
  echo ".env 已存在, 跳过"
fi

echo "=== 3/5 后端虚拟环境 + 依赖 ==="
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "已创建 .venv"
fi
.venv/bin/pip install -q --upgrade pip
if ! .venv/bin/pip install -r backend/requirements.txt; then
  echo ""
  echo "依赖安装失败, 常见原因与解决:"
  echo "- 请把上方 ERROR: 开头的完整报错贴出来, 以便定位是哪个包"
  echo "- 如报 pg_config 缺失 / 需要编译: macOS 请先 xcode-select --install, 或 brew install postgresql"
  echo "- 如仍失败, 可换 Python 3.11/3.12 重建环境: rm -rf .venv && python3.12 -m venv .venv && ./scripts/setup.sh"
  exit 1
fi
echo "后端依赖安装完成"

echo "=== 4/5 前端依赖 ==="
if [ ! -d web/node_modules ]; then
  (cd web && npm install)
else
  echo "web/node_modules 已存在, 跳过 (如需更新请手动 cd web && npm install)"
fi

echo "=== 5/5 检查 PG / Redis 连通性 ==="
set -a; [ -f .env ] && source .env >/dev/null 2>&1; set +a
.venv/bin/python - <<'EOF'
import socket, os
from urllib.parse import urlparse

def tcp_ok(host, port):
    s = socket.socket(); s.settimeout(3)
    try:
        s.connect((host, int(port))); return True
    except Exception:
        return False
    finally:
        s.close()

pg = urlparse(os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/deep_platform"))
print(f"Postgres {pg.hostname}:{pg.port or 5432} ->", "通 ✅" if tcp_ok(pg.hostname, pg.port or 5432) else "不通 ❌ (请先启动 Postgres)")
rds = urlparse(os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"))
print(f"Redis {rds.hostname}:{rds.port or 6379} ->", "通 ✅" if tcp_ok(rds.hostname, rds.port or 6379) else "不通 ❌ (请先启动 Redis)")
EOF

echo ""
echo "准备完成! 启动服务: ./scripts/start.sh"
