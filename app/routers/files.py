"""知识库文件上传 / 列表 / 读取 / 编辑 / 删除。"""
import os

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.store import get_agent
from app.knowledge import (
    save_knowledge_file,
    list_knowledge,
    delete_knowledge,
    knowledge_dir,
)

router = APIRouter()


class KnowledgeText(BaseModel):
    filename: str
    content: str


@router.get("/agents/{slug}/knowledge")
def knowledge_list(slug: str):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    return list_knowledge(slug)


@router.post("/agents/{slug}/knowledge")
async def upload_knowledge(slug: str, file: UploadFile = File(...)):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    content = (await file.read()).decode("utf-8", errors="ignore")
    return save_knowledge_file(slug, file.filename, content)


@router.post("/agents/{slug}/knowledge/text")
def knowledge_save_text(slug: str, body: KnowledgeText):
    """在线新建/编辑知识文本（按文件名覆盖写）。"""
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    if not body.filename.strip():
        raise HTTPException(400, "文件名不能为空")
    return save_knowledge_file(slug, body.filename.strip(), body.content)


@router.get("/agents/{slug}/knowledge/{kid}")
def knowledge_get(slug: str, kid: str):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    p = os.path.join(knowledge_dir(slug), os.path.basename(kid))
    if not os.path.exists(p):
        raise HTTPException(404, "知识不存在")
    with open(p, encoding="utf-8") as f:
        content = f.read()
    return {"kid": kid, "title": kid, "content": content}


@router.delete("/agents/{slug}/knowledge/{kid}")
def knowledge_delete(slug: str, kid: str):
    if not get_agent(slug):
        raise HTTPException(404, "智能体不存在")
    ok = delete_knowledge(slug, kid)
    if not ok:
        raise HTTPException(404, "知识不存在")
    return {"ok": True}
