from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.models import User

class UserRepository:
    def __init__(self, db: AsyncSession): self.db=db
    async def get_by_username(self, username: str):
        q=await self.db.execute(select(User).where(User.username==username))
        return q.scalars().first()
    async def get_by_id(self, uid: str):
        q=await self.db.execute(select(User).where(User.id==uid))
        return q.scalars().first()
    async def list_all(self):
        q=await self.db.execute(select(User).order_by(User.created_at.desc()))
        return q.scalars().all()
