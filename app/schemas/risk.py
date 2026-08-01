"""风险评估请求/响应 —— 严格对齐前端 fore-end/src/api/types.ts 契约"""

from pydantic import BaseModel


class RiskInput(BaseModel):
    """涉农企业风险录入数据（六大类21项替代数据指标体系）"""

    # 基本信息
    enterpriseName: str = ""
    businessType: str = ""  # 经营类型：种植/养殖/加工/混合
    productType: str = ""  # 主营产品

    # === 户主特征类 ===
    age: float | None = None  # 年龄（岁）
    education: str = ""  # 受教育程度：小学及以下/初中/高中/大专及以上
    familyMembers: float | None = None  # 家庭成员数量（人）

    # === 第一类：土地经营类 ===
    landConfirmedArea: float | None = None  # 土地确权面积（亩）
    landTransferYears: float | None = None  # 土地流转年限（年）
    plantingStructure: str = ""  # 种植结构：主粮/经济作物/混合/设施农业
    landUtilization: float | None = None  # 土地规模利用率（%）

    # === 第二类：农业补贴类 ===
    grainSubsidy: float | None = None  # 粮食直补金额（元）
    machinerySubsidy: float | None = None  # 农机购置补贴（元）
    otherSubsidy: float | None = None  # 其他涉农补贴（元）

    # === 第三类：农业保险类 ===
    insuranceCoverage: float | None = None  # 农业保险覆盖率（%）
    claimCount: float | None = None  # 历年理赔次数（次）
    claimAmount: float | None = None  # 历年理赔金额（元）
    claimRatio: float | None = None  # 理赔金额占比（%）

    # === 第四类：经营稳定性类 ===
    yearsOperating: float | None = None  # 经营年限（年）
    businessConcentration: float | None = None  # 经营范围集中度（%）
    annualRevenue: float | None = None  # 年销售收入（万元）
    revenueStability: str = ""  # 销售收入稳定性
    creditStatus: str = ""  # 经营者征信状况

    # === 第五类：贷款历史类 ===
    loanHistory: float | None = None  # 历史贷款记录（次，0=无）
    loanOverdueHistory: float | None = None  # 历史逾期记录（次，0=无）


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
