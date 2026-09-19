from contextlib import asynccontextmanager
from fastapi import FastAPI
from deep_platform.storage.postgres.manager import init_models, engine
from deep_platform.storage.redis import get_async_redis_client
from deep_platform.storage.postgres.models import Agent
from deep_platform.agents.presets import AGENT_PRESETS
from deep_platform.storage.postgres.manager import SessionLocal
from sqlalchemy import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=== Lifespan startup ===")
    try:
        await init_models()
        print("PG init ok")
    except Exception as e:
        print(f"PG init failed {e}")
        raise

    try:
        r=await get_async_redis_client()
        await r.ping()
        print(f"Redis ok {r}")
    except Exception as e:
        print(f"Redis failed {e}")
        raise

    # seed builtin agents
    try:
        async with SessionLocal() as db:
            for slug, preset in AGENT_PRESETS.items():
                q=await db.execute(select(Agent).where(Agent.slug==slug))
                if not q.scalars().first():
                    # find admin user
                    from deep_platform.storage.postgres.models import User
                    uq=await db.execute(select(User).where(User.username=="admin"))
                    admin=uq.scalars().first()
                    owner=admin.id if admin else "system"
                    ag=Agent(slug=slug, name=preset["name"], description=preset["description"], icon=preset["icon"], backend_id=preset["backend_id"], system_prompt=preset["system_prompt"], is_builtin=True, is_public=True, owner_id=owner)
                    db.add(ag)
            await db.commit()
            print("Builtin agents seeded")
    except Exception as e:
        print(f"Seed agents failed {e}")

    # seed siliconflow provider from env (so /models/specs shows Qwen)
    try:
        import os
        from deep_platform.storage.postgres.models import ModelProvider
        from deep_platform.config import settings
        async with SessionLocal() as db:
            q=await db.execute(select(ModelProvider).where(ModelProvider.name=="siliconflow-default"))
            if not q.scalars().first():
                default_model = settings.DEFAULT_MODEL or "siliconflow:Qwen/Qwen2.5-7B-Instruct"
                _, _, model_name = default_model.partition(":")
                prov=ModelProvider(
                    name="siliconflow-default",
                    provider="siliconflow",
                    api_key=settings.SILICONFLOW_API_KEY or "",
                    base_url=settings.SILICONFLOW_BASE_URL or "https://api.siliconflow.cn/v1",
                    models_json={"models":[model_name or "Qwen/Qwen2.5-7B-Instruct"]},
                )
                db.add(prov)
                await db.commit()
                print("SiliconFlow provider seeded")
    except Exception as e:
        print(f"Seed model provider failed {e}")

    yield
    print("=== Lifespan shutdown ===")
    from deep_platform.services.run_queue_service import close_queue_clients
    await close_queue_clients()
    await engine.dispose()
