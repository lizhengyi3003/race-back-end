"""评估记录模型：21 项替代数据指标（对齐前端 RiskInput）+ 评分结果 + 输入/结果 JSON 快照"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssessmentRecord(Base):
    __tablename__ = "assessment_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---------- 基本信息 ----------
    enterprise_name: Mapped[str] = mapped_column(String(128), default="")
    business_type: Mapped[str] = mapped_column(String(32), default="")  # 种植/养殖/加工/混合
    product_type: Mapped[str] = mapped_column(String(64), default="")

    # ---------- 户主特征类 ----------
    age: Mapped[float | None] = mapped_column(Float, nullable=True)  # 岁
    education: Mapped[str | None] = mapped_column(String(32), nullable=True)
    family_members: Mapped[float | None] = mapped_column(Float, nullable=True)  # 人

    # ---------- 第一类：土地经营类 ----------
    land_confirmed_area: Mapped[float | None] = mapped_column(Float, nullable=True)  # 亩
    land_transfer_years: Mapped[float | None] = mapped_column(Float, nullable=True)  # 年
    planting_structure: Mapped[str | None] = mapped_column(String(32), nullable=True)
    land_utilization: Mapped[float | None] = mapped_column(Float, nullable=True)  # %

    # ---------- 第二类：农业补贴类 ----------
    grain_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    machinery_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    other_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元

    # ---------- 第三类：农业保险类 ----------
    insurance_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)  # %
    claim_count: Mapped[float | None] = mapped_column(Float, nullable=True)  # 次
    claim_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    claim_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # %

    # ---------- 第四类：经营稳定性类 ----------
    years_operating: Mapped[float | None] = mapped_column(Float, nullable=True)  # 年
    business_concentration: Mapped[float | None] = mapped_column(Float, nullable=True)  # %
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)  # 万元
    revenue_stability: Mapped[str | None] = mapped_column(String(32), nullable=True)
    credit_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ---------- 第五类：贷款历史类 ----------
    loan_history: Mapped[float | None] = mapped_column(Float, nullable=True)  # 次
    loan_overdue_history: Mapped[float | None] = mapped_column(Float, nullable=True)  # 次

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
