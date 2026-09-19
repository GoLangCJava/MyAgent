# Deep Platform - 完整版

基于 Yuxi 架构 + deepagents 内核的高并发智能体平台，含完整前后端。

## 快速启动 (本地脚本, 不用 docker)

前置: 本机装好 Python 3.10+、Node 18+，并启动 Postgres(5432) / Redis(6379)。

```bash
# 1. 一键准备环境 (建 venv、装依赖、生成 .env、检查 PG/Redis)
./scripts/setup.sh

# 2. 编辑 .env, 填入你的 Key:
#   SILICONFLOW_API_KEY=sk-xxx
#   SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
#   DEFAULT_MODEL=siliconflow:Qwen/Qwen2.5-7B-Instruct

# 3. 一键启动 api + worker + web (后台运行)
./scripts/start.sh

# 前端 http://localhost:5173  账号 admin / admin123
# 后端 docs http://localhost:8000/docs
curl http://localhost:8000/api/system/ready
```

常用脚本:

| 脚本 | 说明 |
|---|---|
| `./scripts/setup.sh` | 初始化环境, 只需跑一次 |
| `./scripts/start.sh [all\|api\|worker\|web]` | 后台启动服务, 日志在 `logs/` |
| `./scripts/stop.sh [all\|api\|worker\|web]` | 停止服务 |
| `./scripts/status.sh` | 查看运行状态 + api 健康检查 |
| `./scripts/start-api.sh` / `start-worker.sh` / `start-web.sh` | 前台单独启动, 调试用 |
| `WORKERS=2 ./scripts/start.sh worker` | 启动 2 个 worker |

> `docker-compose.yml` 仍保留, 想用 docker 时 `docker compose up --build -d` 即可。

## 模型配置说明

- 默认模型 `siliconflow:Qwen/Qwen2.5-7B-Instruct`, 走 SiliconFlow OpenAI 兼容接口
- 代码读取顺序: `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` → `OPENAI_*` 兜底
- `model_spec` 格式为 `provider:model`, 如 `siliconflow:Qwen/Qwen2.5-7B-Instruct`
  纯模型名 (如 `Qwen/Qwen2.5-7B-Instruct`) 会自动使用默认 provider
- 真实 Key 只放在本地 `.env` (已 gitignore), 不要提交到 Git
- 也可在前端「设置 → 模型提供商」里添加/切换提供商

## 目录

- `backend/` FastAPI + ARQ + deepagents
  - `server/main.py` 入口, lifespan, CORS, 中间件
  - `server/routers/` 7个路由: auth, agent, conversation, project, model, file, system
  - `package/deep_platform/storage/` PG + Redis 管理
  - `services/` 核心: FIFO队列 + Lease租约 + Redis Stream
  - `agents/` deepagents 工厂 + 预设 + 工具
- `web/` Vue3 + Vite + Pinia + Ant Design Vue
  - 完整路由守卫, 登录, 聊天, 智能体列表, 会话, 设置, 项目文件

## 架构 (Yuxi 核心保留)

```
Vue Chat -> POST /api/agent/runs (request_id幂等)
  -> PG事务: Message + Request + FIFO检查 (FOR UPDATE)
  -> dispatch_ready_head -> ARQ Redis
  -> Worker: try_acquire_lease (120s) + heartbeat 30s + cancel双通道
  -> deepagents: planning(todo) + subagents(task) + filesystem + context压缩
  -> Redis Stream: message_delta -> run_completed -> PG终态
  -> 前端两阶段 SSE: Request(queued) -> Run(stream)
```

## 高并发保证

- 线程级 FIFO: (uid, agent_slug, thread_id) 串行
- Lease: 唯一 worker_id, 过期自动收敛 failed
- 幂等: request_id 唯一索引
- 取消: Redis 0.2s + PG 1s
- 恢复: 启动时 recover_pending_dispatches
# MyAgent
