"""发布逻辑。

slug 即目录名，也是发布链接标识。发布只是把 config.json 的 published 置真。
H5 链接：{base_url}/c/{slug}
"""
from app.config import HOST, PORT


def publish_url(slug: str, base_url: str | None = None) -> str:
    if not base_url:
        base_url = f"http://{HOST}:{PORT}"
    return f"{base_url.rstrip('/')}/c/{slug}"
