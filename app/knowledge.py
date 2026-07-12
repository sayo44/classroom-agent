"""知识库文本处理。

体验版：知识直接存本地文件，对话时全部读取拼接进 prompt，不引向量库。
"""
import os

from app.config import AGENTS_DIR

ALLOWED_EXT = (".txt", ".md")


def knowledge_dir(slug: str) -> str:
    return os.path.join(AGENTS_DIR, slug, "knowledge")


def get_knowledge_text(slug: str) -> str:
    d = knowledge_dir(slug)
    if not os.path.isdir(d):
        return ""
    texts = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(ALLOWED_EXT):
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                texts.append(f.read().strip())
    return "\n\n".join(t for t in texts if t)


def list_knowledge(slug: str) -> list:
    d = knowledge_dir(slug)
    if not os.path.isdir(d):
        return []
    items = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(ALLOWED_EXT):
            p = os.path.join(d, fn)
            items.append({"kid": fn, "title": fn, "size": os.path.getsize(p)})
    return items


def save_knowledge_file(slug: str, filename: str, content: str) -> dict:
    d = knowledge_dir(slug)
    os.makedirs(d, exist_ok=True)
    safe = os.path.basename(filename)
    if not safe.endswith(ALLOWED_EXT):
        safe += ".txt"
    with open(os.path.join(d, safe), "w", encoding="utf-8") as f:
        f.write(content)
    return {"kid": safe, "title": safe}


def delete_knowledge(slug: str, kid: str) -> bool:
    p = os.path.join(knowledge_dir(slug), os.path.basename(kid))
    if os.path.exists(p):
        os.remove(p)
        return True
    return False
