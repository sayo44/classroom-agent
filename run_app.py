"""课堂智能体 · Web 版本地启动器（浏览器访问）

用项目自带 lib\\python 或系统 Python 跑均可。负责：选空闲端口、起 FastAPI 服务、
可选自动开浏览器、写诊断日志。不创建原生窗口——UI 就是系统浏览器。

用法：
  python run_app.py                  # 起服务，控制台可见日志
  OPEN_BROWSER=1 python run_app.py   # 起服务并自动用默认浏览器打开学生聊天页
"""
import os
import sys
import socket
import logging

# 强制 stdout/stderr 用 utf-8，避免 Windows 非 utf-8 locale（如 cp1252）打印中文时报 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 诊断日志：真机启动失败时，去 USER_DATA/launch.log 看最后记录即可定位
USER_DATA = os.path.join(os.path.expanduser("~"), "ClassroomAgent")
os.makedirs(USER_DATA, exist_ok=True)
LAUNCH_LOG = os.path.join(USER_DATA, "launch.log")
logging.basicConfig(
    filename=LAUNCH_LOG,
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("launch")


def find_free_port(start=8000, tries=30):
    """从 start 起找第一个未被占用的 127.0.0.1 端口。"""
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return None


def main():
    log.info("进入 main()")
    PORT = find_free_port(8000)
    if PORT is None:
        log.error("启动失败：8000-8029 端口均被占用")
        print("启动失败：8000-8029 端口均被占用，请关闭占用程序后重试。")
        return
    log.info("选定端口 %s", PORT)

    import uvicorn

    chat_url = f"http://127.0.0.1:{PORT}/c/congcong"
    admin_url = f"http://127.0.0.1:{PORT}/"
    print(f"[启动] 学生聊天页：{chat_url}")
    print(f"[启动] 老师管理端：{admin_url}")
    # 可选：自动用默认浏览器打开学生聊天页（动态端口也能正确打开）
    if os.getenv("OPEN_BROWSER"):
        import webbrowser
        try:
            webbrowser.open(chat_url)
            print(f"[启动] 已尝试在浏览器打开：{chat_url}")
        except Exception as e:
            print(f"[启动] 自动打开浏览器失败（请手动访问 {chat_url}）：{e}")

    log.info("启动 uvicorn host=127.0.0.1 port=%s", PORT)
    # 绑定 127.0.0.1（localhost 安全上下文，浏览器麦克风可用）；控制台保持打开便于排查
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=False, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        log.error("未捕获异常导致启动失败：\n%s", traceback.format_exc())
        # 真机启动失败时，弹窗提示并指向日志，避免用户完全看不到原因（Windows 专用）
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
