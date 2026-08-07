"""风险评估请求/响应 —— 严格对齐前端 fore-end/src/api/types.ts 契约"""

from pydantic import BaseModel


class RiskInput(BaseModel):
    """涉农企业风险录入数据（文档 3.3.2 四大维度 15 项替代数据指标体系）"""
    # 基本信息
    enterpriseName: str = ""
    businessType: str = ""  # 经营类型：种植/养殖/加工/混合
    productType: str = ""  # 主营产品

    # === 维度一：土地经营类 ===
    landConfirmedArea: float | None = None  # 确权耕地总面积（亩）
    landTransferYears: float | None = None  # 土地流转合同年限（年）
    landTransferStability: str = ""  # 稳定/小幅调整/频繁变更
    blackSoilProtection: float | None = None  # 黑土地保护性耕作面积（亩）

    # === 维度二：农业补贴类 ===
    grainSubsidy: float | None = None  # 耕地地力保护补贴（元）
    machinerySubsidy: float | None = None  # 大型农机购置补贴（元）
    grainScaleSubsidy: float | None = None  # 粮食规模种植专项补贴（元）
    specialtyCropSubsidy: float | None = None  # 特色经济作物补贴（元）

    # === 维度三：农业保险类 ===
    insuranceYears: float | None = None  # 农业保险连续投保年限（年）
    claimCount: float | None = None  # 历史保险理赔频次（次）
    facilityInsurance: str = ""  # 完整投保/仅基础险/未投保

    # === 维度四：产销经营类 ===
    yearsOperating: float | None = None  # 主体持续经营年限（年）
    purchaseOrder: str = ""  # 年度订单/零散收购/无稳定渠道
    annualRevenue: float | None = None  # 农产品年稳定营收（万元）
    creditRecord: str = ""  # 无逾期/有逾期


class DynamicRiskInput(BaseModel):
    """动态指标体系评估请求（Phase 1：专家引擎，指标按编码动态传入）。"""

    enterpriseName: str = ""
    businessType: str = ""  # 经营类型大类编码 01~10；混合经营用 MIXED
    productType: str = ""
    middleType: str = ""  # 中类编码（可选）
    smallType: str = ""  # 小类编码（可选）
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
