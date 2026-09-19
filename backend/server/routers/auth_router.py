from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.manager import get_db
from deep_platform.storage.postgres.models import User
from deep_platform.utils.security import verify_password, hash_password, create_access_token
from server.utils.auth import get_current_user

auth_router = APIRouter()

class LoginIn(BaseModel):
    username: str
    password: str

class RegisterIn(BaseModel):
    username: str
    password: str
    email: str = ""

@auth_router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(User).where(User.username==payload.username))
    user=q.scalars().first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    token=create_access_token({"sub": user.id, "username": user.username})
    return {"access_token": token, "token_type":"bearer", "user":{"id":user.id, "username":user.username, "email":user.email, "is_admin":user.is_admin}}

@auth_router.post("/register")
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(User).where(User.username==payload.username))
    if q.scalars().first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    u=User(username=payload.username, email=payload.email, hashed_password=hash_password(payload.password))
    db.add(u)
    await db.commit()
    await db.refresh(u)
    token=create_access_token({"sub": u.id, "username": u.username})
    return {"access_token": token, "token_type":"bearer", "user":{"id":u.id, "username":u.username}}

@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id":current_user.id, "username":current_user.username, "email":current_user.email, "is_admin":current_user.is_admin, "is_superadmin":current_user.is_superadmin}

@auth_router.get("/users")
async def list_users(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    q=await db.execute(select(User).order_by(User.created_at.desc()))
    users=q.scalars().all()
    return {"users":[{"id":u.id, "username":u.username, "email":u.email, "is_admin":u.is_admin, "is_active":u.is_active, "created_at":u.created_at} for u in users]}
