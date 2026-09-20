from fastapi import APIRouter, Depends, Query, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid, asyncio, json, logging
from deep_platform.utils.logger import get_logger

logger = get_logger(__name__)

from deep_platform.storage.postgres.manager import get_db, SessionLocal
from deep_platform.storage.postgres.models import AgentRunRequest, AgentRun, Message, Agent, User
from deep_platform.services.agent_request_service import AgentRequestInput, submit_agent_request
from deep_platform.services.run_queue_service import list_run_events, publish_cancel_signal
from deep_platform.services.agent_request_queue_service import get_queue_position
from server.utils.auth import get_current_user

agent_router = APIRouter()

class AgentCreate(BaseModel):
    slug: str
    name: str
    description: str = ""
    icon: str = "🤖"
    system_prompt: str = "You are a helpful assistant."
    config_json: dict = {}
    is_public: bool = True

class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    system_prompt: str | None = None
    config_json: dict | None = None
    is_public: bool | None = None

class AgentRunCreate(BaseModel):
    agent_slug: str = "chatbot"
    thread_id: str
    query: str
    request_id: str | None = None
    queue_policy: str = "enqueue"
    model_spec: str | None = None

@agent_router.get("/")
async def list_agents(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    agents=q.scalars().all()
    # filter public or owned
    visible=[a for a in agents if a.is_public or a.owner_id==current_user.id or current_user.is_admin]
    return {"agents":[{"id":a.id,"slug":a.slug,"name":a.name,"description":a.description,"icon":a.icon,"backend_id":a.backend_id,"system_prompt":a.system_prompt,"is_builtin":a.is_builtin,"is_public":a.is_public,"owner_id":a.owner_id,"created_at":a.created_at} for a in visible]}

@agent_router.post("/")
async def create_agent(payload: AgentCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Agent).where(Agent.slug==payload.slug))
    if q.scalars().first():
        raise HTTPException(status_code=409, detail="slug 已存在")
    ag=Agent(slug=payload.slug, name=payload.name, description=payload.description, icon=payload.icon, system_prompt=payload.system_prompt, config_json=payload.config_json, is_public=payload.is_public, owner_id=current_user.id, backend_id="custom")
    db.add(ag)
    await db.commit()
    await db.refresh(ag)
    return {"agent":{"id":ag.id,"slug":ag.slug,"name":ag.name}}

@agent_router.get("/{slug}")
async def get_agent(slug: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Agent).where(Agent.slug==slug))
    ag=q.scalars().first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent":{"id":ag.id,"slug":ag.slug,"name":ag.name,"description":ag.description,"icon":ag.icon,"system_prompt":ag.system_prompt,"config_json":ag.config_json,"is_builtin":ag.is_builtin,"is_public":ag.is_public}}

@agent_router.put("/{slug}")
async def update_agent(slug: str, payload: AgentUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Agent).where(Agent.slug==slug))
    ag=q.scalars().first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")
    if ag.owner_id!=current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission")
    if ag.is_builtin and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Builtin cannot edit")
    if payload.name is not None: ag.name=payload.name
    if payload.description is not None: ag.description=payload.description
    if payload.icon is not None: ag.icon=payload.icon
    if payload.system_prompt is not None: ag.system_prompt=payload.system_prompt
    if payload.config_json is not None: ag.config_json=payload.config_json
    if payload.is_public is not None: ag.is_public=payload.is_public
    await db.commit()
    return {"agent":{"id":ag.id,"slug":ag.slug,"name":ag.name}}

@agent_router.delete("/{slug}")
async def delete_agent(slug: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Agent).where(Agent.slug==slug))
    ag=q.scalars().first()
    if not ag:
        raise HTTPException(status_code=404, detail="Not found")
    if ag.is_builtin:
        raise HTTPException(status_code=403, detail="Builtin cannot delete")
    if ag.owner_id!=current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission")
    await db.delete(ag)
    await db.commit()
    return {"success":True}

