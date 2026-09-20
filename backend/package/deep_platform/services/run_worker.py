import asyncio, uuid, os
import logging
from deep_platform.utils.logger import get_logger
from datetime import datetime, timezone
from arq import func
from deep_platform.storage.postgres.manager import SessionLocal
from deep_platform.storage.postgres.models import AgentRun, Message, AgentRunRequest, Conversation
from deep_platform.services.agent_request_queue_service import try_acquire_run_lease, renew_run_lease, dispatch_ready_head
from deep_platform.services.run_queue_service import append_run_event, wait_for_cancel_signal, clear_cancel_signal
from deep_platform.services.agent_run_service import complete_run
from deep_platform.agents.factory import create_deep_agent_for_run
from deep_platform.storage.redis import get_arq_redis_settings
from sqlalchemy import select

WORKER_ID=f"worker-{uuid.uuid4().hex[:8]}"
HEARTBEAT=30
logger = get_logger(__name__)

async def run_agent(ctx, run_id: str):
    print(f"[{WORKER_ID}] run {run_id} start")
    logger.info("[run %s] worker=%s 领到任务", run_id, WORKER_ID)
    async with SessionLocal() as db:
        ok=await try_acquire_run_lease(db, run_id, WORKER_ID)
        if not ok:
            logger.warning("[run %s] lease 获取失败 (已有 worker 在跑或状态不对), 跳过", run_id)
            print(f"[{WORKER_ID}] lease not acquired {run_id}")
            return

    # 加载上下文
    async with SessionLocal() as db:
        q=await db.execute(select(AgentRun).where(AgentRun.id==run_id))
        run=q.scalars().first()
        if not run:
            logger.error("[run %s] DB 中找不到该 run, 放弃", run_id)
            return
        uid, agent_slug, thread_id, request_id, conv_id = run.uid, run.agent_slug, run.thread_id, run.request_id, run.conversation_id
        q2=await db.execute(select(Message).where(Message.request_id==request_id, Message.role=="user"))
        umsg=q2.scalars().first()
        query=umsg.content if umsg else "Hello"
        q3=await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id==request_id))
        req=q3.scalars().first()
        model_spec=req.input_payload.get("model_spec") if req and req.input_payload else None
        q4=await db.execute(select(Conversation).where(Conversation.id==conv_id))
        conv=q4.scalars().first()
        system_prompt=conv.extra_metadata.get("system_prompt") if conv and conv.extra_metadata else None
        if not system_prompt:
            from deep_platform.storage.postgres.models import Agent
            q5=await db.execute(select(Agent).where(Agent.slug==agent_slug))
            ag=q5.scalars().first()
            system_prompt=ag.system_prompt if ag else None
    logger.info("[run %s] 上下文 thread=%s agent=%s model_spec=%s query_len=%d", run_id, thread_id, agent_slug, model_spec, len(query))

    cancel_event=asyncio.Event()
    async def watch_cancel():
        await wait_for_cancel_signal(run_id, 0.2)
        cancel_event.set()
    async def heartbeat():
        while not cancel_event.is_set():
            await asyncio.sleep(HEARTBEAT)
            async with SessionLocal() as db:
                renewed=await renew_run_lease(db, run_id, WORKER_ID)
                if not renewed:
                    cancel_event.set()
                    return
    ct=asyncio.create_task(watch_cancel())
    ht=asyncio.create_task(heartbeat())

    try:
        await append_run_event(run_id, "run_started", {"run_id":run_id, "thread_id":thread_id}, thread_id)

        agent=create_deep_agent_for_run(agent_slug, system_prompt=system_prompt, model_spec=model_spec, thread_id=thread_id)
        logger.info("[run %s] agent 构建完成, 开始调用模型...", run_id)

        output_text=""
        msg_n=0; upd_n=0; first_delta_logged=False
        import time as _time
        _t0=_time.time()
        # 兼容 deepagents 和 langchain agent 的流式
        try:
            async for event in agent.astream({"messages":[{"role":"user","content":query}]}, stream_mode=["messages","updates"]):
                if cancel_event.is_set():
                    logger.info("[run %s] 用户取消", run_id)
                    await append_run_event(run_id, "run_cancelled", {"reason":"user_cancel"}, thread_id)
                    async with SessionLocal() as db:
                        q=await db.execute(select(AgentRun).where(AgentRun.id==run_id).with_for_update())
                        r=q.scalars().first()
                        if r:
                            r.status="cancelled"
                            r.finished_at=datetime.now(timezone.utc).replace(tzinfo=None)
                            r.lease_expires_at=None
                            await db.commit()
                    return

                try:
                    if isinstance(event, (list,tuple)) and len(event)==2:
                        mode,data=event
                    else:
                        mode,data="messages",event

                    if mode=="messages":
                        # data is (chunk, metadata)
                        chunk=data[0] if isinstance(data,(list,tuple)) else data
                        content=getattr(chunk,"content",None)
                        if content is None and isinstance(chunk, dict):
                            content=chunk.get("content")
                        if content:
                            # content可能是list
                            if isinstance(content, list):
                                txt="".join([c.get("text","") if isinstance(c,dict) else str(c) for c in content])
                            else:
                                txt=str(content)
                            if txt:
                                output_text+=txt
                                msg_n+=1
                                if not first_delta_logged:
                                    first_delta_logged=True
                                    logger.info("[run %s] 首个 delta 到达 (%.1fs), 累计输出 %d 字符", run_id, _time.time()-_t0, len(output_text))
                                await append_run_event(run_id, "message_delta", {"delta":txt}, thread_id)
                    elif mode=="updates":
                        # 工具调用等
                        upd_n+=1
                        await append_run_event(run_id, "step_update", {"update":str(data)[:2000]}, thread_id)
                    else:
                        logger.warning("[run %s] 未知 stream mode=%r, 事件已忽略", run_id, mode)
                except Exception as e:
                    logger.warning("[run %s] 事件解析失败: %s (事件预览: %r)", run_id, e, str(event)[:300])
                    print(f"event parse error {e}")

            logger.info("[run %s] 模型流结束 (%.1fs): deltas=%d updates=%d output_len=%d", run_id, _time.time()-_t0, msg_n, upd_n, len(output_text))
            if msg_n==0 and upd_n==0:
                logger.warning("[run %s] 模型一次事件都没吐! 检查 Key/网络/模型名", run_id)

        except Exception as e:
            # fallback: invoke
            logger.warning("[run %s] astream 失败转 invoke: %s", run_id, e)
            print(f"astream failed {e}, fallback invoke")
            try:
                result=await agent.ainvoke({"messages":[{"role":"user","content":query}]})
                msgs=result.get("messages",[]) if isinstance(result, dict) else []
                if msgs:
                    last=msgs[-1]
                    txt=getattr(last,"content","") or (last.get("content") if isinstance(last,dict) else str(last))
                    if isinstance(txt, list):
                        txt="".join([c.get("text","") if isinstance(c,dict) else str(c) for c in txt])
                    output_text=str(txt)
                    await append_run_event(run_id, "message_delta", {"delta":output_text}, thread_id)
                else:
                    output_text=str(result)
                    await append_run_event(run_id, "message_delta", {"delta":output_text}, thread_id)
            except Exception as e2:
                logger.error("[run %s] invoke 也失败了: %s", run_id, e2)
                print(f"invoke also failed {e2}")
                raise e

        # 保存 assistant消息
        async with SessionLocal() as db:
            out_id=str(uuid.uuid4())
            out_msg=Message(id=out_id, conversation_id=conv_id, thread_id=thread_id, run_id=run_id, request_id=request_id, role="assistant", content=output_text or "[No output]", delivery_status="dispatched", extra_metadata={"run_id":run_id})
            db.add(out_msg)
            await db.flush()
            await complete_run(db, run_id, output_message_id=out_id)
            await append_run_event(run_id, "run_completed", {"run_id":run_id, "output_message_id":out_id}, thread_id)
            logger.info("[run %s] 完成: output_len=%d msg=%s", run_id, len(output_text), out_id)

        # 链式派发下一请求
        async with SessionLocal() as db:
            dispatched=await dispatch_ready_head(db, uid=uid, agent_slug=agent_slug, thread_id=thread_id)
            await db.commit()
            if dispatched:
                from deep_platform.services.agent_run_service import enqueue_agent_run
                await enqueue_agent_run(dispatched.id)

    except Exception as e:
        logger.exception("[run %s] 失败: %s", run_id, e)
        print(f"[{WORKER_ID}] run {run_id} failed {e}")
        import traceback; traceback.print_exc()
        async with SessionLocal() as db:
            await complete_run(db, run_id, error={"message":str(e)})
            await append_run_event(run_id, "run_failed", {"error":str(e)}, thread_id)
    finally:
        ct.cancel(); ht.cancel()
        try: await asyncio.gather(ct, ht, return_exceptions=True)
        except: pass
        await clear_cancel_signal(run_id)

class WorkerSettings:
    functions=[func(run_agent, name="run_agent", max_tries=1)]
    redis_settings=get_arq_redis_settings()
    max_jobs=int(os.getenv("ARQ_MAX_JOBS","10"))
    job_timeout=3600
    async def startup(self, ctx):
        print(f"Worker {WORKER_ID} startup max_jobs={self.max_jobs}")
        async with SessionLocal() as db:
            from deep_platform.services.agent_request_queue_service import recover_pending_dispatches, fail_expired_leases
            await fail_expired_leases(db)
            cnt=await recover_pending_dispatches(db)
            print(f"Recovered {cnt} pending")
    async def shutdown(self, ctx):
        print(f"Worker {WORKER_ID} shutdown")
