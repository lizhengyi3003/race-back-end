"""风险评估请求/响应 —— 严格对齐前端 fore-end/src/api/types.ts 契约"""

from pydantic import BaseModel


class DynamicRiskInput(BaseModel):
    """动态指标体系评估请求（Phase 1：专家引擎，指标按编码动态传入）。"""

    enterpriseName: str = ""
    businessType: str = ""  # 经营类型大类编码 01~10；混合经营用 MIXED
    middleType: str = ""  # 中类编码（可选，兼容旧渐进式）
    smallType: str = ""  # 小类编码（可选，兼容旧渐进式）
    specificType: str = ""  # 具体营业类型编码（可选，兼容旧渐进式）
    selectedCategories: list[str] = []  # el-tree 勾选的具体营业类型叶子编码列表
    mixedBusiness: dict[str, float] = {}  # 混合经营比例 {大类编码: 0~1}
    indicators: dict[str, str] = {}  # 动态指标值 {指标编码: 值}


class FactorContribution(BaseModel):
    """各指标贡献"""

    factor: str
    category: str
    weight: float
    score: float  # 单项得分 0-100


class Deduction(BaseModel):
    """扣分原因（前三项负面指标）"""

    factor: str
    score: float
    reason: str


class RiskResult(BaseModel):
    """风险评估结果（评分卡 0-1000 分）"""

    score: int  # 综合信用评分 (0-1000)
    probability: float  # 违约概率 (0-1)
    level: str  # 低风险 / 中等风险 / 高风险
    suggestedAmount: float  # 建议授信额度（万元）
    suggestedRate: float  # 建议利率（%）
    contributions: list[FactorContribution]
    deductions: list[Deduction]
    advice: str
    overrides: list[str] = []  # 触发的兜底规则（极端场景人工复核提示）
    veto: str | None = None  # 一票否决命中指标名（专家引擎）
    completeness: float = 0.0  # 数据完整度 0~1（相对期望指标集）
