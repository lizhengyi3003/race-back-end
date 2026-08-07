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


# 业务类型默认配置（与 scripts/seed_business_config.py 一致，供服务器开箱即用）
_DEFAULT_LEVEL_WEIGHTS = {"基本项": 0.35, "大类": 0.28, "中类": 0.22, "小类": 0.15}
_SYNERGY_FACTORS: dict[str, dict] = {
    "01+02": {"factor": 1.06, "name": "种植+食用加工·产销一体"},
    "01+04": {"factor": 1.04, "name": "种植+生产资料·农资一体化"},
    "01+08": {"factor": 1.05, "name": "种植+生态环保·生态循环"},
    "01+05": {"factor": 1.04, "name": "种植+流通·产销衔接"},
    "02+05": {"factor": 1.04, "name": "加工+流通·供应链闭环"},
    "03+05": {"factor": 1.03, "name": "非食用加工+流通·原料直达"},
    "04+01": {"factor": 1.04, "name": "生产资料+种植·农资一体化"},
}


def init_business_configs(db: Session) -> None:
    """种子经营类型配置：10 大类层级权重 + MIXED 协同因子（已存在则补齐默认）。"""
    from app.models.indicator import BusinessTypeConfig, IndicatorCategory

    cats = db.query(IndicatorCategory).filter(IndicatorCategory.level == "大类").all()
    for cat in cats:
        row = db.query(BusinessTypeConfig).filter(BusinessTypeConfig.business_type_code == cat.code).first()
        if row:
            if not row.level_weights:
                row.level_weights = dict(_DEFAULT_LEVEL_WEIGHTS)
            if not row.feature_boost:
                row.feature_boost = 1.1
            continue
        db.add(
            BusinessTypeConfig(
                business_type_code=cat.code,
                name=cat.name,
                level_weights=dict(_DEFAULT_LEVEL_WEIGHTS),
                feature_boost=1.1,
                region_boost={},
                synergy_factors={},
                active=True,
            )
        )
    mixed = db.query(BusinessTypeConfig).filter(BusinessTypeConfig.business_type_code == "MIXED").first()
    if not mixed:
        db.add(
            BusinessTypeConfig(
                business_type_code="MIXED",
                name="混合经营",
                level_weights=dict(_DEFAULT_LEVEL_WEIGHTS),
                feature_boost=1.1,
                region_boost={},
                synergy_factors=dict(_SYNERGY_FACTORS),
                active=True,
            )
        )
    elif not mixed.synergy_factors:
        mixed.synergy_factors = dict(_SYNERGY_FACTORS)
    db.commit()


def full_init(db: Session | None = None) -> None:
    """完整初始化：建表 + 默认管理员 + 默认配置 + 业务配置"""
    init_db(db)
    own_session = db is None
    session = db or SessionLocal()
    try:
        init_default_admin(session)
        init_default_configs(session)
        try:
            init_business_configs(session)
        except Exception:  # noqa: BLE001  指标表未导入时不阻断启动
            pass
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    full_init()
    print("✅ 数据库初始化完成")
