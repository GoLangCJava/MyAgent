from fastapi import APIRouter
from .auth_router import auth_router
from .agent_router import agent_router
from .conversation_router import conversation_router
from .project_router import project_router
from .model_router import model_router
from .file_router import file_router
from .system_router import system_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(agent_router, prefix="/agent", tags=["agent"])
router.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
router.include_router(project_router, prefix="/projects", tags=["projects"])
router.include_router(model_router, prefix="/models", tags=["models"])
router.include_router(file_router, prefix="/files", tags=["files"])
router.include_router(system_router, prefix="/system", tags=["system"])
