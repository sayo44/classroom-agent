"""模型设置路由（体验版无数据库，存 data/settings.json）。

每个模型独立保存：base_url、api_key、model_id（实际参数值）、name（显示名称）。
"""
import re
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.store import get_settings, save_settings

router = APIRouter()


class ModelItem(BaseModel):
    id: str
    name: str
    base_url: str
    api_key: str  # 前端传 "********" 表示保持原值不变
    model_id: str


class SettingsUpdate(BaseModel):
    default_model: str = ""
    models: List[ModelItem] = []


def _normalize_base_url(url: str) -> str:
    """用户常复制完整 chat completions 地址，这里把后缀剥离成 OpenAI client 用的 base_url。"""
    url = (url or "").strip().rstrip("/")
    if not url:
        return ""
    # 去掉常见后缀：/v1/chat/completions、/chat/completions、/v1
    for suffix in ["/v1/chat/completions", "/chat/completions", "/v1"]:
        if url.lower().endswith(suffix):
            url = url[: -len(suffix)]
            break
    return url.rstrip("/")


def _mask_model_key(m: dict) -> dict:
    """返回前端时隐藏真实 API Key。"""
    out = dict(m)
    if out.get("api_key"):
        out["api_key"] = "********"
    return out


def _mask(settings: dict) -> dict:
    out = {
        "default_model": settings.get("default_model", ""),
        "models": [_mask_model_key(m) for m in settings.get("models", [])],
    }
    out["api_key_set"] = any(bool(m.get("api_key")) for m in settings.get("models", []))
    return out


@router.get("/settings")
def api_get_settings():
    return _mask(get_settings())


@router.put("/settings")
def api_update_settings(body: SettingsUpdate):
    current = get_settings()
    old_models = {m["id"]: m for m in current.get("models", [])}

    new_models = []
    for m in body.models:
        mid = (m.id or m.model_id or re.sub(r"[^a-z0-9_-]+", "-", (m.model_id or m.name).lower()).strip("-"))
        # 掩码占位符表示不修改原密钥
        api_key = m.api_key
        if api_key == "********" and mid in old_models:
            api_key = old_models[mid].get("api_key", "")
        new_models.append({
            "id": mid,
            "name": m.name or m.model_id,
            "base_url": _normalize_base_url(m.base_url),
            "api_key": api_key,
            "model_id": m.model_id or mid,
        })

    default_model = body.default_model or (new_models[0]["id"] if new_models else "")
    # 确保 default_model 在列表中
    if new_models and default_model not in {m["id"] for m in new_models}:
        default_model = new_models[0]["id"]

    updated = {"default_model": default_model, "models": new_models}
    save_settings(updated)
    return _mask(updated)
