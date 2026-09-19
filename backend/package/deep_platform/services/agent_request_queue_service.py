from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.models import AgentRunRequest, AgentRun
from deep_platform.config import settings
import uuid

LEASE_SECONDS=120

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

async def get_queue_head(db: AsyncSession, uid: str, agent_slug: str, thread_id: str):
    q=await db.execute(select(AgentRunRequest).where(AgentRunRequest.uid==uid, AgentRunRequest.agent_slug==agent_slug, AgentRunRequest.thread_id==thread_id, AgentRunRequest.status=="queued").order_by(AgentRunRequest.created_at.asc()).limit(1).with_for_update())
    return q.scalars().first()

async def get_active_run(db: AsyncSession, uid: str, thread_id: str):
    q=await db.execute(select(AgentRun).where(AgentRun.uid==uid, AgentRun.thread_id==thread_id, AgentRun.status=="running").limit(1))
    return q.scalars().first()

async def get_queue_position(db: AsyncSession, request: AgentRunRequest) -> int:
    q=await db.execute(select(func.count()).select_from(AgentRunRequest).where(AgentRunRequest.uid==request.uid, AgentRunRequest.agent_slug==request.agent_slug, AgentRunRequest.thread_id==request.thread_id, AgentRunRequest.status=="queued", AgentRunRequest.created_at<=request.created_at))
    return int(q.scalar() or 1)

async def dispatch_ready_head(db: AsyncSession, uid: str, agent_slug: str, thread_id: str, expected_request_id: str|None=None):
    head=await get_queue_head(db, uid, agent_slug, thread_id)
    if not head: return None
    if expected_request_id and head.request_id!=expected_request_id: return None
    active=await get_active_run(db, uid, thread_id)
    if active: return None
    run_id=str(uuid.uuid4())
    now=utcnow()
    run=AgentRun(id=run_id, request_id=head.request_id, uid=uid, agent_slug=agent_slug, thread_id=thread_id, conversation_id=head.conversation_id or thread_id, status="pending", runtime_scope_id=thread_id, attempt=0, created_at=now)
    db.add(run)
    head.status="dispatched"
    head.dispatched_run_id=run_id
    head.updated_at=now
    await db.flush()
    return run

async def recover_pending_dispatches(db: AsyncSession):
    q=await db.execute(select(AgentRun).where(AgentRun.status=="pending").limit(100))
    runs=q.scalars().all()
    from deep_platform.services.agent_run_service import enqueue_agent_run
    for r in runs:
        await enqueue_agent_run(r.id)
    return len(runs)

async def try_acquire_run_lease(db: AsyncSession, run_id: str, worker_id: str) -> bool:
    now=utcnow()
    q=await db.execute(select(AgentRun).where(AgentRun.id==run_id).with_for_update())
    run=q.scalars().first()
    if not run: return False
    if run.status not in ("pending","running"):
        if run.status=="running" and run.lease_expires_at and run.lease_expires_at < now:
            pass
        else:
            return False
    run.worker_id=worker_id
    run.status="running"
    run.attempt+=1
    run.started_at=run.started_at or now
    run.lease_expires_at=now+timedelta(seconds=LEASE_SECONDS)
    await db.flush()
    await db.commit()
    return True

async def renew_run_lease(db: AsyncSession, run_id: str, worker_id: str) -> bool:
    now=utcnow()
    q=await db.execute(select(AgentRun).where(AgentRun.id==run_id, AgentRun.worker_id==worker_id).with_for_update())
    run=q.scalars().first()
    if not run or run.status!="running": return False
    run.lease_expires_at=now+timedelta(seconds=LEASE_SECONDS)
    await db.flush()
    await db.commit()
    return True

async def fail_expired_leases(db: AsyncSession):
    now=utcnow()
    q=await db.execute(select(AgentRun).where(AgentRun.status=="running", AgentRun.lease_expires_at!=None, AgentRun.lease_expires_at<now))
    runs=q.scalars().all()
    for r in runs:
        r.status="failed"
        r.error={"reason":"worker_lease_expired"}
        r.finished_at=now
        r.lease_expires_at=None
    if runs:
        await db.commit()
    return len(runs)
