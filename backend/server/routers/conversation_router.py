from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.manager import get_db
from deep_platform.storage.postgres.models import Conversation, Message, User
from server.utils.auth import get_current_user
from pydantic import BaseModel

conversation_router = APIRouter()

class ConversationUpdate(BaseModel):
    title: str | None = None

@conversation_router.get("/")
async def list_conversations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Conversation).where(Conversation.uid==current_user.id, Conversation.status!="deleted").order_by(Conversation.updated_at.desc()).limit(100))
    convs=q.scalars().all()
    return {"conversations":[{"id":c.id,"thread_id":c.thread_id,"title":c.title,"agent_slug":c.agent_slug,"model_spec":c.model_spec,"created_at":c.created_at,"updated_at":c.updated_at} for c in convs]}

@conversation_router.get("/{thread_id}")
async def get_conversation(thread_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Conversation).where(Conversation.thread_id==thread_id, Conversation.uid==current_user.id))
    conv=q.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    mq=await db.execute(select(Message).where(Message.thread_id==thread_id).order_by(Message.created_at.asc()).limit(200))
    msgs=mq.scalars().all()
    return {"conversation":{"id":conv.id,"thread_id":conv.thread_id,"title":conv.title,"agent_slug":conv.agent_slug,"model_spec":conv.model_spec}, "messages":[{"id":m.id,"role":m.role,"content":m.content,"run_id":m.run_id,"created_at":m.created_at} for m in msgs]}

@conversation_router.put("/{thread_id}")
async def update_conversation(thread_id: str, payload: ConversationUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Conversation).where(Conversation.thread_id==thread_id, Conversation.uid==current_user.id))
    conv=q.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.title is not None:
        conv.title=payload.title
    await db.commit()
    return {"success":True}

@conversation_router.delete("/{thread_id}")
async def delete_conversation(thread_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Conversation).where(Conversation.thread_id==thread_id, Conversation.uid==current_user.id))
    conv=q.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Not found")
    conv.status="deleted"
    await db.commit()
    return {"success":True}
