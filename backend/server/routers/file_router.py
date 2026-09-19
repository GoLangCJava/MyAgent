from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from deep_platform.storage.postgres.models import User
from server.utils.auth import get_current_user
import os, uuid, aiofiles

file_router = APIRouter()

@file_router.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    from deep_platform.config import settings
    base=os.path.join(settings.WORKSPACE_BASE, current_user.id, "uploads")
    os.makedirs(base, exist_ok=True)
    ext=os.path.splitext(file.filename)[1]
    save_name=f"{uuid.uuid4().hex}{ext}"
    save_path=os.path.join(base, save_name)
    async with aiofiles.open(save_path, "wb") as out:
        content=await file.read()
        await out.write(content)
    return {"file_id":save_name, "filename":file.filename, "path":save_path, "size":len(content)}

@file_router.get("/workspace/list")
async def list_workspace(thread_id: str = "default", path: str = "", current_user: User = Depends(get_current_user)):
    from deep_platform.config import settings
    base=os.path.join(settings.WORKSPACE_BASE, thread_id)
    target=os.path.join(base, path.lstrip("/"))
    if not os.path.exists(base):
        os.makedirs(base, exist_ok=True)
        return {"files":[], "path":path}
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        raise HTTPException(status_code=403, detail="Path traversal")
    if os.path.isfile(target):
        return {"is_file":True}
    files=[]
    try:
        for name in os.listdir(target):
            full=os.path.join(target, name)
            files.append({"name":name, "is_dir":os.path.isdir(full), "size":os.path.getsize(full) if os.path.isfile(full) else 0, "path":os.path.join(path, name)})
    except FileNotFoundError:
        files=[]
    return {"files":files, "path":path, "base":base}
