from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.manager import get_db
from deep_platform.storage.postgres.models import ModelProvider, User
from server.utils.auth import get_current_user, require_admin
from pydantic import BaseModel

model_router = APIRouter()

class ModelProviderCreate(BaseModel):
    name: str
    provider: str
    api_key: str = ""
    base_url: str = ""
    models_json: dict = {}

@model_router.get("/")
async def list_providers(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(ModelProvider).order_by(ModelProvider.created_at.desc()))
    providers=q.scalars().all()
    return {"providers":[{"id":p.id,"name":p.name,"provider":p.provider,"base_url":p.base_url,"models_json":p.models_json,"is_active":p.is_active} for p in providers]}

@model_router.post("/")
async def create_provider(payload: ModelProviderCreate, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(ModelProvider).where(ModelProvider.name==payload.name))
    if q.scalars().first():
        raise HTTPException(status_code=409, detail="Name exists")
    prov=ModelProvider(name=payload.name, provider=payload.provider, api_key=payload.api_key, base_url=payload.base_url, models_json=payload.models_json)
    db.add(prov)
    await db.commit()
    return {"success":True, "id":prov.id}

@model_router.delete("/{provider_id}")
async def delete_provider(provider_id: str, current_user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(ModelProvider).where(ModelProvider.id==provider_id))
    prov=q.scalars().first()
    if not prov:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(prov)
    await db.commit()
    return {"success":True}

@model_router.get("/specs")
async def list_model_specs(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(ModelProvider).where(ModelProvider.is_active==True))
    providers=q.scalars().all()
    specs=[]
    for p in providers:
        models=p.models_json.get("models",[]) if p.models_json else []
        for m in models:
            specs.append(f"{p.provider}:{m}")
    # fallback: 优先 SiliconFlow Qwen
    if not specs:
        from deep_platform.config import settings
        specs=[settings.DEFAULT_MODEL, "siliconflow:Qwen/Qwen2.5-7B-Instruct", "openai:gpt-4o-mini","openai:gpt-4o","anthropic:claude-3-5-sonnet-20241022"]
        # 去重保序
        specs=list(dict.fromkeys(specs))
    return {"specs":specs}
