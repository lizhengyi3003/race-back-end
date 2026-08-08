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

CATEGORICAL_FIELDS: list[str] = [f for f, m in INDICATOR_META.items() if m["type"] == "categorical"]
