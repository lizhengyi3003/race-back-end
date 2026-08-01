"""数据库初始化：建表 + 默认管理员 + 默认系统配置。"""

from datetime import datetime

from sqlalchemy.orm import Session

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine

DEFAULT_CONFIGS = [
    ("low_risk_threshold", str(settings.LOW_RISK_THRESHOLD), "低风险评分阈值（≥ 此分为低风险）"),
    ("high_risk_threshold", str(settings.HIGH_RISK_THRESHOLD), "高风险评分阈值（< 此分为高风险）"),
    ("base_rate", str(settings.BASE_RATE), "基准贷款利率（%）"),
    ("risk_premium_factor", str(settings.RISK_PREMIUM_FACTOR), "风险溢价系数"),
    ("api_log_retention_days", str(settings.API_LOG_RETENTION_DAYS), "API 日志保留天数"),
]


def init_db(db: Session | None = None) -> None:
    """创建所有表"""
    Base.metadata.create_all(bind=engine)


def init_default_admin(db: Session) -> None:
    """创建默认管理员"""
    from app.models.user import User

    username = settings.DEFAULT_ADMIN_USERNAME
    exists = db.query(User).filter(User.username == username).first()
    if not exists:
        db.add(
            User(
                username=username,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                real_name="系统管理员",
                role="admin",
                status=1,
            )
        )
        db.commit()


def init_default_configs(db: Session) -> None:
    """写入默认系统配置（已存在则跳过）"""
    from app.models.sys_config import SystemConfig

    for key, value, desc in DEFAULT_CONFIGS:
        exists = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if not exists:
            db.add(
                SystemConfig(
                    config_key=key,
                    config_value=value,
                    description=desc,
                    updated_at=datetime.now(),
                )
            )
    db.commit()


def full_init(db: Session | None = None) -> None:
    """完整初始化：建表 + 默认管理员 + 默认配置"""
    init_db(db)
    own_session = db is None
    session = db or SessionLocal()
    try:
        init_default_admin(session)
        init_default_configs(session)
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    full_init()
    print("✅ 数据库初始化完成")
