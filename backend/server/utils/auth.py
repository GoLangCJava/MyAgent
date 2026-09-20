from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.manager import get_db
from deep_platform.utils.security import decode_token
from deep_platform.storage.postgres.models import User

security = HTTPBearer(auto_error=False)

async def _user_from_token(token: str, db: AsyncSession):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token")
    q = await db.execute(select(User).where(User.id==uid))
    user = q.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await _user_from_token(creds.credentials, db)

async def get_current_user_sse(creds: HTTPAuthorizationCredentials = Depends(security), token: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    """SSE 专用: 浏览器 EventSource 发不出 Authorization 头, 允许 ?token= 传参"""
    raw = creds.credentials if creds else token
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await _user_from_token(raw, db)

async def get_optional_user(creds: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    if not creds:
        return None
    payload = decode_token(creds.credentials)
    if not payload:
        return None
    uid = payload.get("sub")
    q = await db.execute(select(User).where(User.id==uid))
    return q.scalars().first()

def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user
