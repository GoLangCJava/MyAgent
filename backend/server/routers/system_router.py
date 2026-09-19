from fastapi import APIRouter
from sqlalchemy import text
from deep_platform.storage.postgres.manager import SessionLocal
from deep_platform.storage.redis import get_async_redis_client

system_router = APIRouter()

@system_router.get("/ready")
async def ready():
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        r=await get_async_redis_client()
        await r.ping()
        return {"status":"ready","postgres":"ok","redis":"ok"}
    except Exception as e:
        return {"status":"not_ready","error":str(e)}

@system_router.get("/health")
async def health():
    return {"status":"alive"}

@system_router.get("/stats")
async def stats():
    from sqlalchemy import select, func
    from deep_platform.storage.postgres.models import AgentRun, Conversation, User, Agent
    async with SessionLocal() as db:
        q1=await db.execute(select(func.count()).select_from(AgentRun))
        q2=await db.execute(select(func.count()).select_from(Conversation))
        q3=await db.execute(select(func.count()).select_from(User))
        q4=await db.execute(select(func.count()).select_from(Agent))
        return {"runs":q1.scalar(),"conversations":q2.scalar(),"users":q3.scalar(),"agents":q4.scalar()}
