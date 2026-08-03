"""风险评估服务：加载模型与阈值 → 评估 → 落库"""

from sqlalchemy.orm import Session

from app.ml.predictor import assess
from app.ml.training import load_active_model
from app.models.assessment import AssessmentRecord
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
