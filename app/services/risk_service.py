"""风险评估服务：加载模型与阈值 → 评估 → 落库"""

from sqlalchemy.orm import Session

from app.ml.expert_engine import expert_assess
from app.ml.predictor import assess
from app.ml.training import load_active_model
from app.models.assessment import AssessmentRecord
from app.models.indicator import IndicatorValue
from app.services.model_service import get_thresholds

# 前端 camelCase 字段 → ORM 列名映射（供 assess 落库与 CSV 导入共用）
_COLUMN_MAP = {
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


def assess_and_store(db: Session, payload: dict, assessor_name: str | None = None) -> dict:
    model = load_active_model(db)
    thresholds = get_thresholds(db)
    result = assess(payload, model=model, thresholds=thresholds)

    rec = AssessmentRecord(
        enterprise_name=payload.get("enterpriseName", ""),
        business_type=payload.get("businessType", ""),
        product_type=payload.get("productType", ""),
        **{_COLUMN_MAP[k]: payload.get(k) for k in _COLUMN_MAP},
        score=result["score"],
        probability=result["probability"],
        level=result["level"],
        suggested_amount=result["suggestedAmount"],
        suggested_rate=result["suggestedRate"],
        input_json=payload,
        result_json=result,
        assessor_name=assessor_name,
    )
    db.add(rec)
    db.commit()
    return result


def _combine_mixed(sub_results: dict[str, tuple[float, dict]]) -> dict:
    """混合经营：按子类型比例加权合并专家评估结果。"""
    total_ratio = sum(r for r, _ in sub_results.values()) or 1.0
    score = round(sum(ratio * res["score"] for ratio, res in sub_results.values()) / total_ratio)
    probability = sum(ratio * res["probability"] for ratio, res in sub_results.values()) / total_ratio
    level = "低风险" if score >= 700 else ("中等风险" if score >= 500 else "高风险")

    contributions = []
    for ratio, res in sub_results.values():
        for c in res["contributions"]:
            c2 = dict(c)
            c2["weight"] = round(c2["weight"] * ratio / total_ratio, 4)
            contributions.append(c2)
    deductions = sorted(
        [d for _, res in sub_results.values() for d in res["deductions"]],
        key=lambda x: x["score"],
    )[:3]

    # 额度/利率按加权分
    amount = round(sum(ratio * res["suggestedAmount"] for ratio, res in sub_results.values()) / total_ratio, 2)
    rate = round(sum(ratio * res["suggestedRate"] for ratio, res in sub_results.values()) / total_ratio, 2)
    advice = _build_mixed_advice(level, amount, rate)

    return {
        "score": score,
        "probability": round(probability, 4),
        "level": level,
        "suggestedAmount": amount,
        "suggestedRate": rate,
        "contributions": contributions,
        "deductions": deductions,
        "advice": advice,
        "overrides": [],
        "veto": None,
        "completeness": next(iter(sub_results.values()))[1]["completeness"],
    }


def _build_mixed_advice(level: str, amount: float, rate: float) -> str:
    if level == "低风险":
        return f"【混合经营】综合评估良好，建议授信约 {amount} 万元，执行优惠利率 {rate}%。"
    if level == "中等风险":
        return f"【混合经营】建议审慎授信，额度约 {amount} 万元，利率 {rate}%，可补充担保。"
    return f"【混合经营】建议暂缓放贷或要求足额抵押物，参考额度 {amount} 万元，利率 {rate}%。"


def assess_dynamic_and_store(
    db: Session,
    payload: dict,
    assessor_name: str | None = None,
) -> dict:
    """动态指标体系评估（专家引擎）：支持单经营类型与混合经营加权。"""
    indicators = payload.get("indicators", {}) or {}
    business_type = payload.get("businessType", "")
    mixed = payload.get("mixedBusiness", {}) or {}

    if business_type == "MIXED" and mixed:
        sub_results: dict[str, tuple[float, dict]] = {}
        for code, ratio in mixed.items():
            if ratio > 0:
                sub_results[code] = (float(ratio), expert_assess(db, code, indicators))
        if sub_results:
            result = _combine_mixed(sub_results)
        else:
            result = expert_assess(db, "", indicators)
    else:
        result = expert_assess(db, business_type, indicators)

    # 落库：动态输入/结果快照 + 指标明细
    rec = AssessmentRecord(
        enterprise_name=payload.get("enterpriseName", ""),
        business_type=business_type,
        product_type=payload.get("productType", ""),
        score=result["score"],
        probability=result["probability"],
        level=result["level"],
        suggested_amount=result["suggestedAmount"],
        suggested_rate=result["suggestedRate"],
        input_json=payload,
        result_json=result,
        assessor_name=assessor_name,
    )
    db.add(rec)
    db.flush()  # 拿到 rec.id

    for code, value in indicators.items():
        db.add(IndicatorValue(assessment_id=rec.id, indicator_code=code, value=str(value)))

    db.commit()
    return result
