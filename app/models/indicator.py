"""动态指标体系模型：指标配置表（文档 14 列 schema）+ 类别树。

数据来源：docs/农业及相关产业动态指标搜集体系.md / .xlsx（775 条指标）。
"""

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IndicatorCategory(Base):
    """行业类别树：大类(2位) → 中类(3位) → 小类(4位)，编码与《农业及相关产业统计分类（2020）》一致。"""

    __tablename__ = "indicator_category"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)  # 01 / 011 / 0111
    name: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[str] = mapped_column(String(8), default="")  # 大类 / 中类 / 小类
    parent_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class IndicatorConfig(Base):
    """指标配置：动态表单与评分引擎的元数据（对应文档 14 列）。"""

    __tablename__ = "indicator_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # 指标编码（唯一）
    name: Mapped[str] = mapped_column(String(128), index=True)
    level: Mapped[str] = mapped_column(String(8), index=True)  # 基本项 / 大类 / 中类 / 小类
    category_code: Mapped[str] = mapped_column(String(16), index=True)  # 所属类别编码（基本项=BASIC）
    category_name: Mapped[str] = mapped_column(String(64), default="")
    indicator_type: Mapped[str] = mapped_column(String(8), default="数值")  # 数值 / 枚举 / 布尔 / 文本
    unit: Mapped[str] = mapped_column(String(32), default="")
    value_range: Mapped[str] = mapped_column(String(255), default="")  # 取值说明
    data_source: Mapped[str] = mapped_column(String(255), default="")
    is_feature: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否特色指标
    risk_meaning: Mapped[str] = mapped_column(String(255), default="")
    weight_star: Mapped[float] = mapped_column(Float, default=3.0)  # 建议权重（星级数值化 3/3.5/4.5/5）
    region: Mapped[str] = mapped_column(String(64), default="")  # 适用区域
    is_veto: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否一票否决
    cycle: Mapped[str] = mapped_column(String(8), default="")  # 采集周期：年报/季报/月报/实时
    scoring_rule: Mapped[str] = mapped_column(String(255), default="")  # 评分规则
    display_order: Mapped[int] = mapped_column(Integer, default=0)
