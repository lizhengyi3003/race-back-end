"""动态指标体系相关 Pydantic 契约（前端动态表单与指标树）。"""

from typing import Literal

from pydantic import BaseModel


class IndicatorField(BaseModel):
    """动态表单字段配置（对应 indicator_config 14 列 + 派生选项）。"""

    code: str
    name: str
    level: str  # 基本项 / 大类 / 中类 / 小类
    category_code: str
    category_name: str
    indicator_type: Literal["数值", "枚举", "布尔", "文本"] = "数值"
    unit: str = ""
    value_range: str = ""
    options: list[str] = []  # 枚举类型解析出的选项
    data_source: str = ""
    is_feature: bool = False
    risk_meaning: str = ""
    weight_star: float = 3.0
    region: str = ""
    is_veto: bool = False
    cycle: str = ""
    scoring_rule: str = ""
    required: bool = True  # 文本备注类默认非必填


class CategoryNode(BaseModel):
    """指标类别树节点（大类/中类/小类）。"""

    code: str
    name: str
    level: str
    display: str  # "0111 谷物种植"
    indicator_count: int = 0
    children: list["CategoryNode"] = []


class IndicatorTree(BaseModel):
    """指标树：基本项字段 + 类别树。"""

    basic: list[IndicatorField] = []
    categories: list[CategoryNode] = []


class IndicatorConfigOut(BaseModel):
    """渐进式表单配置：基本项 + 选中分支指标 + 当前选择路径。"""

    basic: list[IndicatorField] = []
    indicators: list[IndicatorField] = []
    selected: dict = {}  # {"businessType": "01", "middleType": "011", "smallType": "0111"}
