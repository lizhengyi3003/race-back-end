"""指标管理（管理平台）：列表 / 详情 / 更新 / 统计。"""

from typing import Literal

from pydantic import BaseModel


class IndicatorAdminOut(BaseModel):
    """指标管理列表/详情（对应 indicator_config 全字段 + 派生信息）。"""

    id: int
    code: str
    name: str
    level: Literal["基本项", "大类", "中类", "小类", "具体营业类型"] = "基本项"
    category_code: str = ""
    category_name: str = ""
    indicator_type: Literal["数值", "枚举", "布尔", "文本"] = "数值"
    unit: str = ""
    value_range: str = ""
    options: list[str] = []
    data_source: str = ""
    is_feature: bool = False
    risk_meaning: str = ""
    weight_star: float = 3.0
    region: str = ""
    is_veto: bool = False
    cycle: str = ""
    scoring_rule: str = ""
    scoring_config: dict | None = None
    display_order: int = 0

    @classmethod
    def from_model(cls, c, options: list[str] | None = None) -> "IndicatorAdminOut":
        return cls(
            id=c.id,
            code=c.code,
            name=c.name,
            level=c.level,
            category_code=c.category_code,
            category_name=c.category_name,
            indicator_type=c.indicator_type,
            unit=c.unit,
            value_range=c.value_range,
            options=options or [],
            data_source=c.data_source,
            is_feature=c.is_feature,
            risk_meaning=c.risk_meaning,
            weight_star=c.weight_star,
            region=c.region,
            is_veto=c.is_veto,
            cycle=c.cycle,
            scoring_rule=c.scoring_rule,
            scoring_config=c.scoring_config,
            display_order=c.display_order,
        )


class IndicatorUpdate(BaseModel):
    """可编辑字段（管理平台维护权重 / 评分 / 归属 / 类型等）。"""

    name: str | None = None
    indicator_type: Literal["数值", "枚举", "布尔", "文本"] | None = None
    unit: str | None = None
    value_range: str | None = None
    data_source: str | None = None
    is_feature: bool | None = None
    risk_meaning: str | None = None
    weight_star: float | None = None
    region: str | None = None
    is_veto: bool | None = None
    cycle: str | None = None
    scoring_rule: str | None = None
    scoring_config: dict | None = None
    display_order: int | None = None


class IndicatorStats(BaseModel):
    """指标总量统计。"""

    total: int = 0
    by_level: dict[str, int] = {}
    by_type: dict[str, int] = {}
    feature: int = 0
    veto: int = 0
    categories: int = 0
