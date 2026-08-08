"""应用配置：基于 pydantic-settings 从 .env / 环境变量读取。"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（config.py 位于 app/core/，上溯 3 级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _abs_path(value: str) -> str:
    """相对路径解析到项目根，避免后端从任意 cwd 启动时找不到模型/样本。"""
    p = Path(value)
    return str(p.resolve()) if p.is_absolute() else str((PROJECT_ROOT / p).resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- 应用 ----------
    APP_NAME: str = "涉农信贷风险智能评估系统"
    APP_VERSION: str = "1.6.0"
    API_PREFIX: str = "/api/v1"

    # ---------- 数据库（MySQL）----------
    # 默认连接本机 MySQL（Docker 或本机安装均可），通过 .env 的 DATABASE_URL 覆盖
    DATABASE_URL: str = "mysql+pymysql://root:race123456@127.0.0.1:3306/race?charset=utf8mb4"

    # ---------- JWT ----------
    JWT_SECRET_KEY: str = "race-dev-secret-key-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ---------- CORS ----------
    CORS_ORIGINS: str = "*"

    # ---------- 默认管理员 ----------
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # ---------- 模型与数据目录 ----------
    MODEL_DIR: str = "data/models"
    SAMPLE_DIR: str = "data/samples"

    @field_validator("MODEL_DIR", "SAMPLE_DIR")
    @classmethod
    def _absolutize_dirs(cls, v: str) -> str:
        return _abs_path(v)

    # ---------- 模型训练 ----------
    AUTO_TRAIN_ON_STARTUP: bool = True
    SEED_SAMPLES: int = 4000
    SEED_DEFAULT_RATE: float = 0.04
    # SMOTE 过采样（对违约样本合成扩增，缓解样本不平衡）
    SMOTE_ENABLED: bool = True

    # ---------- 评分卡业务阈值（管理平台可在线调整）----------
    LOW_RISK_THRESHOLD: int = 700
    HIGH_RISK_THRESHOLD: int = 500
    BASE_RATE: float = 3.5
    RISK_PREMIUM_FACTOR: float = 6.0

    # ---------- API 日志 ----------
    API_LOG_RETENTION_DAYS: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
