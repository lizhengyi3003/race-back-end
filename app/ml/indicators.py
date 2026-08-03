"""15 项涉农替代数据指标定义 + 规则评分卡（评分卡刻度 0-1000）。

四大维度：土地经营 / 农业补贴 / 农业保险 / 产销经营（文档 3.3.2）。
对齐前端 fore-end/src/utils/riskModel.ts 的分箱与权重逻辑，
用于：1) 无训练模型时的兜底评估；2) 模型未选中指标的可解释展示。
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------
# 指标元数据（顺序即展示顺序；权重 = 文档维度权重 × 维度内分值比例）
# ---------------------------------------------------------------
INDICATOR_META: dict[str, dict[str, Any]] = {
    # 维度一：土地经营类（38%）
    "land_confirmed_area": {
        "name": "确权耕地总面积",
        "category": "土地经营类",
        "weight": 0.136,
        "unit": "亩",
        "type": "continuous",
    },
    "land_transfer_years": {
        "name": "土地流转合同年限",
        "category": "土地经营类",
        "weight": 0.109,
        "unit": "年",
        "type": "continuous",
    },
    "land_transfer_stability": {
        "name": "土地流转稳定性",
        "category": "土地经营类",
        "weight": 0.081,
        "unit": "",
        "type": "categorical",
    },
    "black_soil_protection": {
        "name": "黑土地保护性耕作面积",
        "category": "土地经营类",
        "weight": 0.054,
        "unit": "亩",
        "type": "continuous",
    },
    # 维度二：农业补贴类（27%）
    "grain_subsidy": {
        "name": "耕地地力保护补贴",
        "category": "农业补贴类",
        "weight": 0.088,
        "unit": "元",
        "type": "continuous",
    },
    "machinery_subsidy": {
        "name": "大型农机购置补贴",
        "category": "农业补贴类",
        "weight": 0.074,
        "unit": "元",
        "type": "continuous",
    },
    "grain_scale_subsidy": {
        "name": "粮食规模种植专项补贴",
        "category": "农业补贴类",
        "weight": 0.059,
        "unit": "元",
        "type": "continuous",
    },
    "specialty_crop_subsidy": {
        "name": "特色经济作物补贴",
        "category": "农业补贴类",
        "weight": 0.049,
        "unit": "元",
        "type": "continuous",
    },
    # 维度三：农业保险类（20%）
    "insurance_years": {
        "name": "农业保险连续投保年限",
        "category": "农业保险类",
        "weight": 0.089,
        "unit": "年",
        "type": "continuous",
    },
    "claim_count": {
        "name": "历史保险理赔频次",
        "category": "农业保险类",
        "weight": 0.067,
        "unit": "次",
        "type": "continuous",
    },
    "facility_insurance": {
        "name": "设施农业附加保险",
        "category": "农业保险类",
        "weight": 0.044,
        "unit": "",
        "type": "categorical",
    },
    # 维度四：产销经营类（15%）
    "years_operating": {
        "name": "主体持续经营年限",
        "category": "产销经营类",
        "weight": 0.044,
        "unit": "年",
        "type": "continuous",
    },
    "purchase_order": {
        "name": "长期农产品收购订单",
        "category": "产销经营类",
        "weight": 0.037,
        "unit": "",
        "type": "categorical",
    },
    "annual_revenue": {
        "name": "农产品年稳定营收",
        "category": "产销经营类",
        "weight": 0.031,
        "unit": "万元",
        "type": "continuous",
    },
    "credit_record": {
        "name": "历年涉农信贷履约记录",
        "category": "产销经营类",
        "weight": 0.037,
        "unit": "",
        "type": "categorical",
    },
}

INDICATOR_ORDER: list[str] = list(INDICATOR_META.keys())

# camelCase（前端契约）→ snake_case（模型字段）映射
CAMEL_TO_SNAKE: dict[str, str] = {
    "landConfirmedArea": "land_confirmed_area",
    "landTransferYears": "land_transfer_years",
    "landTransferStability": "land_transfer_stability",
    "blackSoilProtection": "black_soil_protection",
    "grainSubsidy": "grain_subsidy",
    "machinerySubsidy": "machinery_subsidy",
    "grainScaleSubsidy": "grain_scale_subsidy",
    "specialtyCropSubsidy": "specialty_crop_subsidy",
    "insuranceYears": "insurance_years",
    "claimCount": "claim_count",
    "facilityInsurance": "facility_insurance",
    "yearsOperating": "years_operating",
    "purchaseOrder": "purchase_order",
    "annualRevenue": "annual_revenue",
    "creditRecord": "credit_record",
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


def _score_land_confirmed_area(v: float) -> float:
    # 文档：>300亩25分；200-300-20；50-200-12；<50-5（归一化 0-100）
    return _bin_score(v, [(0, 50, 20), (50, 200, 48), (200, 300, 80), (300, 1e18, 100)])


def _score_land_transfer_years(v: float) -> float:
    # 文档：≥3年书面20分；1年书面10；口头2（归一化 0-100）
    return _bin_score(v, [(0, 1, 10), (1, 3, 50), (3, 1e18, 100)])


def _score_land_transfer_stability(v: str) -> float:
    # 文档：稳定15分；小幅调整6；频繁变更0
    return {"稳定": 100, "小幅调整": 40, "频繁变更": 0}.get(v, 40)


def _score_black_soil_protection(v: float) -> float:
    # 黑土地保护性耕作覆盖比例（0-100%）：全覆盖10分；部分4；无0
    return _bin_score(v, [(0, 40, 0), (40, 80, 40), (80, 1e18, 100)])


def _score_grain_subsidy(v: float) -> float:
    # 地力补贴：>1万18分；5千-1万12；1千-5千6；<1千2（归一化 0-100）
    return _bin_score(v, [(0, 1000, 11), (1000, 5000, 33), (5000, 10000, 67), (10000, 1e18, 100)])


def _score_machinery_subsidy(v: float) -> float:
    # 农机补贴：近3年申领大型15分；小型6；无0
    return _bin_score(v, [(0, 10000, 0), (10000, 50000, 40), (50000, 1e18, 100)])


def _score_grain_scale_subsidy(v: float) -> float:
    # 规模种植补贴：连续2年12分；单次5；无0
    return _bin_score(v, [(0, 5000, 0), (5000, 20000, 42), (20000, 1e18, 100)])


def _score_specialty_crop_subsidy(v: float) -> float:
    # 特色作物补贴：常年10分；无0
    return _bin_score(v, [(0, 1000, 0), (1000, 1e18, 100)])


def _score_insurance_years(v: float) -> float:
    # 投保年限：≥3年16分；1-2年8；无0
    return _bin_score(v, [(0, 1, 0), (1, 3, 50), (3, 1e18, 100)])


def _score_claim_count(v: float) -> float:
    # 理赔频次：无12分；1次6；≥2次1
    if v <= 0:
        return 100.0
    if v <= 1:
        return 50.0
    return 8.0


def _score_facility_insurance(v: str) -> float:
    # 设施附加险：完整8分；仅基础3；无0
    return {"完整投保": 100, "仅基础险": 37, "未投保": 0}.get(v, 37)


def _score_years_operating(v: float) -> float:
    # 经营年限：≥5年14分；2-5年7；<2年2
    return _bin_score(v, [(0, 2, 14), (2, 5, 50), (5, 1e18, 100)])


def _score_purchase_order(v: str) -> float:
    # 收购订单：年度12分；零散4；无0
    return {"年度订单": 100, "零散收购": 33, "无稳定渠道": 0}.get(v, 33)


def _score_annual_revenue(v: float) -> float:
    # 营收（万元）：>50万10分；10-50万5；<10万1
    return _bin_score(v, [(0, 10, 10), (10, 50, 50), (50, 1e18, 100)])


def _score_credit_record(v: str) -> float:
    # 信贷履约：无逾期12分；有逾期扣10（记0）
    return {"无逾期": 100, "有逾期": 0}.get(v, 50)


RULE_SCORERS: dict[str, Any] = {
    "land_confirmed_area": _score_land_confirmed_area,
    "land_transfer_years": _score_land_transfer_years,
    "land_transfer_stability": _score_land_transfer_stability,
    "black_soil_protection": _score_black_soil_protection,
    "grain_subsidy": _score_grain_subsidy,
    "machinery_subsidy": _score_machinery_subsidy,
    "grain_scale_subsidy": _score_grain_scale_subsidy,
    "specialty_crop_subsidy": _score_specialty_crop_subsidy,
    "insurance_years": _score_insurance_years,
    "claim_count": _score_claim_count,
    "facility_insurance": _score_facility_insurance,
    "years_operating": _score_years_operating,
    "purchase_order": _score_purchase_order,
    "annual_revenue": _score_annual_revenue,
    "credit_record": _score_credit_record,
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
