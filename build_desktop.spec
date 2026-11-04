# -*- mode: python ; coding: utf-8 -*-
"""课堂智能体桌面客户端打包配置（PyInstaller）。

用法：
  Windows:  pyinstaller build_desktop.spec
  macOS:    pyinstaller build_desktop.spec

重要：
  - PyInstaller 不能交叉编译，Windows 包只能在 Windows 上打，macOS 包只能在 Mac 上打。
  - data/settings.local.json（含真实 LLM 密钥）已被排除，不会进入安装包。
  - 语音模型 models/（约 216MB）全量打进，离线可用。
  - EXE/文件夹用英文名 ClassroomAgent，避开 Windows 路径与 CI 中文编码坑；窗口标题仍显示中文「课堂智能体」。
"""
import os
import sys

# PyInstaller 通过 exec() 执行本 spec，命名空间里没有 __file__，用 PyInstaller 提供的 SPECPATH（spec 所在目录）。
# 保留 __file__ 兜底，以便本地以其他非 PyInstaller 方式加载时也能用。
try:
    HERE = SPECPATH
except NameError:
    HERE = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "课堂智能体"
EXE_NAME = "ClassroomAgent"  # 英文产物名，避开 Windows 路径与 CI 中文编码问题


def collect_data_datas(base):
    """收集 data/ 下所有文件，但排除含真实密钥的 settings.local.json。"""
    out = []
    data_dir = os.path.join(base, "data")
    if not os.path.isdir(data_dir):
        return out
    for root, _dirs, files in os.walk(data_dir):
        for f in files:
            if f == "settings.local.json":
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            out.append((full, os.path.dirname(rel)))
    return out


def add_data(out, src_rel, dst):
    """仅当源路径存在才加入 datas，避免空目录/缺失目录导致 PyInstaller 报错。"""
    src = os.path.join(HERE, src_rel)
    if os.path.exists(src):
        out.append((src, dst))
    return out

datas = []
datas = add_data(datas, "frontend", "frontend")
datas = add_data(datas, "assets", "assets")
datas = add_data(datas, "models", "models")
datas = add_data(datas, ".env.example", ".env.example")
datas += collect_data_datas(HERE)

hiddenimports = [
    "app", "app.main", "app.config", "app.store", "app.llm", "app.asr", "app.tts",
    "app.knowledge", "app.publish", "app.schemas",
    "app.routers", "app.routers.agents", "app.routers.files",
    "app.routers.tts", "app.routers.transcribe", "app.routers.settings",
    "faster_whisper", "ctranslate2", "onnxruntime", "huggingface_hub",
    "opencc", "edge_tts", "openai", "uvicorn", "starlette", "pydantic",
    "python_dotenv", "multipart", "pywebview",
]

# 按平台补充 pywebview 平台模块（这些是通过字符串动态 import 的，PyInstaller 可能漏收集）
if sys.platform == "win32":
    hiddenimports += [
        "webview.platforms.edgechrome",
        "webview.platforms.winforms",
        "webview.platforms.mshtml",
    ]
elif sys.platform == "darwin":
    hiddenimports += ["webview.platforms.cocoa"]

a = Analysis(
    [os.path.join(HERE, "launch_desktop.py")],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],  # 端口异常仅控制台提示，避免打包 tkinter 增大体积
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # 桌面应用不弹控制台
    disable_windowed_traceback=False,
    argv_emulation=True,      # macOS 友好
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name=EXE_NAME,
)

app = BUNDLE(
    coll,
    name=APP_NAME + ".app",
    icon=None,
    bundle_identifier="com.classroomagent.desktop",
    info_plist={
        "NSMicrophoneUsageDescription": "课堂智能体需要麦克风，用于小朋友语音对话的本地转写。",
        "NSSpeechRecognitionUsageDescription": "课堂智能体需要语音识别，用于把小朋友的语音转成文字（本地处理，不上传）。",
        "NSRequiresAquaSystemAppearance": False,
    },
)
