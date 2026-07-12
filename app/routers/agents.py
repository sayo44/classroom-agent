"""智能体路由：CRUD + 对话 + 发布 + 头像上传。"""
import json
import os

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.schemas import AgentCreate, AgentUpdate, ChatRequest
from app.store import (
    list_agents,
    get_agent,
    create_agent,
    update_agent,
    delete_agent,
    publish_agent,
    save_avatar,
    _path,
)
from app.llm import chat_sync, chat_stream
from app.config import LLM_BASE_URL, LLM_MODEL
from app.store import get_settings

router = APIRouter()


@router.get("/config")
def api_config():
    # 不暴露密钥，只返回非敏感配置供管理端展示
    settings = get_settings()
    return {
        "default_model": settings.get("default_model") or LLM_MODEL,
        "models": [
            {"id": m.get("id"), "name": m.get("name"), "model_id": m.get("model_id")}
            for m in settings.get("models", [])
        ],
    }


@router.get("/agents")
def api_list():
    return list_agents()


@router.post("/agents")
def api_create(body: AgentCreate):
    return create_agent(body.dict())


@router.get("/agents/{slug}")
def api_get(slug: str):
    a = get_agent(slug)
    if not a:
        raise HTTPException(404, "智能体不存在")
    return a


@router.put("/agents/{slug}")
def api_update(slug: str, body: AgentUpdate):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    data = {k: v for k, v in body.dict().items() if v is not None}
    return update_agent(slug, data)


@router.delete("/agents/{slug}")
def api_delete(slug: str):
    ok = delete_agent(slug)
    if not ok:
        raise HTTPException(404, "智能体不存在")
    return {"ok": True}


@router.post("/agents/{slug}/avatar")
async def api_avatar(slug: str, file: UploadFile = File(...)):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    ext = os.path.splitext(file.filename)[1] or ".png"
    data = await file.read()
    avatar_file = save_avatar(slug, data, ext)
    update_agent(slug, {"avatar": avatar_file})
    return {"avatar": avatar_file}


@router.post("/agents/{slug}/publish")
def api_publish(slug: str):
    r = publish_agent(slug)
    if not r:
        raise HTTPException(404, "智能体不存在")
    return r


@router.get("/agents/{slug}/publish")
def api_publish_get(slug: str):
    a = get_agent(slug)
    if not a:
        raise HTTPException(404, "智能体不存在")
    return {"slug": a.get("slug"), "published": a.get("published", False)}


@router.post("/agents/{slug}/chat")
def api_chat(slug: str, body: ChatRequest):
    a = get_agent(slug)
    if not a:
        raise HTTPException(404, "智能体不存在")
    if body.stream:
        def gen():
            for piece in chat_stream(a, body.messages):
                yield f"data: {json.dumps({'content': piece}, ensure_ascii=False)}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream; charset=utf-8")
    return {"reply": chat_sync(a, body.messages)}
