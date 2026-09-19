import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.utils.lifespan import lifespan
from server.routers import router

app = FastAPI(title="Deep Platform - Fullstack", version="1.0.0", lifespan=lifespan)

# CORS
origins=os.getenv("CORS_ORIGINS","*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"name":"Deep Platform","version":"1.0.0","docs":"/docs","ready":"/api/system/ready"}

@app.get("/health")
async def health():
    return {"status":"ok"}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["server","package"])
