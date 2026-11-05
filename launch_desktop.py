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

# 强制 stdout/stderr 用 utf-8，避免 Windows（非 utf-8 locale，如 cp1252）打印中文时报 UnicodeEncodeError
# 对打包后的 exe 与本地 Windows 用户同样有效
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

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

import logging
# 启动诊断日志：console=False 会吞掉所有 stdout/stderr，真机双击无反应时无法排查。
# 这里把关键步骤与未捕获异常写文件，双击无窗口时直接看本文件即可定位。
LAUNCH_LOG = os.path.join(USER_DATA, "launch.log")
logging.basicConfig(
    filename=LAUNCH_LOG,
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("launch")


def _safe_copy(src, dst):
    """健壮复制：纯二进制读-写，绕开 Windows 上 shutil.copy2/CopyFile2 对只读或隐藏源文件
    （如 .env.example）的权限怪癖。失败仅告警，不抛异常（复制模板不是启动的硬性前提）。"""
    try:
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)
        return True
    except OSError as e:
        print(f"[WARN] 复制失败 {src} -> {dst}: {e}", file=sys.stderr)
        return False


def init_user_data():
    """首次运行：把包内 data 模板（排除密钥文件）与 .env.example 复制到用户目录。
    任何复制失败都只告警、不致命，保证后端一定能启动。"""
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
                    try:
                        shutil.copytree(s, d)
                    except OSError as e:
                        print(f"[WARN] copytree 失败 {s}: {e}", file=sys.stderr)
            elif not os.path.exists(d):
                _safe_copy(s, d)
    # .env（首次从 .env.example 复制；若复制或源缺失则创建空文件，用户自行填 LLM_API_KEY）
    env_path = os.path.join(USER_DATA, ".env")
    if not os.path.exists(env_path):
        example = resource_path(".env.example")
        print(f"[DEBUG] USER_DATA={USER_DATA} example={example} exists={os.path.exists(example)}", file=sys.stderr)
        created = False
        if os.path.exists(example):
            created = _safe_copy(example, env_path)
        if not created:
            try:
                open(env_path, "w", encoding="utf-8").close()
            except OSError as e:
                print(f"[WARN] 创建空 .env 失败（后端将以默认配置启动）: {e}", file=sys.stderr)
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


def build_menu():
    """兼容 pywebview 4.x 与 5.x 的菜单 API。

    4.x：webview.MenuAction / webview.MenuSeparator 在顶层，start(menu=[...]) 直接传列表。
    5.x：这些移到 webview.menu 子模块，且顶层菜单必须用 Menu(title, items=[...]) 包裹。
    取不到菜单 API 时返回 None，调用方降级为无菜单启动（管理端仍可经页面按钮切换）。
    """
    try:
        from webview.menu import Menu, MenuAction, MenuSeparator
        return Menu("课堂智能体", [
            MenuAction("打开老师管理端", open_admin),
            MenuSeparator(),
            MenuAction("返回学生聊天", open_chat),
        ])
    except (ImportError, AttributeError):
        pass
    try:
        MenuAction = webview.MenuAction
        MenuSeparator = webview.MenuSeparator
        return [
            MenuAction("打开老师管理端", open_admin),
            MenuSeparator(),
            MenuAction("返回学生聊天", open_chat),
        ]
    except AttributeError:
        return None


def main():
    global PORT, main_window
    log.info("进入 main()，FROZEN=%s", FROZEN)

    # 桌面模式下把运行时数据目录交给 config。
    # 仅当用户目录 data 已就绪（init_user_data 复制成功）才切换；否则 config 回退到
    # 包内 _MEIPASS/data（只读但完整），保证后端即使复制失败也能正常启动。
    if FROZEN and os.path.isdir(os.path.join(USER_DATA, "data")):
        os.environ["APP_DATA_DIR"] = USER_DATA

    init_user_data()
    log.info("init_user_data 完成")

    PORT = find_free_port(8000)
    if PORT is None:
        log.error("启动失败：8000-8029 端口均被占用")
        print("启动失败：8000-8029 端口均被占用，请关闭占用程序后重试。")
        return
    log.info("选定端口 %s", PORT)

    server_thread = threading.Thread(target=run_server, args=(PORT,), daemon=True)
    server_thread.start()
    log.info("后端线程已启动，等待 2.5s 让 uvicorn 起来")
    # 等后端起来
    time.sleep(2.5)

    # 无界面模式（CI 冒烟测试 / web 版本地部署）：只起后端，不创建原生窗口
    if os.getenv("NO_GUI"):
        chat_url = f"http://127.0.0.1:{PORT}/c/congcong"
        admin_url = f"http://127.0.0.1:{PORT}/"
        log.info("NO_GUI 模式，仅起后端，不创建窗口")
        print(f"[NO_GUI] 后端已启动：{chat_url}")
        print(f"[NO_GUI] 管理端：{admin_url}")
        # web 版本地部署：起好后自动用默认浏览器打开学生聊天页（动态端口也能正确打开）
        if os.getenv("OPEN_BROWSER"):
            import webbrowser
            try:
                webbrowser.open(chat_url)
                print(f"[NO_GUI] 已尝试在浏览器打开：{chat_url}")
            except Exception as e:
                print(f"[NO_GUI] 自动打开浏览器失败（请手动访问 {chat_url}）：{e}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    menu = build_menu()
    log.info("创建 pywebview 窗口，URL=http://127.0.0.1:%s/c/congcong", PORT)
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
        log.info("调用 webview.start()（menu=%s）", "有" if menu is not None else "无")
        if menu is not None:
            webview.start(menu=menu)
        else:
            webview.start()
    except TypeError:
        # 旧版 pywebview 不支持 menu 参数时回退
        log.warning("webview.start(menu=...) 不支持，回退无菜单")
        webview.start()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log.error("未捕获异常导致启动失败：\n%s", traceback.format_exc())
        # 真机双击无反应时，弹窗提示并指向日志，避免用户完全看不到原因
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"课堂智能体启动失败，详见日志：\n{LAUNCH_LOG}",
                "启动失败",
                0x10,
            )
        except Exception:
            pass
