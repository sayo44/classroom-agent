"""LLM 调用层（OpenAI 兼容接口）。

拼装 system prompt：人设 + 工作描述 + 开场风格 + 知识库文本，
带历史消息调用模型。支持流式输出（打字机效果）。
"""
import logging

from openai import OpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from app.knowledge import get_knowledge_text
from app.store import get_settings

logger = logging.getLogger("llm")


def _get_settings() -> dict:
    """读取系统设置，读取失败则返回空字典，避免影响主流程。"""
    try:
        return get_settings()
    except Exception:
        return {}

# 简繁转换缓存：模型可能默认输出繁体，统一转回简体（双保险）
_cc = None


def _to_simplified(text: str) -> str:
    """把文本转成简体中文；opencc 未安装时原样返回，不影响主流程。"""
    global _cc
    if _cc is None:
        try:
            from opencc import OpenCC

            _cc = OpenCC("t2s")
        except Exception:
            _cc = False
    if not _cc or not text:
        return text
    return _cc.convert(text)


def build_system_prompt(agent: dict) -> str:
    parts = [f"你是{agent.get('name', '智能体')}。{agent.get('persona', '')}"]
    if agent.get("description"):
        # 用显式分区 + 强调语，提升模型对长串工作描述的遵循度
        parts.append(
            "【你的工作任务 · 必须严格遵循】\n" + agent["description"]
        )
    if agent.get("opening"):
        parts.append(f"【开场白参考】首次见面可用类似语气打招呼：{agent['opening']}")
    kb = agent.get("knowledge") or get_knowledge_text(agent.get("slug", ""))
    if kb:
        parts.append("【参考资料 · 仅用于回答时参考，不要逐字背诵】\n" + kb)
    # 通用硬性约束：把角色设定里最易被忽略的否定式规则单独强调
    parts.append(
        "【绝对约束 · 违反任意一条都不允许】\n"
        "1. 只输出你（智能体）说的话，严禁描写自己的表情、动作、心理活动。\n"
        "2. 严禁使用“昨天”“以前”“上周”等模糊时间词，只能用“有一天”“很久很久以前”。\n"
        "3. 用幼儿园孩子能听懂的大白话，不堆难词、不卖弄。\n"
        "4. 紧扣本智能体负责的 topic 回答，孩子问什么耐心答，偶尔用提问引导他思考。\n"
        "5. 必须用简体中文回复，全程不得出现任何繁体字。"
    )
    return "\n\n".join(parts)


def _find_model_config(model_id: str) -> dict | None:
    """根据 model_id 从模型设置里找到对应配置（含 base_url/api_key）。"""
    settings = _get_settings()
    for m in settings.get("models", []):
        if m.get("id") == model_id or m.get("model_id") == model_id:
            return m
    return None


def _resolve_model(agent: dict) -> tuple[str, dict]:
    """确定实际调用模型及其配置：智能体指定 > 系统默认 > .env 兜底。"""
    settings = _get_settings()
    model_id = agent.get("model") or settings.get("default_model") or LLM_MODEL
    config = _find_model_config(model_id)
    if config:
        return config.get("model_id") or model_id, config
    # 如果找不到配置（比如用户手动填了 .env 里的模型），按 .env 兜底
    return model_id, {"base_url": LLM_BASE_URL, "api_key": LLM_API_KEY, "model_id": model_id}


def get_client_for_config(config: dict) -> OpenAI:
    base_url = config.get("base_url") or LLM_BASE_URL
    api_key = config.get("api_key") or LLM_API_KEY
    return OpenAI(base_url=base_url, api_key=api_key)


def _friendly_error(e: Exception) -> str:
    """把模型调用的异常转成用户能看懂的中文提示，避免前端白屏/500。"""
    msg = str(e)
    low = msg.lower()
    if "402" in msg or "insufficient" in low or "balance" in low:
        return "（调用模型失败：账户余额不足，请到 DeepSeek 平台充值后重试～）"
    if "401" in msg or "auth" in low or "invalid api key" in low:
        return "（调用模型失败：API Key 无效，请检查 .env 中的 LLM_API_KEY～）"
    if "connect" in low or "timeout" in low or "network" in low:
        return "（调用模型失败：网络连不上模型服务，请检查服务器网络～）"
    return "（调用模型出错啦，请稍后再试，或查看服务日志～）"


def _api_key_configured(model_config: dict | None = None) -> bool:
    if model_config:
        return bool(model_config.get("api_key") or LLM_API_KEY)
    settings = _get_settings()
    return any(bool(m.get("api_key")) for m in settings.get("models", [])) or bool(LLM_API_KEY)


def chat_sync(agent: dict, messages: list) -> str:
    model_id, config = _resolve_model(agent)
    if not _api_key_configured(config):
        return "（未配置 API Key，请先在模型设置或 .env 中填写模型密钥后重试～）"
    try:
        client = get_client_for_config(config)
        system = build_system_prompt(agent)
        full = [{"role": "system", "content": system}] + messages
        resp = client.chat.completions.create(model=model_id, messages=full)
        return _to_simplified(resp.choices[0].message.content or "")
    except Exception as e:
        logger.exception("LLM chat_sync failed")
        return _friendly_error(e)


def chat_stream(agent: dict, messages: list):
    model_id, config = _resolve_model(agent)
    if not _api_key_configured(config):
        yield {"content": "（未配置 API Key，请先在模型设置或 .env 中填写模型密钥后重试～）", "error": True}
        return
    try:
        client = get_client_for_config(config)
        system = build_system_prompt(agent)
        full = [{"role": "system", "content": system}] + messages
        stream = client.chat.completions.create(model=model_id, messages=full, stream=True)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield {"content": _to_simplified(delta)}
    except Exception as e:
        logger.exception("LLM chat_stream failed")
        yield {"content": _friendly_error(e), "error": True}
