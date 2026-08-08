"""评估记录模型：15 项涉农替代数据指标（文档 3.3.2 四大维度）+ 评分结果 + 输入/结果 JSON 快照"""

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
    business_type: Mapped[str] = mapped_column(String(32), default="")  # 种植/养殖/加工/混合

    # ---------- 维度一：土地经营类 ----------
    land_confirmed_area: Mapped[float | None] = mapped_column(Float, nullable=True)  # 亩
    land_transfer_years: Mapped[float | None] = mapped_column(Float, nullable=True)  # 年
    land_transfer_stability: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 稳定/小幅调整/频繁变更
    black_soil_protection: Mapped[float | None] = mapped_column(Float, nullable=True)  # 亩

    # ---------- 维度二：农业补贴类 ----------
    grain_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    machinery_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    grain_scale_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元
    specialty_crop_subsidy: Mapped[float | None] = mapped_column(Float, nullable=True)  # 元

    # ---------- 维度三：农业保险类 ----------
    insurance_years: Mapped[float | None] = mapped_column(Float, nullable=True)  # 年
    claim_count: Mapped[float | None] = mapped_column(Float, nullable=True)  # 次
    facility_insurance: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 完整投保/仅基础险/未投保

    # ---------- 维度四：产销经营类 ----------
    years_operating: Mapped[float | None] = mapped_column(Float, nullable=True)  # 年
    purchase_order: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 年度订单/零散收购/无稳定渠道
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)  # 万元
    credit_record: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 无逾期/有逾期

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
