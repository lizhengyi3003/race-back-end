"""数据库引擎与会话管理。"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def ensure_runtime_dirs() -> None:
    """确保运行期目录存在（SQLite 文件目录 / 模型目录 / 样本目录）"""
    Path(settings.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.SAMPLE_DIR).mkdir(parents=True, exist_ok=True)
    if settings.is_sqlite:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


ensure_runtime_dirs()

# SQLite 需要 check_same_thread=False 以支持多线程
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    """FastAPI 依赖：请求级数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
