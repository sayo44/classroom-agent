"""课堂智能体 · 桌面客户端启动器

把 FastAPI 后端以本地子进程方式启动（绑定 127.0.0.1，localhost 为安全上下文，麦克风可用），
再用 pywebview 开原生窗口加载学生聊天页。不改动现有 run.py / config.py / main.py 的默认行为。

原理：
- 开发模式：资源就在项目根，BASE_DIR = 项目根。
- 打包模式（PyInstaller）：资源解压到 sys._MEIPASS，BASE_DIR = sys._MEIPASS（只读）。
  运行时数据（.env、agents、settings.local.json）复制到用户可写目录 APP_DATA_DIR。
"""
import os
import sys
import socket
import threading
import time
import shutil
import webview

FROZEN = getattr(sys, "frozen", False)


def resource_path(rel):
    """打包后指向 sys._MEIPASS 内的资源；开发时指向项目根。"""
    if FROZEN:
        return os.path.join(sys._MEIPASS, rel)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


# 项目根加入 sys.path（开发模式保证 import app 可用）
BASE_DIR = resource_path("")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def resolve_user_data():
    """返回用户可写数据目录（跨平台）。"""
    if os.name == "nt":
        base = os.getenv("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "ClassroomAgent")
    else:
        path = os.path.expanduser("~/Library/Application Support/ClassroomAgent")
    os.makedirs(path, exist_ok=True)
    return path


USER_DATA = resolve_user_data()
PORT = None  # 运行时确定


def init_user_data():
    """首次运行：把包内 data 模板（排除密钥文件）与 .env.example 复制到用户目录。"""
    # data 模板（排除含真实密钥的 settings.local.json）
    src_data = resource_path("data")
    dst_data = os.path.join(USER_DATA, "data")
    os.makedirs(dst_data, exist_ok=True)
    if os.path.isdir(src_data):
        for name in os.listdir(src_data):
            if name == "settings.local.json":
                continue  # 绝不复制真实密钥
            s = os.path.join(src_data, name)
            d = os.path.join(dst_data, name)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    shutil.copytree(s, d)
            elif not os.path.exists(d):
                shutil.copy2(s, d)
    # .env（首次从 .env.example 复制；若不存在则创建空文件，用户自行填 LLM_API_KEY）
    env_path = os.path.join(USER_DATA, ".env")
    if not os.path.exists(env_path):
        example = resource_path(".env.example")
        if os.path.exists(example):
            shutil.copy2(example, env_path)
        else:
            open(env_path, "w", encoding="utf-8").close()
    # 切到用户目录，使 config.load_dotenv() 读到 USER_DATA/.env
    os.chdir(USER_DATA)


def find_free_port(start=8000, tries=30):
    """从 start 起找第一个未被占用的 127.0.0.1 端口。"""
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return None


def run_server(port):
    """在子线程启动 uvicorn（仅本机回环，localhost 为安全上下文）。"""
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False, log_level="warning")


# ---- pywebview 菜单 / JS 桥 ----
main_window = None


def open_admin():
    if main_window is not None:
        main_window.load_url(f"http://127.0.0.1:{PORT}/")


def open_chat():
    if main_window is not None:
        main_window.load_url(f"http://127.0.0.1:{PORT}/c/congcong")


class JsApi:
    """暴露给前端（可选调用）：pywebview.api.open_admin() / open_chat()"""

    def open_admin(self):
        open_admin()

    def open_chat(self):
        open_chat()


def main():
    global PORT, main_window

    # 桌面模式下把运行时数据目录交给 config
    if FROZEN:
        os.environ["APP_DATA_DIR"] = USER_DATA

    init_user_data()

    PORT = find_free_port(8000)
    if PORT is None:
        print("启动失败：8000-8029 端口均被占用，请关闭占用程序后重试。")
        return

    server_thread = threading.Thread(target=run_server, args=(PORT,), daemon=True)
    server_thread.start()
    # 等后端起来
    time.sleep(2.5)

    # 无界面模式（CI 冒烟测试 / 纯服务端部署）：只起后端，不创建原生窗口
    if os.getenv("NO_GUI"):
        print(f"[NO_GUI] 后端已启动：http://127.0.0.1:{PORT}/c/congcong")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    menu = [
        webview.MenuAction("打开老师管理端", open_admin),
        webview.MenuSeparator(),
        webview.MenuAction("返回学生聊天", open_chat),
    ]
    main_window = webview.create_window(
        title="课堂智能体",
        url=f"http://127.0.0.1:{PORT}/c/congcong",
        js_api=JsApi(),
        width=1100,
        height=760,
        text_select=True,
        confirm_close=True,
    )
    try:
        webview.start(menu=menu)
    except TypeError:
        # 旧版 pywebview 不支持 menu 参数时回退
        webview.start()


if __name__ == "__main__":
    main()
