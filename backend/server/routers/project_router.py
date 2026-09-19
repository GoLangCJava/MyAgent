from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from deep_platform.storage.postgres.manager import get_db
from deep_platform.storage.postgres.models import Project, User
from server.utils.auth import get_current_user
from pydantic import BaseModel
import os, uuid

project_router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

@project_router.get("/")
async def list_projects(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Project).where(Project.owner_id==current_user.id).order_by(Project.created_at.desc()))
    projs=q.scalars().all()
    return {"projects":[{"id":p.id,"name":p.name,"workdir_path":p.workdir_path,"description":p.description,"created_at":p.created_at} for p in projs]}

@project_router.post("/")
async def create_project(payload: ProjectCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from deep_platform.config import settings
    workdir=os.path.join(settings.WORKSPACE_BASE, current_user.id, f"{payload.name}_{uuid.uuid4().hex[:6]}")
    os.makedirs(workdir, exist_ok=True)
    proj=Project(name=payload.name, owner_id=current_user.id, workdir_path=workdir, description=payload.description)
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return {"project":{"id":proj.id,"name":proj.name,"workdir_path":proj.workdir_path}}

@project_router.get("/{project_id}/files")
async def list_files(project_id: str, path: str = "", current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Project).where(Project.id==project_id, Project.owner_id==current_user.id))
    proj=q.scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    base=proj.workdir_path
    target=os.path.join(base, path.lstrip("/"))
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        raise HTTPException(status_code=403, detail="Path traversal")
    if not os.path.exists(target):
        return {"files":[], "path":path}
    if os.path.isfile(target):
        return {"file":True, "path":path}
    files=[]
    for name in os.listdir(target):
        full=os.path.join(target, name)
        files.append({"name":name, "is_dir":os.path.isdir(full), "size":os.path.getsize(full) if os.path.isfile(full) else 0, "path": os.path.join(path, name)})
    return {"files":files, "path":path, "workdir":base}

@project_router.get("/{project_id}/files/content")
async def read_file(project_id: str, path: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q=await db.execute(select(Project).where(Project.id==project_id, Project.owner_id==current_user.id))
    proj=q.scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    base=proj.workdir_path
    target=os.path.join(base, path.lstrip("/"))
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        raise HTTPException(status_code=403, detail="Path traversal")
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            content=f.read(50000)
        return {"content":content, "path":path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
