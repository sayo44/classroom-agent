# 课堂智能体 · 体验版

一个**课堂互动简易智能体**平台，形态类似豆包智能体，但完全自主可控、可部署到自己服务器。

- 老师（PC 端）创建、调试、发布一个智能体
- 可配置：头像、人设、工作描述、知识库、开场问候语（可选）
- 发布后生成 H5 链接，学生/家长（手机端）用微信风格聊天窗对话
- 支持语音交互（说和听）
- **轻量化 · 无数据库 · 克隆即用 · 零运维**

技术栈：FastAPI（后端）+ 纯 HTML/CSS/JS（前端）+ 本地文件存储 + OpenAI 兼容 LLM 接口。

---

## 自动部署说明（面向 Coze / WorkBuddy 等 agent）

> 本仓库已附带示例智能体「聪聪」（邯郸学步成语故事），克隆后无需建库即可体验。
> agent 可直接按以下步骤执行，密钥请向用户索取，不要硬编码。

**环境要求**
- Python 3.10 或以上
- 可访问外网的机器（用于调用 LLM API）

**自动部署步骤（agent 可直接执行）**
1. 克隆仓库：`git clone <repo> && cd classroom-agent`
2. 建虚拟环境并装依赖：`python -m venv venv && venv/bin/pip install -r requirements.txt`
3. 配置环境变量：复制 `.env.example` 为 `.env`，写入 `LLM_API_KEY` 等（向用户索取密钥，不要写死）
4. 启动：`venv/bin/python run.py`
5. 验证：服务监听 `http://0.0.0.0:8000`，打开 `/` 看到管理端，`/c/congcong` 是示例聊天页

**运行时约定**
- 所有接口前缀 `/api`，页面由根路径托管
- 配置项集中在 `.env`，不写死在代码
- 智能体数据存 `data/agents/` 目录，首次运行自动创建，无需建库

---

## 手动使用

```bash
# 1. 安装依赖
python -m venv venv
venv/bin/pip install -r requirements.txt

# 2. 配置密钥
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（及可选的 LLM_BASE_URL / LLM_MODEL）

# 3. 启动
python run.py
```

打开浏览器：
- 管理端：`http://localhost:8000/`
- 示例聊天页：`http://localhost:8000/c/congcong`

---

## 目录结构

```
classroom-agent/
├── README.md
├── requirements.txt
├── .env.example
├── run.py                  # 启动入口
├── app/
│   ├── main.py             # FastAPI 实例 + 路由 + 静态托管
│   ├── config.py           # 读取 .env
│   ├── store.py            # 本地文件读写（无数据库）
│   ├── schemas.py          # 请求/响应结构
│   ├── llm.py              # LLM 调用层（拼 prompt + 调 API）
│   ├── knowledge.py        # 知识库文本处理
│   ├── publish.py          # 发布链接逻辑
│   ├── tts.py              # Edge TTS 封装（可选）
│   └── routers/            # agents / files / tts 路由
├── frontend/
│   ├── admin/              # 管理端（PC）
│   └── chat/               # H5 聊天页（手机）
├── data/agents/            # 每个智能体一个目录（无数据库）
│   └── congcong/           # 示例智能体
└── assets/
```

---

## 接口速览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | 智能体列表 |
| POST | `/api/agents` | 创建 |
| GET | `/api/agents/{slug}` | 详情 |
| PUT | `/api/agents/{slug}` | 更新 |
| DELETE | `/api/agents/{slug}` | 删除 |
| POST | `/api/agents/{slug}/avatar` | 上传头像 |
| POST | `/api/agents/{slug}/knowledge` | 上传知识文件 |
| GET | `/api/agents/{slug}/knowledge` | 知识列表 |
| DELETE | `/api/agents/{slug}/knowledge/{kid}` | 删除知识 |
| POST | `/api/agents/{slug}/chat` | 对话（支持流式） |
| POST | `/api/agents/{slug}/publish` | 发布，返回 H5 链接 |
| GET | `/c/{slug}` | H5 聊天页 |
| POST | `/api/tts` | 文本转语音（可选） |

---

## Windows 便携桌面版（自带 Python，免安装）

不想在每台电脑装 Python？本仓库附带一键脚本，把**嵌入式 Python 与全部依赖装进项目 `lib\` 目录**，用 `lib\python\python.exe` 直接运行，不写系统 PATH、不装系统 Python。

1. 把本仓库（或压缩包）放到任意目录
2. 双击 `install_windows.bat`：首次自动下载嵌入式 Python 3.11 到 `lib\python` 并安装依赖（**首次需联网**，之后离线可用），并生成 `.env`
3. 双击 `start_windows.bat`：前台启动，弹出课堂智能体桌面窗口；**控制台保持打开**，任何报错都会直接打印，便于排查
4. 浏览器访问：管理端 `http://localhost:8000/`、聊天页 `http://localhost:8000/c/congcong`

> 注意：pywebview 在 Windows 依赖系统自带的 **Microsoft Edge WebView2 Runtime**。若双击无窗口，先确认系统已装 WebView2（设置 → 应用 搜 WebView2；缺失则从微软官网装 Evergreen 版）。
> 语音模型 `models/` 不进仓库，首次运行若缺失，执行 `lib\python\python.exe scripts\download_model.py` 拉取（离线可用）。

---

## 常见问题

- **对话没反应**：检查 `.env` 里的 `LLM_API_KEY` 是否正确，以及 `LLM_BASE_URL` 是否可达。
- **语音不可用**：STT 依赖浏览器 Web Speech API（Chrome/Edge 支持最好）；TTS 未装 `edge-tts` 时自动降级为浏览器朗读。
- **想换模型**：改 `.env` 的 `LLM_MODEL`，或在管理端「模型」字段单独覆盖。
