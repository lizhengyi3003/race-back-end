"""21 项涉农替代数据指标定义 + 规则评分卡（评分卡刻度 0-1000）。

六大类：户主特征 / 土地经营 / 农业补贴 / 农业保险 / 经营稳定性 / 贷款历史。
对齐前端 fore-end/src/utils/riskModel.ts 的分箱与权重逻辑，
用于：1) 无训练模型时的兜底评估；2) 模型未选中指标的可解释展示。
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------
# 指标元数据（顺序即展示顺序）
# ---------------------------------------------------------------
INDICATOR_META: dict[str, dict[str, Any]] = {
    # 第一类：户主特征类
    "age": {"name": "年龄", "category": "户主特征类", "weight": 0.04, "unit": "岁", "type": "continuous"},
    "education": {"name": "受教育程度", "category": "户主特征类", "weight": 0.05, "unit": "", "type": "categorical"},
    "family_members": {
        "name": "家庭成员数量",
        "category": "户主特征类",
        "weight": 0.03,
        "unit": "人",
        "type": "continuous",
    },
    # 第二类：土地经营类
    "land_confirmed_area": {
        "name": "土地确权面积",
        "category": "土地经营类",
        "weight": 0.06,
        "unit": "亩",
        "type": "continuous",
    },
    "land_transfer_years": {
        "name": "土地流转年限",
        "category": "土地经营类",
        "weight": 0.04,
        "unit": "年",
        "type": "continuous",
    },
    "planting_structure": {
        "name": "种植结构",
        "category": "土地经营类",
        "weight": 0.04,
        "unit": "",
        "type": "categorical",
    },
    "land_utilization": {
        "name": "土地规模利用率",
        "category": "土地经营类",
        "weight": 0.05,
        "unit": "%",
        "type": "continuous",
    },
    # 第三类：农业补贴类
    "grain_subsidy": {
        "name": "粮食直补金额",
        "category": "农业补贴类",
        "weight": 0.04,
        "unit": "元",
        "type": "continuous",
    },
    "machinery_subsidy": {
        "name": "农机购置补贴",
        "category": "农业补贴类",
        "weight": 0.04,
        "unit": "元",
        "type": "continuous",
    },
    "other_subsidy": {
        "name": "其他涉农补贴",
        "category": "农业补贴类",
        "weight": 0.03,
        "unit": "元",
        "type": "continuous",
    },
    # 第四类：农业保险类
    "insurance_coverage": {
        "name": "农业保险覆盖率",
        "category": "农业保险类",
        "weight": 0.08,
        "unit": "%",
        "type": "continuous",
    },
    "claim_count": {
        "name": "历年理赔次数",
        "category": "农业保险类",
        "weight": 0.04,
        "unit": "次",
        "type": "continuous",
    },
    "claim_amount": {
        "name": "历年理赔金额",
        "category": "农业保险类",
        "weight": 0.05,
        "unit": "元",
        "type": "continuous",
    },
    "claim_ratio": {
        "name": "理赔金额占比",
        "category": "农业保险类",
        "weight": 0.05,
        "unit": "%",
        "type": "continuous",
    },
    # 第五类：经营稳定性类
    "years_operating": {
        "name": "经营年限",
        "category": "经营稳定性类",
        "weight": 0.07,
        "unit": "年",
        "type": "continuous",
    },
    "business_concentration": {
        "name": "经营范围集中度",
        "category": "经营稳定性类",
        "weight": 0.05,
        "unit": "%",
        "type": "continuous",
    },
    "annual_revenue": {
        "name": "年销售收入",
        "category": "经营稳定性类",
        "weight": 0.06,
        "unit": "万元",
        "type": "continuous",
    },
    "revenue_stability": {
        "name": "销售收入稳定性",
        "category": "经营稳定性类",
        "weight": 0.05,
        "unit": "",
        "type": "categorical",
    },
    "credit_status": {
        "name": "经营者征信",
        "category": "经营稳定性类",
        "weight": 0.06,
        "unit": "",
        "type": "categorical",
    },
    # 第六类：贷款历史类
    "loan_history": {
        "name": "历史贷款记录",
        "category": "贷款历史类",
        "weight": 0.03,
        "unit": "次",
        "type": "continuous",
    },
    "loan_overdue_history": {
        "name": "历史逾期记录",
        "category": "贷款历史类",
        "weight": 0.04,
        "unit": "次",
        "type": "continuous",
    },
}

INDICATOR_ORDER: list[str] = list(INDICATOR_META.keys())

# camelCase（前端契约）→ snake_case（模型字段）映射
CAMEL_TO_SNAKE: dict[str, str] = {
    "age": "age",
    "education": "education",
    "familyMembers": "family_members",
    "landConfirmedArea": "land_confirmed_area",
    "landTransferYears": "land_transfer_years",
    "plantingStructure": "planting_structure",
    "landUtilization": "land_utilization",
    "grainSubsidy": "grain_subsidy",
    "machinerySubsidy": "machinery_subsidy",
    "otherSubsidy": "other_subsidy",
    "insuranceCoverage": "insurance_coverage",
    "claimCount": "claim_count",
    "claimAmount": "claim_amount",
    "claimRatio": "claim_ratio",
    "yearsOperating": "years_operating",
    "businessConcentration": "business_concentration",
    "annualRevenue": "annual_revenue",
    "revenueStability": "revenue_stability",
    "creditStatus": "credit_status",
    "loanHistory": "loan_history",
    "loanOverdueHistory": "loan_overdue_history",
}
SNAKE_TO_CAMEL: dict[str, str] = {v: k for k, v in CAMEL_TO_SNAKE.items()}

CONTINUOUS_FIELDS: list[str] = [f for f, m in INDICATOR_META.items() if m["type"] == "continuous"]
CATEGORICAL_FIELDS: list[str] = [f for f, m in INDICATOR_META.items() if m["type"] == "categorical"]

# ---------------------------------------------------------------
# 规则评分（兜底 / 未选中指标展示）—— 对齐前端 riskModel.ts
# ---------------------------------------------------------------


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _bin_score(value: float, bins: list[tuple[float, float, float]]) -> float:
    for lo, hi, score in bins:
        if lo <= value < hi:
            return score
    return 10.0


def _score_land_area(v: float) -> float:
    return _bin_score(v, [(0, 50, 20), (50, 200, 55), (200, 500, 80), (500, 1e18, 95)])


def _score_transfer_years(v: float) -> float:
    return _bin_score(v, [(0, 1, 20), (1, 3, 50), (3, 5, 75), (5, 1e18, 95)])


def _score_planting(v: str) -> float:
    return {"主粮种植": 70, "经济作物": 85, "混合经营": 92, "设施农业": 82}.get(v, 50)


def _score_utilization(v: float) -> float:
    return _bin_score(v, [(0, 50, 40), (50, 70, 60), (70, 90, 85), (90, 1e18, 98)])


def _score_subsidy(v: float, ceiling: float) -> float:
    if v <= 0:
        return 30.0
    return _clamp(round(v / ceiling * 90 + 10), 10, 100)


def _score_insurance(v: float) -> float:
    return _bin_score(v, [(0, 30, 30), (30, 60, 60), (60, 80, 82), (80, 1e18, 98)])


def _score_claim_count(v: float) -> float:
    if v <= 0:
        return 100.0
    if v <= 2:
        return 60.0
    if v <= 5:
        return 35.0
    return 15.0


def _score_claim_ratio(v: float) -> float:
    return _bin_score(v, [(0, 10, 90), (10, 30, 70), (30, 60, 45), (60, 1e18, 20)])


def _score_operating_years(v: float) -> float:
    return _bin_score(v, [(0, 2, 30), (2, 5, 60), (5, 10, 85), (10, 1e18, 98)])


def _score_concentration(v: float) -> float:
    if 70 <= v <= 90:
        return 95.0
    if 50 <= v < 70:
        return 75.0
    if v > 90:
        return 80.0
    if 30 <= v < 50:
        return 55.0
    return 35.0


def _score_revenue(v: float) -> float:
    return _bin_score(v, [(0, 20, 25), (20, 60, 55), (60, 150, 80), (150, 1e18, 95)])


def _score_revenue_stability(v: str) -> float:
    return {"稳定": 98, "基本稳定": 80, "波动较大": 50, "大幅波动": 25}.get(v, 50)


def _score_credit_status(v: str) -> float:
    return {"无不良记录": 98, "轻微逾期": 70, "多次逾期": 35, "严重失信": 10}.get(v, 50)


def _score_age(v: float) -> float:
    # 务农主体：25-55 岁壮年为黄金还款期，年轻经验不足 / 年迈经营能力下降
    return _bin_score(v, [(0, 25, 60), (25, 35, 85), (35, 55, 95), (55, 65, 80), (65, 1e18, 55)])


def _score_education(v: str) -> float:
    # 受教育程度 = 金融素养代理变量，学历越高信用越好
    return {"小学及以下": 40, "初中": 65, "高中": 85, "大专及以上": 95}.get(v, 50)


def _score_family_members(v: float) -> float:
    # 家庭成员 3-5 人（劳动力充足且负担适中）评分最高
    return _bin_score(v, [(0, 1, 40), (1, 3, 75), (3, 5, 95), (5, 7, 80), (7, 1e18, 60)])


def _score_claim_amount(v: float) -> float:
    # 历年理赔金额（元）越高，风险越大
    return _bin_score(v, [(0, 1, 100), (1, 10000, 80), (10000, 50000, 60), (50000, 100000, 40), (100000, 1e18, 20)])


def _score_loan_history(v: float) -> float:
    # 有 1-5 次贷款记录（且逾期少）说明信用历史良好；无记录信息不足为中性
    return _bin_score(v, [(0, 1, 55), (1, 3, 80), (3, 5, 90), (5, 1e18, 75)])


def _score_loan_overdue_history(v: float) -> float:
    # 历史逾期次数越多，信用越差（强负面信号）
    if v <= 0:
        return 98.0
    if v <= 1:
        return 60.0
    if v <= 3:
        return 35.0
    return 15.0


RULE_SCORERS: dict[str, Any] = {
    "age": _score_age,
    "education": _score_education,
    "family_members": _score_family_members,
    "land_confirmed_area": _score_land_area,
    "land_transfer_years": _score_transfer_years,
    "planting_structure": _score_planting,
    "land_utilization": _score_utilization,
    "grain_subsidy": lambda v: _score_subsidy(v or 0, 5000),
    "machinery_subsidy": lambda v: _score_subsidy(v or 0, 30000),
    "other_subsidy": lambda v: _score_subsidy(v or 0, 5000),
    "insurance_coverage": _score_insurance,
    "claim_count": _score_claim_count,
    "claim_amount": _score_claim_amount,
    "claim_ratio": _score_claim_ratio,
    "years_operating": _score_operating_years,
    "business_concentration": _score_concentration,
    "annual_revenue": _score_revenue,
    "revenue_stability": _score_revenue_stability,
    "credit_status": _score_credit_status,
    "loan_history": _score_loan_history,
    "loan_overdue_history": _score_loan_overdue_history,
}


def rule_sub_score(field: str, value: Any) -> float:
    """计算某指标规则子得分（0-100）"""
    try:
        if value is None or value == "" or (isinstance(value, float) and value != value):
            value = 0.0
        return float(RULE_SCORERS[field](value))
    except (TypeError, ValueError):
        return 50.0


def rule_weighted_score(inputs: dict[str, Any]) -> tuple[float, list[dict]]:
    """规则评分卡：加权汇总 → 0-100 原始分 → ×10 → 0-1000"""
    indicators = []
    total = 0.0
    for field in INDICATOR_ORDER:
        meta = INDICATOR_META[field]
        s = rule_sub_score(field, inputs.get(field))
        total += meta["weight"] * s
        indicators.append(
            {"factor": meta["name"], "category": meta["category"], "weight": meta["weight"], "score": s, "field": field}
        )
    return total * 10, indicators  # 0-1000
