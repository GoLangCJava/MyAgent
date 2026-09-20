import logging
from deep_platform.utils.logger import get_logger
from datetime import datetime, timezone
from deep_platform.services.run_queue_service import get_arq_pool

logger = get_logger(__name__)

async def enqueue_agent_run(run_id: str):
    pool=await get_arq_pool()
    job=await pool.enqueue_job("run_agent", run_id)
    logger.info("[run %s] 已入 ARQ 队列 job=%s", run_id, getattr(job, "job_id", "?"))

async def complete_run(db, run_id: str, output_message_id: str|None=None, error: dict|None=None):
    from sqlalchemy import select
    from deep_platform.storage.postgres.models import AgentRun
    q=await db.execute(select(AgentRun).where(AgentRun.id==run_id).with_for_update())
    run=q.scalars().first()
    if not run: return
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    if error:
        run.status="failed"
        run.error=error
    else:
        run.status="completed"
    run.output_message_id=output_message_id
    run.finished_at=now
    run.lease_expires_at=None
    await db.flush()
    await db.commit()
