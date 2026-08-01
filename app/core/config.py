"""应用配置：基于 pydantic-settings 从 .env / 环境变量读取。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---------- 应用 ----------
    APP_NAME: str = "涉农信贷风险智能评估系统"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # ---------- 数据库 ----------
    # 默认 SQLite（零配置）；切换 MySQL 只需修改 DATABASE_URL：
    # mysql+pymysql://user:pass@host:3306/dbname?charset=utf8mb4
    DATABASE_URL: str = "sqlite:///./data/race.db"

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

    # ---------- 模型训练 ----------
    AUTO_TRAIN_ON_STARTUP: bool = True
    SEED_SAMPLES: int = 4000
    SEED_DEFAULT_RATE: float = 0.04
    # SMOTE 过采样（对违约样本合成扩增，缓解样本不平衡）
    SMOTE_ENABLED: bool = True

    # ---------- 兜底规则阈值（触发后强制高风险，供人工复核）----------
    OVERRIDE_CLAIM_RATIO: float = 70.0  # 理赔金额占比 ≥ 此值
    OVERRIDE_CLAIM_COUNT: int = 2  # 理赔次数 ≥ 此值
    OVERRIDE_INSURANCE_LOW: float = 40.0  # 保险覆盖率 < 此值
    OVERRIDE_UTILIZATION_LOW: float = 35.0  # 土地规模利用率 < 此值
    OVERRIDE_AREA_MIN: float = 100.0  # 土地面积 ≥ 此值（配合利用率规则）
    OVERRIDE_CATASTROPHE_CLAIMS: int = 5  # 重大灾害规则：理赔次数 ≥ 此值
    OVERRIDE_CATASTROPHE_INSURANCE: float = 30.0  # 重大灾害规则：保险覆盖率 < 此值

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

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
