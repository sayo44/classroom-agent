#!/usr/bin/env python3
"""预下载 faster-whisper 模型到项目本地目录（运行时零联网）。

用法：
    venv/bin/python scripts/download_model.py            # 默认下载 base
    venv/bin/python scripts/download_model.py --size tiny
    venv/bin/python scripts/download_model.py --size small

模型落点： models/faster-whisper-{size}/  （flat，根目录直接含 model.bin 等）
代码 app/asr.py 用 WhisperModel(MODEL_DIR) 加载，要求 flat 布局。
faster-whisper 默认会把模型下载成 HF hub 缓存布局（嵌套子目录），
本脚本负责展平，避免运行时报 'Unable to open file model.bin'。
"""
import os
import shutil
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE_DIR, ".hf_cache")

# 国内可访问的 HF 镜像；也可删掉这行走官方源
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("未找到 huggingface_hub，请先安装：venv/bin/pip install faster-whisper")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="base", choices=["tiny", "base", "small"])
    args = ap.parse_args()
    size = args.size
    repo = f"Systran/faster-whisper-{size}"
    DEST = os.path.join(BASE_DIR, "models", f"faster-whisper-{size}")

    print(f"正在从镜像下载 {repo} -> 缓存 {CACHE}")
    snap = snapshot_download(repo, cache_dir=CACHE)

    os.makedirs(DEST, exist_ok=True)
    for name in os.listdir(snap):
        src = os.path.join(snap, name)
        dst = os.path.join(DEST, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    print(f"模型已就绪：{DEST}")
    print("包含文件：", sorted(os.listdir(DEST)))


if __name__ == "__main__":
    main()
