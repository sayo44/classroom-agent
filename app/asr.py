"""本地语音识别（faster-whisper，后端进程内常驻）。

把 Whisper 模型包成进程内 API：浏览器录音 -> POST /api/transcribe -> 本函数本地转写。
模型权重放在仓库 models/faster-whisper-base/，运行时零联网、音频不出本机。
"""
import os

from app.config import BASE_DIR

MODEL_DIR = os.path.join(BASE_DIR, "models", "faster-whisper-base")

_model = None

# 初始提示：把识别语境锁定在幼儿园课堂，提升“邯郸学步”等专有词的命中率
INITIAL_PROMPT = (
    "以下是幼儿园课堂对话，由小朋友说话。请用简体中文准确转写儿童语音，"
    "常见词语包括：邯郸学步、故事、走路、成语、老师、小朋友。"
)

# 同音/近音纠错表：base 模型对儿童语音仍有少量谐音幻觉（如“含单”→“邯郸”），
# 这里用确定性的子串替换兜底。可被子智能体的 config.asr_corrections 合并/覆盖。
# 键按长度降序匹配，避免短词先替换破坏长词（如先处理“含单学步”再处理“含单”）。
DEFAULT_CORRECTIONS = {
    "含单学步": "邯郸学步",
    "含单": "邯郸",
    "小验子": "小燕子",
    "验国": "燕国",
}


def get_model():
    """懒加载并常驻 Whisper 模型（首次调用时载入内存，后续复用）。"""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        if not os.path.isdir(MODEL_DIR):
            raise RuntimeError(
                f"未找到本地 Whisper 模型：{MODEL_DIR}\n"
                "请先运行脚本预下载模型（见 README / 部署说明）。"
            )
        # int8 在 CPU 上速度与精度平衡最好；Apple Silicon 会自动走 Accelerate 加速
        _model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
    return _model


def _apply_corrections(text: str, corrections: dict | None) -> str:
    """按 key 长度降序做子串替换，避免短词先替换破坏长词。"""
    if not corrections:
        return text
    for wrong in sorted(corrections, key=len, reverse=True):
        if wrong:
            text = text.replace(wrong, corrections[wrong])
    return text


def transcribe_file(path: str, corrections: dict | None = None) -> str:
    """对音频文件（wav/mp3/flac/webm 等）做中文转写，返回文本。

    corrections: 可选同音纠错表 {错词: 正词}，会与 DEFAULT_CORRECTIONS 合并（传入优先）。
    """
    model = get_model()
    segments, _ = model.transcribe(
        path,
        language="zh",
        beam_size=5,
        vad_filter=True,          # 过滤静音段，减少幻觉
        initial_prompt=INITIAL_PROMPT,
    )
    text = "".join(getattr(s, "text", "") for s in segments).strip()
    # 转简体，方便幼儿园场景阅读（faster-whisper 默认偏繁体输出）
    try:
        from opencc import OpenCC

        text = OpenCC("t2s").convert(text)
    except Exception:
        pass
    # 同音纠错兜底：合并默认表与调用方传入的表（传入优先）
    merged = dict(DEFAULT_CORRECTIONS)
    if corrections:
        merged.update(corrections)
    text = _apply_corrections(text, merged)
    return text
