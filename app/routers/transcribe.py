"""语音转写接口：接收前端上传的音频，本地 faster-whisper 转写为文字。

前端把录音在浏览器内解码成 16kHz 单声道 WAV 再上传，后端用 soundfile 直接读取，
不依赖 ffmpeg，手机/电脑浏览器通用。
"""
import os
import tempfile

from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse

from app.asr import transcribe_file
from app.store import get_agent

router = APIRouter()


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), slug: str = Form("")):
    data = await file.read()
    if not data:
        return JSONResponse(status_code=400, content={"error": "空音频"})

    # 按智能体取同音纠错表（config.asr_corrections）；无 slug 时仅用默认表
    corrections = None
    if slug:
        agent = get_agent(slug)
        if agent and agent.get("asr_corrections"):
            corrections = agent["asr_corrections"]

    # 依据上传类型选文件后缀，便于后端正确解码
    suffix = ".wav"
    ctype = (file.content_type or "").lower()
    if "webm" in ctype:
        suffix = ".webm"
    elif "mp3" in ctype or "mpeg" in ctype:
        suffix = ".mp3"
    elif "flac" in ctype:
        suffix = ".flac"
    elif "ogg" in ctype:
        suffix = ".ogg"

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(data)
            tmp = f.name
        text = transcribe_file(tmp, corrections=corrections)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"转写失败：{e}"})
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return {"text": text}
