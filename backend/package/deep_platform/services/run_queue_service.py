import asyncio, json, os
import logging
from deep_platform.utils.logger import get_logger
from datetime import datetime, timezone
from deep_platform.storage.redis import get_async_redis_client, create_arq_pool, close_async_redis_client
from deep_platform.config import settings

logger = get_logger(__name__)

_arq_pool=None

def _cancel_key(run_id: str): return f"run:cancel:{run_id}"
def _event_key(run_id: str): return f"run:events:{run_id}"

async def get_redis(): return await get_async_redis_client()
async def get_arq_pool():
    global _arq_pool
    if _arq_pool is None:
        _arq_pool=await create_arq_pool()
    return _arq_pool

async def publish_cancel_signal(run_id: str):
    try:
        r=await get_redis()
        await r.set(_cancel_key(run_id), "1", ex=settings.RUN_CANCEL_TTL)
    except: pass

async def wait_for_cancel_signal(run_id: str, poll_interval: float=0.2):
    loop=asyncio.get_running_loop()
    while True:
        start=loop.time()
        try:
            r=await get_redis()
            if await r.get(_cancel_key(run_id)):
                return True
        except asyncio.CancelledError:
            raise
        except: pass
        await asyncio.sleep(max(0, poll_interval-(loop.time()-start)))

async def clear_cancel_signal(run_id: str):
    try:
        r=await get_redis()
        await r.delete(_cancel_key(run_id))
    except: pass

def build_envelope(run_id: str, event_type: str, payload: dict, thread_id: str|None=None):
    return {
        "schema_version":1,
        "run_id":run_id,
        "thread_id":thread_id,
        "event":event_type,
        "payload":payload,
        "created_at":datetime.now(timezone.utc).isoformat()
    }

async def append_run_event(run_id: str, event_type: str, payload: dict, thread_id: str|None=None) -> str:
    r=await get_redis()
    key=_event_key(run_id)
    envelope=build_envelope(run_id, event_type, payload, thread_id)
    fields={"event_type":event_type, "payload":json.dumps(envelope, ensure_ascii=False), "ts":str(int(datetime.now(timezone.utc).timestamp()*1000))}
    kwargs={}
    if settings.RUN_STREAM_MAXLEN>0:
        kwargs["maxlen"]=settings.RUN_STREAM_MAXLEN
        kwargs["approximate"]=True
    async with r.pipeline(transaction=False) as pipe:
        pipe.xadd(key, fields, **kwargs)
        pipe.expire(key, settings.RUN_STREAM_TTL)
        eid,_=await pipe.execute()
    extra=""
    if event_type=="message_delta":
        extra=f" preview={str(payload.get('delta',''))[:60]!r}"
    elif event_type in ("run_failed",):
        extra=f" error={str(payload.get('error',''))[:200]!r}"
    # logger.info("[stream %s] %s seq=%s%s", run_id, event_type, eid, extra)
    return str(eid)

async def list_run_events(run_id: str, after_seq: str="0-0", limit: int=200):
    r=await get_redis()
    key=_event_key(run_id)
    start="-" if after_seq in {"0-0",""} else f"({after_seq}"
    rows=await r.xrange(key, min=start, max="+", count=limit)
    out=[]
    for eid, fields in rows:
        try:
            payload=json.loads(fields.get("payload","{}"))
        except:
            payload={}
        out.append({"seq":str(eid), "event_type":fields.get("event_type"), "payload":payload, "ts":fields.get("ts")})
    return out

async def close_queue_clients():
    global _arq_pool
    if _arq_pool:
        try: await _arq_pool.close()
        except: pass
        _arq_pool=None
    await close_async_redis_client()
