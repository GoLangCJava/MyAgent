# Deep Platform - 完整版

基于 Yuxi 架构 + deepagents 内核的高并发智能体平台，含完整前后端。

## 快速启动

```bash
docker compose up --build -d
curl http://localhost:8000/api/system/ready
# 前端 http://localhost:5173  账号 admin / admin123
# 后端 docs http://localhost:8000/docs
```

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
