from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from deep_platform.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with SessionLocal() as session:
        yield session

async def init_models():
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # seed admin
    from sqlalchemy import select
    from .models import User
    from deep_platform.utils.security import hash_password
    async with SessionLocal() as db:
        q = await db.execute(select(User).where(User.username=="admin"))
        if not q.scalars().first():
            u = User(username="admin", email="admin@local", hashed_password=hash_password("admin123"), is_admin=True, is_superadmin=True)
            db.add(u)
            await db.commit()
            print("Seeded admin / admin123")
