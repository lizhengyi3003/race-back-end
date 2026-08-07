"""动态指标体系模型：指标配置表（文档 14 列 schema）+ 类别树。

数据来源：docs/农业及相关产业动态指标搜集体系.md / .xlsx（775 条指标）。
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String
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
    scoring_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 评分参数（数值上限/档位映射等，可覆盖默认）
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class IndicatorValue(Base):
    """评估指标明细：一次评估中各动态指标的取值与数据质量。"""

    __tablename__ = "indicator_value"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(Integer, index=True)
    indicator_code: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[str | None] = mapped_column(String(512), nullable=True)  # 原始值（数值/枚举/布尔/文本）
    quality: Mapped[str] = mapped_column(String(16), default="直接")  # 直接 / 代理 / 缺失 / 存疑
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class DataSourceMapping(Base):
    """数据-指标映射字典：外部数据源字段 → 指标，含融合规则与可信度。"""

    __tablename__ = "data_source_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_source: Mapped[str] = mapped_column(String(32), index=True)  # CMES / CHFS / CFPS
    data_field: Mapped[str] = mapped_column(String(64))  # 数据集字段名
    indicator_code: Mapped[str] = mapped_column(String(32), index=True)  # 映射到的指标
    transform_rule: Mapped[str] = mapped_column(String(255), default="")  # 转换规则（JSON/描述）
    aggregation: Mapped[str] = mapped_column(String(16), default="加权平均")  # 加权平均/最大/最小/规则
    reliability: Mapped[float] = mapped_column(Float, default=0.5)  # 数据源可信度 0-1
    conflict_policy: Mapped[str] = mapped_column(String(32), default="加权平均")  # 冲突处理策略
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BusinessTypeConfig(Base):
    """经营类型（大类）配置：层级基础权重 + 混合经营协同因子 + 调整项。"""

    __tablename__ = "business_type_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_type_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # 01~10 / MIXED
    name: Mapped[str] = mapped_column(String(64), default="")
    level_weights: Mapped[dict] = mapped_column(JSON, default=dict)  # {基本项:0.30, 大类:0.25, 中类:0.20, 小类:0.15, 特殊:0.10}
    feature_boost: Mapped[float] = mapped_column(Float, default=1.1)  # 特色指标加成系数
    region_boost: Mapped[dict] = mapped_column(JSON, default=dict)  # {适用区域: 加成}
    synergy_factors: Mapped[dict] = mapped_column(JSON, default=dict)  # { "01+02": {"factor":1.05, "name":"生态循环"} }
    active: Mapped[bool] = mapped_column(Boolean, default=True)
