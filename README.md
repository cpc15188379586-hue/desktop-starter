# Tauri 2 + Vue 3 + Python 桌面应用骨架

一个可在 macOS / Windows 分别构建的最小项目骨架：

- 桌面外壳：Tauri 2
- 前端：Vue 3 + TypeScript + Vite
- 本地后端：Python + FastAPI
- 通信：HTTP（127.0.0.1）+ 随机启动令牌
- Python 打包：PyInstaller onefile（便于作为单个 sidecar 分发）
- Python 后端按需启动；前端退出时尝试结束子进程

> 这是开发骨架，不包含 AI/RAG 模型依赖。先验证跨平台启动、通信和打包，再逐步加入业务模块。

## 目录

```text
desktop-starter/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   ├── requirements.txt
│   └── build.py
└── src-tauri/
    ├── binaries/              # 放置各平台编译后的 Python sidecar
    ├── capabilities/
    ├── src/
    ├── Cargo.toml
    └── tauri.conf.json
```

## 运行开发环境

### 1. 安装依赖

需要 Node.js、Rust、Python 3.12+。Tauri 的系统依赖请按官方文档安装：
https://v2.tauri.app/start/prerequisites/

```bash
cd frontend
npm install
npm install @tauri-apps/api @tauri-apps/plugin-shell
npm install -D @tauri-apps/cli
```

Python 环境：

```bash
cd ../backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. 先单独测试 Python API

```bash
cd backend
python -m app.main --port 18765 --token dev-token
```

另开终端：

```bash
curl -H "X-App-Token: dev-token" http://127.0.0.1:18765/api/health
```

### 3. 开发模式

当前骨架的 Tauri 前端会启动 sidecar，因此先构建 sidecar，再运行 Tauri。

```bash
# 在 backend 目录，激活虚拟环境后
python build.py
```

把生成的单个可执行文件复制到 `src-tauri/binaries/`，并按当前机器的 Rust target 命名：

- macOS Apple Silicon：`python-backend-aarch64-apple-darwin`
- macOS Intel：`python-backend-x86_64-apple-darwin`
- Windows x64：`python-backend-x86_64-pc-windows-msvc.exe`

然后：

```bash
cd ../frontend
npm run tauri -- dev
```

注意：Tauri externalBin 要求文件名带 Rust target triple。不同平台分别构建，不能把 macOS 二进制直接放进 Windows 安装包。

## 构建发布包

在目标操作系统上构建对应 sidecar，然后：

```bash
cd frontend
npm run tauri build
```

输出位置通常在 `src-tauri/target/release/bundle/`。

## 关键设计说明

1. Python 后端不是随系统启动的服务，只由桌面应用拉起。
2. 前端生成随机 token，作为 sidecar 参数传给 Python；HTTP 请求必须携带 `X-App-Token`。
3. API 只监听 `127.0.0.1`，不要监听 `0.0.0.0`。
4. 示例使用固定端口 `18765`，正式产品建议改成动态端口：Python 绑定端口 `0`，把实际端口通过 stdout 输出给 Tauri，再由前端读取。
5. 关闭窗口时会尝试 kill sidecar。正式版还应在 Rust 层实现更可靠的进程生命周期管理，避免前端异常退出后残留进程。
6. 不要把 PyTorch、Transformers 等重型依赖放进基础环境。按 AI 功能拆分可选依赖或独立 worker。

## 后续建议

- `backend/app/modules/ai/`：模型 API 抽象
- `backend/app/modules/rag/`：文档解析、切片、检索
- `backend/app/modules/agent/`：Agent 编排
- `backend/app/modules/document/`：PDF / Office 处理
- `backend/app/modules/ocr/`：OCR
- `frontend/src/features/`：按业务功能拆分前端
# desktop-starter
# desktop-starter
# desktop-starter
# desktop-starter
