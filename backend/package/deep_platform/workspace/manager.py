import os
from deep_platform.config import settings

def get_thread_workspace(thread_id: str):
    base=os.path.join(settings.WORKSPACE_BASE, thread_id)
    os.makedirs(base, exist_ok=True)
    return base

def list_workspace_files(thread_id: str, subpath: str=""):
    base=get_thread_workspace(thread_id)
    target=os.path.join(base, subpath.lstrip("/"))
    if not os.path.abspath(target).startswith(os.path.abspath(base)):
        raise ValueError("Path traversal")
    if not os.path.exists(target):
        return []
    if os.path.isfile(target):
        return [{"name":os.path.basename(target), "is_dir":False, "size":os.path.getsize(target), "path":subpath}]
    files=[]
    for name in os.listdir(target):
        full=os.path.join(target, name)
        files.append({"name":name, "is_dir":os.path.isdir(full), "size":os.path.getsize(full) if os.path.isfile(full) else 0, "path": os.path.join(subpath, name)})
    return files
