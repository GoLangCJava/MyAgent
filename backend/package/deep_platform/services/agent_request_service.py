from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from deep_platform.storage.postgres.models import AgentRunRequest, Message, Conversation
import uuid

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

@dataclass
class AgentRequestInput:
    agent_slug: str
    thread_id: str
    request_id: str
    query: str
    uid: str
    queue_policy: str="enqueue"
    model_spec: str|None=None
    conversation_id: str|None=None

async def submit_agent_request(db: AsyncSession, inp: AgentRequestInput):
    # 幂等
    q=await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id==inp.request_id))
    existing=q.scalars().first()
    if existing:
        return {"request_id":existing.request_id, "status":existing.status, "run_id":existing.dispatched_run_id, "queue_position":1, "request_events_url":f"/api/agent/requests/{existing.request_id}/events"}

    # 确保 Conversation 存在
    conv_q=await db.execute(select(Conversation).where(Conversation.thread_id==inp.thread_id))
    conv=conv_q.scalars().first()
    if not conv:
        conv=Conversation(thread_id=inp.thread_id, uid=inp.uid, agent_slug=inp.agent_slug, title=inp.query[:50] or "New Chat", model_spec=inp.model_spec)
        db.add(conv)
        await db.flush()
    else:
        conv.updated_at=utcnow()
        if inp.model_spec:
            conv.model_spec=inp.model_spec

    # 创建 user message
    msg_id=str(uuid.uuid4())
    msg=Message(id=msg_id, conversation_id=conv.id, thread_id=inp.thread_id, request_id=inp.request_id, role="user", content=inp.query, delivery_status="queued", extra_metadata={"request_id":inp.request_id})
    db.add(msg)

    req=AgentRunRequest(request_id=inp.request_id, uid=inp.uid, agent_slug=inp.agent_slug, thread_id=inp.thread_id, conversation_id=conv.id, queue_policy=inp.queue_policy, status="queued", input_payload={"model_spec":inp.model_spec, "query":inp.query}, input_message_id=msg_id, created_at=utcnow(), updated_at=utcnow())
    db.add(req)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        q=await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id==inp.request_id))
        e=q.scalars().first()
        return {"request_id":e.request_id, "status":e.status, "run_id":e.dispatched_run_id}

    from deep_platform.services.agent_request_queue_service import dispatch_ready_head
    dispatched=await dispatch_ready_head(db, uid=inp.uid, agent_slug=inp.agent_slug, thread_id=inp.thread_id)
    await db.commit()

    if dispatched:
        from deep_platform.services.agent_run_service import enqueue_agent_run
        await enqueue_agent_run(dispatched.id)
        return {"request_id":req.request_id, "status":"dispatched", "run_id":dispatched.id, "stream_url":f"/api/agent/runs/{dispatched.id}/events", "request_events_url":f"/api/agent/requests/{req.request_id}/events", "conversation_id":conv.id}
    else:
        return {"request_id":req.request_id, "status":"queued", "run_id":None, "queue_position":1, "request_events_url":f"/api/agent/requests/{req.request_id}/events", "conversation_id":conv.id}
