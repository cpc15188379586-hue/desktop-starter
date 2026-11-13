#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地后端启动入口（PyCharm / 命令行两用）
====================================

用途：不经过 Tauri 打包，在开发机上直接把导入工具的后端跑起来，
方便调试导入引擎、模板解析和接口。

用法
----
    PyCharm：右键本文件 → Run 'run'（已附带 .idea 运行配置，直接在右上角下拉选择即可）
    命令行： python run.py                # 127.0.0.1:18765
             python run.py --port 18766   # 自定义端口
             python run.py --reload       # 代码改动自动重启（开发模式）

接口自检
--------
    浏览器打开  http://127.0.0.1:18765/api/health            → {"status": "ok"}
                http://127.0.0.1:18765/api/importer/groups   → 业务分组
    前端（Vite/Tauri）默认请求 127.0.0.1:18765，端口保持一致即可联调。
"""

from __future__ import annotations

import argparse
import os
import sys

# 无论从哪里启动，都切到本文件所在目录，保证 `import app.*` 可用
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="HDMS 基础数据导入工具 - 本地后端")
    parser.add_argument("--port", type=int, default=18765, help="监听端口（默认 18765）")
    parser.add_argument("--reload", action="store_true", help="开发模式：代码改动后自动重启")
    args = parser.parse_args()

    import uvicorn

    print("=" * 56)
    print("HDMS 基础数据导入工具 · 本地后端")
    print(f"地址    : http://127.0.0.1:{args.port}")
    print(f"健康检查: http://127.0.0.1:{args.port}/api/health")
    print(f"模式    : {'开发（自动重载）' if args.reload else '常规'}")
    print("按 Ctrl+C 停止")
    print("=" * 56)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",          # 只监听本机，不暴露局域网
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
