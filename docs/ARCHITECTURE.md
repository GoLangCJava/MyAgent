# 架构详解 - Yuxi vs 本项目

## Yuxi 前后端

### 前端 (Vue3)
- `web/src/apis/`: 封装所有 /api 调用, 复用 base.js 的 token 和错误
- `stores/`: Pinia, user, agent, theme
- `composables/`: 
  - `useRequestQueue`: 轮询 Request SSE, 展示 position
  - `useRunStream`: 消费 Run SSE, 合并 delta
  - `useAgentChat`: 组装 query, image, attachment, model_spec
- `views/AgentView` + `components/AgentChatComponent`: 核心交互

### 后端
- `server/main.py`: FastAPI + lifespan (DB, Redis, Sandbox, Checkpoint)
- `server/routers/__init__.py`: 统一挂 /api
- `yuxi/services/agent_request_service.py`: 统一入口, 幂等 request_id, 事务写 Request
- `agent_request_queue_service.py`: FIFO派发, 取消, 引导, 恢复
- `run_queue_service.py`: Redis操作封装 (cancel key, stream, ARQ pool, worker health)
- `run_worker.py`: 抢 lease, heartbeat, 执行 LangGraph, 写 Stream + PG终态
- `storage/redis/manager.py`: 只负责连接
- `storage/postgres/`: 业务池 + checkpoint池
- `workspace/`: Project + workdir_path, no-follow

### Redis 高并发设计
- ARQ: 投递, PG提交后才 enqueue
- Stream: 事件持久化, 可回溯, 断线续传 Last-Event-ID
- Cancel Key: 轮询 + PG兜底, 不用 Pub/Sub
- Worker Health: TTL key 判断失联

### 不变量
- 薄路由, 厚service, repository边界
- 请求接入与执行分离
- 线程级FIFO串行
- Lease租约唯一
- 终态权威 output_message_id

## 本项目 (deepagents 版)

### 改进
- 内核: Yuxi BaseAgent -> deepagents create_deep_agent
- 中间件: 规划(todo), 子智能体(task), 文件系统(/workspace), 上下文压缩自动
- Checkpoint: AsyncPostgresSaver 支持中断恢复
- 前端: 完整版, 登录, 智能体管理, 会话, 项目文件, 模型设置
- 后端: 完整版, 7个路由, JWT, 用户, 项目, 文件, 模型

### 目录
- `backend/server/routers/`: auth, agent, conversation, project, model, file, system
- `package/deep_platform/agents/`: factory, presets, tools/builtin
- `services/`: 保留 Yuxi FIFO+Lease+Stream 核心
- `web/src/`: router守卫, Pinia, apis, composables, components, views

### 高并发验证
- 同一 thread_id 并发 100 请求, 观察 queued position 递增, 串行执行
- kill -9 worker, 120s后 lease过期收敛 failed, recover_pending补发
- 前端断网重连, 带 Last-Event-ID 续传
