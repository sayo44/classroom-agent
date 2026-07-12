"""请求/响应结构定义（pydantic）。"""
from typing import Optional, List
from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    persona: str = ""
    description: str = ""
    opening: str = ""
    model: str = ""
    avatar: str = ""
    knowledge: str = ""


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    persona: Optional[str] = None
    description: Optional[str] = None
    opening: Optional[str] = None
    model: Optional[str] = None
    avatar: Optional[str] = None
    knowledge: Optional[str] = None


class ChatRequest(BaseModel):
    # 前端传入完整消息数组（历史 + 本次用户消息）
    messages: List[dict] = []
    stream: bool = False


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
