"""读取 .env 配置。所有配置集中在 .env，不写死在代码里。"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 仓库根目录（classroom-agent/）。
# 打包后（PyInstaller 冻结模式）Python 模块被收进 PYZ 归档，__file__ 是虚拟路径，
# 两层 dirname 解析出的目录里并没有 frontend/models/data；这些资源被打进 sys._MEIPASS，
# 必须以它为准，否则前端/静态挂载在启动时就会因目录不存在而崩溃。
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 可写数据目录：桌面客户端打包后资源在 sys._MEIPASS 内（只读），launcher 会把用户目录写到
# APP_DATA_DIR（存 .env、agents、settings.local.json 等运行时数据）；开发模式不设该变量，默认用仓库 data/。
# 若用户目录 data 尚未就绪（首次复制失败等），回退到包内内置 data（只读但完整），保证后端可启动。
_USER_DATA = os.getenv("APP_DATA_DIR")
if _USER_DATA and os.path.isdir(os.path.join(_USER_DATA, "data")):
    DATA_DIR = os.path.join(_USER_DATA, "data")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")
AGENTS_DIR = os.path.join(DATA_DIR, "agents")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# LLM 接入（OpenAI 兼容接口，换模型只改这里）
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4.1")

# 服务监听
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
