"""本地文件存储（无数据库）。

每个智能体一个目录：data/agents/{slug}/
- config.json  人设/描述/开场白/模型/发布状态
- avatar.png   头像（可选）
- knowledge/   知识库文本（.txt/.md）
"""
import os
import json
import re
import shutil
from datetime import datetime

from app.config import AGENTS_DIR, DATA_DIR
from app.knowledge import get_knowledge_text


# 全局系统设置文件（模型/API Key 等）
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "default_model": "deepseek-v4-pro",
    "models": [
        {
            "id": "deepseek-v4-pro",
            "name": "DeepSeek V4 Pro",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "model_id": "deepseek-v4-pro",
        },
        {
            "id": "deepseek-v4-flash",
            "name": "DeepSeek V4 Flash",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "model_id": "deepseek-v4-flash",
        },
    ],
}


def ensure_dirs():
    os.makedirs(AGENTS_DIR, exist_ok=True)


def _migrate_old_settings(raw: dict) -> dict:
    """把旧版全局 base_url/api_key 配置迁移到每个模型条目上。"""
    if "models" not in raw or not isinstance(raw.get("models"), list):
        return dict(DEFAULT_SETTINGS)
    # 旧格式特征：顶层有 base_url/api_key，models 条目只有 id+name
    old_global_url = raw.get("base_url", "")
    old_global_key = raw.get("api_key", "")
    models = []
    for m in raw.get("models", []):
        if not isinstance(m, dict):
            continue
        new_m = {
            "id": m.get("id") or m.get("model_id") or "",
            "name": m.get("name") or m.get("id") or "未命名模型",
            "base_url": m.get("base_url") or old_global_url or DEFAULT_SETTINGS["models"][0]["base_url"],
            "api_key": m.get("api_key") if "api_key" in m else old_global_key,
            "model_id": m.get("model_id") or m.get("id") or "",
        }
        models.append(new_m)
    if not models:
        models = list(DEFAULT_SETTINGS["models"])
    return {
        "default_model": raw.get("default_model") or models[0]["id"],
        "models": models,
    }


def ensure_settings():
    """首次启动时写入默认系统设置。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)


def get_settings() -> dict:
    """读取系统设置；不存在则初始化默认值；自动迁移旧格式。"""
    ensure_settings()
    with open(SETTINGS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    # 新格式判断：models[0] 应含 base_url/model_id
    models = raw.get("models", [])
    if models and isinstance(models[0], dict) and ("base_url" in models[0] or "model_id" in models[0]):
        return raw
    migrated = _migrate_old_settings(raw)
    # 把迁移结果落盘，避免每次读取都重复迁移，也保证 UI 拿到的是新格式
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(migrated, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return migrated


def save_settings(settings: dict) -> dict:
    """保存系统设置。"""
    ensure_settings()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    return settings


def _path(slug: str) -> str:
    return os.path.join(AGENTS_DIR, slug)


def _config_path(slug: str) -> str:
    return os.path.join(_path(slug), "config.json")


def generate_slug(name: str) -> str:
    """根据名称生成唯一目录名（slug）。无数字 id，slug 即标识。"""
    base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "agent"
    slug = base
    i = 1
    while os.path.exists(_path(slug)):
        slug = f"{base}-{i}"
        i += 1
    return slug


def list_agents() -> list:
    ensure_dirs()
    result = []
    for slug in sorted(os.listdir(AGENTS_DIR)):
        cp = _config_path(slug)
        if os.path.isfile(cp):
            try:
                with open(cp, encoding="utf-8") as f:
                    result.append(json.load(f))
            except Exception:
                pass
    return result


def get_agent(slug: str) -> dict | None:
    cp = _config_path(slug)
    if not os.path.isfile(cp):
        return None
    with open(cp, encoding="utf-8") as f:
        a = json.load(f)
    # 兼容旧数据：config 没有 knowledge 字段时，从 knowledge/ 目录回填
    if "knowledge" not in a:
        a["knowledge"] = get_knowledge_text(slug)
    return a


def _write(agent: dict):
    slug = agent["slug"]
    os.makedirs(_path(slug), exist_ok=True)
    with open(_config_path(slug), "w", encoding="utf-8") as f:
        json.dump(agent, f, ensure_ascii=False, indent=2)


def create_agent(data: dict) -> dict:
    ensure_dirs()
    slug = generate_slug(data.get("name", "agent"))
    now = datetime.now().isoformat(timespec="seconds")
    agent = {
        "name": data.get("name", "未命名智能体"),
        "slug": slug,
        "persona": data.get("persona", ""),
        "description": data.get("description", ""),
        "opening": data.get("opening", ""),
        "model": data.get("model", ""),
        "avatar": data.get("avatar", ""),
        "knowledge": data.get("knowledge", ""),
        "published": False,
        "created_at": now,
        "updated_at": now,
    }
    _write(agent)
    return agent


def update_agent(slug: str, data: dict) -> dict | None:
    agent = get_agent(slug)
    if not agent:
        return None
    agent.update(data)
    agent["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write(agent)
    return agent


def delete_agent(slug: str) -> bool:
    p = _path(slug)
    if os.path.isdir(p):
        shutil.rmtree(p)
        return True
    return False


def publish_agent(slug: str) -> dict | None:
    agent = get_agent(slug)
    if not agent:
        return None
    agent["published"] = True
    agent["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write(agent)
    return {"slug": slug, "published": True}


def save_avatar(slug: str, data: bytes, ext: str) -> str:
    p = _path(slug)
    os.makedirs(p, exist_ok=True)
    avatar_file = "avatar" + (ext or ".png")
    with open(os.path.join(p, avatar_file), "wb") as f:
        f.write(data)
    return avatar_file
