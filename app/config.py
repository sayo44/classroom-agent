"""读取 .env 配置。所有配置集中在 .env，不写死在代码里。"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 仓库根目录（classroom-agent/）。
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 可写数据目录：默认用仓库 data/（开发模式 / lib 本地部署均可写）。
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
