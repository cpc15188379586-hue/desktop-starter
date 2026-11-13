"""基础数据导入模块：数据库配置、模板解析、按业务导入（后台任务 + 进度轮询）。

- 数据库地址/账号/密码在窗口里配置，可保存到本机 ~/.hdms_import_tool/config.json；
- 导入内容按业务分组勾选，可单独导入某一组/某一张表，也可一键导入全部；
- 默认演练（执行全部 SQL 后回滚不落库），确认后正式导入提交事务；
- 导入过程在后台线程执行，前端通过 /status 轮询进度与日志。
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.importer import engine

router = APIRouter(prefix="/api/importer", tags=["importer"])

CONFIG_DIR = Path.home() / ".hdms_import_tool"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 常用目录：自动搜索模板文件用
SEARCH_DIRS = [
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home(),
]


class DBConfig(BaseModel):
    host: str = ""
    port: int = 3306
    user: str = ""
    password: str = ""
    database: str = ""
    tenant: str = ""


class InspectRequest(BaseModel):
    xlsx_path: str


class RunRequest(BaseModel):
    db: DBConfig
    xlsx_path: str
    sheets: list[str] = []
    execute: bool = False


# ---------------------------------------------------------------------------
# 配置持久化
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return dict(**(__import__("json").loads(CONFIG_FILE.read_text("utf-8"))))
        except Exception:
            pass
    return {}


def _save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import json

    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


@router.get("/config")
def get_config():
    cfg = _load_config()
    cfg.setdefault("host", "")
    cfg.setdefault("port", 3306)
    cfg.setdefault("user", "")
    cfg.setdefault("password", "")
    cfg.setdefault("database", "")
    cfg.setdefault("tenant", "")
    return cfg


@router.post("/config")
def save_config(cfg: DBConfig):
    _save_config(cfg.model_dump())
    return {"ok": True}


@router.post("/test")
def test_connection(cfg: DBConfig):
    if not cfg.host or not cfg.user or not cfg.database:
        raise HTTPException(status_code=400, detail="请先填写数据库地址、用户名和库名")
    result = engine.test_connection(
        cfg.host, cfg.port, cfg.user, cfg.password, cfg.database)
    if not result["ok"]:
        return result
    return result


@router.get("/groups")
def get_groups():
    """业务分组 + 全部导入顺序，供界面渲染勾选项。"""
    return {"groups": engine.SHEET_GROUPS, "order": engine.IMPORT_ORDER}


# ---------------------------------------------------------------------------
# 模板
# ---------------------------------------------------------------------------

@router.get("/templates")
def list_templates():
    """在桌面/下载/文档/用户目录搜索《基础数据准备-导入模板-*.xlsx》。"""
    found: dict[str, dict] = {}
    for d in SEARCH_DIRS:
        if not d.exists():
            continue
        try:
            for p in sorted(d.glob("基础数据准备-导入模板-*.xlsx")):
                if p.name.startswith("~$"):
                    continue
                if p.name not in found:
                    found[p.name] = {
                        "name": p.name,
                        "path": str(p),
                        "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    }
        except OSError:
            continue
    # 字典序即版本序，新的排前面
    items = sorted(found.values(), key=lambda x: x["name"], reverse=True)
    return {"templates": items}


@router.post("/inspect")
def inspect_template(body: InspectRequest):
    path = body.xlsx_path.strip()
    if not path.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请选择 .xlsx 模板文件")
    if not Path(path).exists():
        raise HTTPException(status_code=400, detail="文件不存在：%s" % path)
    try:
        return engine.inspect_book(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail="模板解析失败：%s" % e)


# ---------------------------------------------------------------------------
# 导入任务（后台线程 + 轮询）
# ---------------------------------------------------------------------------

_job_lock = threading.Lock()
_job: dict = {
    "running": False,
    "stage": "",
    "logs": [],
    "result": None,
    "error": None,
    "started": None,
    "finished": None,
}
MAX_LOGS = 5000  # 含逐条 [SQL] 输出，容量放大避免挤掉结果报告


def _log(msg: str) -> None:
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    with _job_lock:
        _job["logs"].append(line)
        if len(_job["logs"]) > MAX_LOGS:
            del _job["logs"][: len(_job["logs"]) - MAX_LOGS]


def _run_job(req: RunRequest) -> None:
    try:
        with _job_lock:
            _job["stage"] = "导入中"
        result = engine.run_import(
            host=req.db.host,
            port=req.db.port,
            user=req.db.user,
            password=req.db.password,
            database=req.db.database,
            tenant=req.db.tenant,
            xlsx_path=req.xlsx_path,
            sheet_names=req.sheets,
            execute=req.execute,
            log=_log,
        )
        with _job_lock:
            _job["result"] = result
            _job["stage"] = "完成"
    except Exception as e:
        _log("导入异常：%s: %s" % (type(e).__name__, e))
        with _job_lock:
            _job["error"] = "%s: %s" % (type(e).__name__, e)
            _job["stage"] = "异常"
    finally:
        with _job_lock:
            _job["running"] = False
            _job["finished"] = datetime.now().strftime("%H:%M:%S")


@router.post("/run")
def run_import(body: RunRequest):
    db = body.db
    if not db.host or not db.user or not db.database:
        raise HTTPException(status_code=400, detail="数据库连接信息不完整，请先配置并测试连接")
    path = body.xlsx_path.strip()
    if not path.lower().endswith(".xlsx") or not Path(path).exists():
        raise HTTPException(status_code=400, detail="模板文件不存在：%s" % path)
    if body.execute and not body.sheets:
        pass  # 空 = 全部导入
    with _job_lock:
        if _job["running"]:
            raise HTTPException(status_code=409, detail="已有导入任务在执行中，请等待完成")
        _job.update({
            "running": True,
            "stage": "连接数据库",
            "logs": [],
            "result": None,
            "error": None,
            "started": datetime.now().strftime("%H:%M:%S"),
            "finished": None,
        })
    t = threading.Thread(target=_run_job, args=(body,), daemon=True)
    t.start()
    return {"ok": True, "message": "导入任务已启动"}


@router.get("/status")
def job_status():
    with _job_lock:
        return {
            "running": _job["running"],
            "stage": _job["stage"],
            "logs": list(_job["logs"]),
            "result": _job["result"],
            "error": _job["error"],
            "started": _job["started"],
            "finished": _job["finished"],
        }


@router.post("/clear-log")
def clear_log():
    """清空运行日志（界面上点「清空显示」时调用，历史日志彻底丢弃）。"""
    with _job_lock:
        _job["logs"] = []
    return {"ok": True}
