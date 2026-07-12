"""FastAPI 应用入口：挂载路由 + 静态托管。

后端只出 API 和静态文件，不服务端渲染页面。
前端（管理端 + H5）作为静态文件由本服务托管。
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import agents, files, tts, transcribe, settings
from app.config import FRONTEND_DIR, ASSETS_DIR, DATA_DIR
from app.store import ensure_dirs

ensure_dirs()

app = FastAPI(title="课堂智能体 · 体验版", version="1.0.0")

app.include_router(agents.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(transcribe.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/")
def admin_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin", "index.html"))


@app.get("/c/{slug}")
def chat_page(slug: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "chat", "chat.html"))


# 静态资源托管
app.mount("/static/admin", StaticFiles(directory=os.path.join(FRONTEND_DIR, "admin")), name="admin_static")
app.mount("/static/chat", StaticFiles(directory=os.path.join(FRONTEND_DIR, "chat")), name="chat_static")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
