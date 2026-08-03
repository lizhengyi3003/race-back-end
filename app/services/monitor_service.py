"""系统监控服务：服务器状态（psutil）/ 数据库状态 / 健康检查"""

import platform
import socket
import time
from datetime import datetime

import psutil
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.ml import model_artifact
from app.schemas.monitor import CpuInfo, DatabaseStatus, DiskInfo, HealthStatus, MemoryInfo, ServerStatus, TableInfo

# psutil.Process.cpu_percent() 首次调用恒返回 0.0（需两次采样建立基准）。
# 每次请求新建 Process 对象都会命中“首次”，导致进程 CPU 一直显示 0%。
# 改为模块级持久化基准 + cpu_times 差值/墙钟差值计算真实平均 CPU 使用率。
_proc = psutil.Process()
_last_cpu_times = _proc.cpu_times()
_last_wall = time.monotonic()


def _process_cpu_percent() -> float:
    global _last_cpu_times, _last_wall
    now_times = _proc.cpu_times()
    now_wall = time.monotonic()
    user = max(now_times.user - _last_cpu_times.user, 0.0)
    sys = max(now_times.system - _last_cpu_times.system, 0.0)
    elapsed = now_wall - _last_wall
    _last_cpu_times, _last_wall = now_times, now_wall
    if elapsed <= 0:
        return 0.0
    return (user + sys) / elapsed * 100.0


def server_status() -> ServerStatus:
    boot = datetime.fromtimestamp(psutil.boot_time())
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(settings.MODEL_DIR.split("/")[0] + "/" if "/" in settings.MODEL_DIR else ".")
    return ServerStatus(
        hostname=socket.gethostname(),
        platform=platform.platform(),
        pythonVersion=platform.python_version(),
        uptimeSeconds=round(time.time() - psutil.boot_time(), 1),
        bootTime=boot,
        cpu=CpuInfo(
            percent=psutil.cpu_percent(interval=0.1),
            cores=psutil.cpu_count(logical=True) or 0,
            freq=psutil.cpu_freq().current if psutil.cpu_freq() else 0.0,
        ),
        memory=MemoryInfo(
            total=round(mem.total / 1024 / 1024, 1),
            used=round(mem.used / 1024 / 1024, 1),
            free=round(mem.free / 1024 / 1024, 1),
            percent=round(mem.percent, 1),
        ),
        disk=DiskInfo(
            total=round(disk.total / 1024**3, 1),
            used=round(disk.used / 1024**3, 1),
            free=round(disk.free / 1024**3, 1),
            percent=round(disk.percent, 1),
        ),
        processCpu=round(_process_cpu_percent(), 1),
        processMemory=round(_proc.memory_info().rss / 1024 / 1024, 1),
        threads=_proc.num_threads(),
    )


def database_status(db: Session) -> DatabaseStatus:
    connected = False
    tables: list[TableInfo] = []
    total_size = 0.0
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            connected = True
        inspector = __import__("sqlalchemy").inspect(engine)
        table_names = inspector.get_table_names()
        # MySQL 双引号是字符串字面量，表名必须用反引号；用方言 prepare 自动引用
        preparer = engine.dialect.identifier_preparer
        for name in table_names:
            quoted = preparer.quote(name)
            rows = db.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar() or 0
            size_mb = _table_size(name, rows)
            total_size += size_mb
            tables.append(TableInfo(name=name, rows=int(rows), sizeMb=round(size_mb, 3)))
    except Exception:
        connected = False
    return DatabaseStatus(
        connected=connected,
        dialect=engine.dialect.name,
        tables=tables,
        totalSizeMb=round(total_size, 3),
    )


def _table_size(table: str, rows: int = 0) -> float:
    """估算表容量（MB）：
    - MySQL：information_schema 直接取 data_length + index_length
    - SQLite：无 dbstat 虚拟表时，按列类型估算（数值 8B/行，文本按实际长度），
      保证各表容量占比相对真实、可用
    """
    try:
        with engine.connect() as conn:
            if not settings.is_sqlite:
                row = conn.execute(
                    text(
                        "SELECT (data_length + index_length) / 1024 / 1024 "
                        "FROM information_schema.TABLES WHERE table_schema = DATABASE() AND table_name = :t"
                    ),
                    {"t": table},
                ).scalar()
                return float(row or 0)

            # ---------- SQLite：优先 dbstat，不可用则按列类型估算 ----------
            try:
                row = conn.execute(text(f'SELECT SUM(pgsize) FROM dbstat WHERE name = "{table}"')).scalar()
                if row:
                    return float(row) / 1024 / 1024
            except Exception:
                pass

            # 降级估算：数值列 8B/行，文本列按 SUM(LENGTH()) 累加
            cols = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
            text_cols = [
                c[1] for c in cols if c[2] and any(k in c[2].upper() for k in ("CHAR", "TEXT", "CLOB", "BLOB", "JSON"))
            ]
            num_cols = len(cols) - len(text_cols)
            if rows <= 0:
                rows = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0
            if text_cols:
                sum_expr = ", ".join(f'COALESCE(SUM(LENGTH("{c}")), 0)' for c in text_cols)
                text_bytes = conn.execute(text(f'SELECT {sum_expr} FROM "{table}"')).fetchone()
                text_total = sum(float(v or 0) for v in text_bytes)
            else:
                text_total = 0.0
            num_total = rows * num_cols * 8.0
            return (num_total + text_total) / 1024 / 1024
    except Exception:
        return 0.0


def health(db: Session) -> HealthStatus:
    service_ok = True
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    # 模型：优先 DB active 版本（与实际生效模型一致），其次磁盘最新文件
    from app.models.model_version import ModelVersion

    model = None
    mv = (
        db.query(ModelVersion)
        .filter(ModelVersion.status == "active")
        .order_by(ModelVersion.id.desc())
        .first()
    )
    if mv and mv.artifact_path:
        model = model_artifact.load_scorecard(mv.artifact_path)
    if model is None:
        path = model_artifact.latest_artifact()
        if path:
            model = model_artifact.load_scorecard(path)
    model_exists = model is not None
    version = model.version if model else None

    status = (
        "healthy" if (service_ok and db_ok and model_exists) else ("degraded" if (service_ok and db_ok) else "down")
    )
    return HealthStatus(
        status=status,
        service="ok" if service_ok else "error",
        database="ok" if db_ok else "error",
        modelExists=model_exists,
        modelVersion=version,
        timestamp=datetime.now(),
    )
