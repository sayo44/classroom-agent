"""可选 TTS 模块（Edge TTS，中文女声）。

未安装 edge-tts 时降级，由前端用浏览器 speechSynthesis 兜底。
"""
try:
    import edge_tts

    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

import io


async def synthesize(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes:
    if not HAS_EDGE_TTS:
        raise RuntimeError("edge-tts 未安装")
    communicate = edge_tts.Communicate(text, voice)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()