@agent_router.post("/runs")
async def create_run(payload: AgentRunCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    req_id=payload.request_id or str(uuid.uuid4())
    inp=AgentRequestInput(agent_slug=payload.agent_slug, thread_id=payload.thread_id, request_id=req_id, query=payload.query, uid=current_user.id, queue_policy=payload.queue_policy, model_spec=payload.model_spec)
    result=await submit_agent_request(db, inp)
    return result

@agent_router.get("/requests/{request_id}")
async def get_request(request_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id==request_id, AgentRunRequest.uid==current_user.id))
    r=q.scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Not found")
    return {"request_id":r.request_id, "status":r.status, "run_id":r.dispatched_run_id, "thread_id":r.thread_id, "created_at":r.created_at}

@agent_router.get("/requests/{request_id}/events")
async def stream_request_events(request_id: str, current_user: User = Depends(get_current_user)):
    async def gen():
        last_pos=-1
        while True:
            async with SessionLocal() as db:
                q=await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id==request_id, AgentRunRequest.uid==current_user.id))
                req=q.scalars().first()
                if not req:
                    yield f"event: error\ndata: {json.dumps({'message':'not found'})}\n\n"
                    return
                if req.status=="dispatched":
                    yield f"event: run_created\ndata: {json.dumps({'request_id':request_id,'run_id':req.dispatched_run_id,'stream_url':f'/api/agent/runs/{req.dispatched_run_id}/events'})}\n\n"
                    return
                if req.status in ("cancelled","rejected","failed"):
                    yield f"event: {req.status}\ndata: {json.dumps({'request_id':request_id,'status':req.status})}\n\n"
                    return
                pos=await get_queue_position(db, req)
                if pos!=last_pos:
                    last_pos=pos
                    yield f"event: queued\ndata: {json.dumps({'request_id':request_id,'position':pos})}\n\n"
            await asyncio.sleep(0.5)
            yield f": heartbeat\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@agent_router.get("/runs/{run_id}")
async def get_run(run_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(AgentRun).where(AgentRun.id==run_id, AgentRun.uid==current_user.id))
    run=q.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    q2=await db.execute(select(Message).where(Message.run_id==run_id, Message.role=="assistant"))
    out=q2.scalars().first()
    return {"run_id":run.id, "status":run.status, "thread_id":run.thread_id, "agent_slug":run.agent_slug, "output":out.content if out else None, "error":run.error, "created_at":run.created_at, "finished_at":run.finished_at}

@agent_router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(AgentRun).where(AgentRun.id==run_id, AgentRun.uid==current_user.id).with_for_update())
    run=q.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    if run.status not in ("running","pending"):
        return {"status":run.status, "message":"not running"}
    run.status="cancel_requested"
    await db.commit()
    await publish_cancel_signal(run_id)
    return {"run_id":run_id, "status":"cancel_requested"}

@agent_router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str, after_seq: str = Query("0-0"), last_event_id: str | None = Header(default=None, alias="Last-Event-ID"), current_user: User = Depends(get_current_user)):
    cursor=last_event_id or after_seq
    # 验证归属
    async with SessionLocal() as db:
        q=await db.execute(select(AgentRun).where(AgentRun.id==run_id, AgentRun.uid==current_user.id))
        if not q.scalars().first():
            raise HTTPException(status_code=404, detail="Not found")
    logger.info("[sse] 订阅 run=%s user=%s cursor=%s", run_id, current_user.id, cursor)

    async def gen():
        cur=cursor
        while True:
            events=await list_run_events(run_id, after_seq=cur, limit=100)
            for ev in events:
                cur=ev["seq"]
                data=json.dumps(ev["payload"], ensure_ascii=False)
                yield f"id: {ev['seq']}\nevent: {ev['event_type']}\ndata: {data}\n\n"
                if ev["event_type"] in ("run_completed","run_failed","run_cancelled"):
                    logger.info("[sse] run=%s 终态推送 %s", run_id, ev["event_type"])
                    return
            async with SessionLocal() as db:
                q=await db.execute(select(AgentRun).where(AgentRun.id==run_id))
                run=q.scalars().first()
                if run and run.status in ("completed","failed","cancelled"):
                    if not events:
                        yield f"event: run_{run.status}\ndata: {json.dumps({'run_id':run_id,'status':run.status})}\n\n"
                    return
            await asyncio.sleep(0.3)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","Connection":"keep-alive","X-Accel-Buffering":"no"})
