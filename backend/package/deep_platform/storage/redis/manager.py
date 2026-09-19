import asyncio, os
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlparse, urlunparse
from deep_platform.config import settings

def redact(url: str) -> str:
    try:
        p=urlparse(url)
        if p.password:
            p=p._replace(netloc=p.netloc.replace(p.password,"***"))
        return urlunparse(p)
    except: return url

@dataclass(frozen=True)
class RedisConfig:
    url: str = settings.REDIS_URL
    max_connections: int = 32
    decode_responses: bool = True
    @classmethod
    def from_env(cls): return cls(url=settings.REDIS_URL)
    @property
    def log_url(self): return redact(self.url)
    def conn_kwargs(self): return {"decode_responses": self.decode_responses, "max_connections": self.max_connections}

def create_sync_client(config: RedisConfig|None=None):
    import redis
    cfg=config or RedisConfig.from_env()
    c=redis.from_url(cfg.url, **cfg.conn_kwargs())
    c.ping()
    return c

async def create_async_client(config: RedisConfig|None=None):
    from redis.asyncio import Redis
    cfg=config or RedisConfig.from_env()
    c=Redis.from_url(cfg.url, **cfg.conn_kwargs())
    await c.ping()
    return c

_async_client: Any|None=None
_lock: asyncio.Lock|None=None

def _get_lock():
    global _lock
    if _lock is None: _lock=asyncio.Lock()
    return _lock

async def get_async_redis_client(config: RedisConfig|None=None):
    global _async_client
    if _async_client is not None: return _async_client
    async with _get_lock():
        if _async_client is None:
            _async_client=await create_async_client(config)
        return _async_client

async def close_async_redis_client():
    global _async_client
    if _async_client:
        try: await _async_client.aclose()
        except: pass
        _async_client=None

def get_arq_redis_settings(config: RedisConfig|None=None):
    from arq.connections import RedisSettings
    cfg=config or RedisConfig.from_env()
    return replace(RedisSettings.from_dsn(cfg.url), max_connections=cfg.max_connections)

async def create_arq_pool(config: RedisConfig|None=None):
    from arq.connections import create_pool
    return await create_pool(get_arq_redis_settings(config))
