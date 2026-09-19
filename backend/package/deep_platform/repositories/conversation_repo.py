from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.models import Conversation, Message

class ConversationRepository:
    def __init__(self, db: AsyncSession): self.db=db
    async def get_by_thread(self, thread_id: str):
        q=await self.db.execute(select(Conversation).where(Conversation.thread_id==thread_id))
        return q.scalars().first()
    async def list_by_user(self, uid: str, limit: int=50):
        q=await self.db.execute(select(Conversation).where(Conversation.uid==uid, Conversation.status!="deleted").order_by(Conversation.updated_at.desc()).limit(limit))
        return q.scalars().all()
    async def get_messages(self, thread_id: str, limit: int=100):
        q=await self.db.execute(select(Message).where(Message.thread_id==thread_id).order_by(Message.created_at.asc()).limit(limit))
        return q.scalars().all()
