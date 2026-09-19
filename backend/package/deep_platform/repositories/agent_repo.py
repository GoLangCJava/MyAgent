from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.models import Agent

class AgentRepository:
    def __init__(self, db: AsyncSession): self.db=db
    async def get_by_slug(self, slug: str):
        q=await self.db.execute(select(Agent).where(Agent.slug==slug))
        return q.scalars().first()
    async def list_all(self, owner_id: str|None=None):
        stmt=select(Agent).order_by(Agent.created_at.desc())
        if owner_id:
            stmt=stmt.where((Agent.owner_id==owner_id)|(Agent.is_public==True))
        q=await self.db.execute(stmt)
        return q.scalars().all()
    async def create(self, **kwargs):
        obj=Agent(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        return obj
