"""可选 TTS 接口（Edge TTS）。未安装依赖时返回 501。"""
from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas import TTSRequest
from app.tts import synthesize, HAS_EDGE_TTS

router = APIRouter()


@router.post("/tts")
async def tts(body: TTSRequest):
    if not HAS_EDGE_TTS:
        return Response(status_code=501, content="TTS 未启用（未安装 edge-tts）")
    try:
        audio = await synthesize(body.text, body.voice)
    except Exception as e:
        return Response(status_code=500, content=f"TTS 失败：{e}")
    return Response(content=audio, media_type="audio/mpeg")
