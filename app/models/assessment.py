"""评估记录模型：动态指标体系（专家引擎）+ 评分结果 + 输入/结果 JSON 快照"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssessmentRecord(Base):
    __tablename__ = "assessment_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---------- 归属（当前账号）----------
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # sys_user.id；匿名评估为 NULL

    # ---------- 基本信息 ----------
    enterprise_name: Mapped[str] = mapped_column(String(128), default="")
    business_type: Mapped[str] = mapped_column(String(32), default="")  # 经营类型大类编码 01~10 / MIXED

    # ---------- 评估结果 ----------
    score: Mapped[int] = mapped_column(Integer, default=0)
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    level: Mapped[str] = mapped_column(String(16), default="")  # 低风险/中等风险/高风险
    suggested_amount: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # ---------- 快照 ----------
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    assessor_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    # ---------- 真实回测（人工回填放款/逾期结果，用于现实版召回率/精确率）----------
    outcome: Mapped[str] = mapped_column(String(16), default="pending")  # pending/normal/overdue/rejected
    outcome_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
