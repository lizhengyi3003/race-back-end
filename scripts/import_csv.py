"""命令行：批量导入评估记录（CSV，字段与风险输入一致）"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal  # noqa: E402
from app.ml.predictor import assess  # noqa: E402
from app.ml.training import load_active_model  # noqa: E402
from app.models.assessment import AssessmentRecord  # noqa: E402

FIELD_MAP = {
    "enterpriseName": "enterprise_name",
    "businessType": "business_type",
    "productType": "product_type",
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


def import_csv(path: str) -> int:
    db = SessionLocal()
    model = load_active_model(db)
    count = 0
    try:
        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                payload = {}
                for k, v in row.items():
                    if k in FIELD_MAP and v not in (None, ""):
                        if k in (
                            "age",
                            "familyMembers",
                            "landConfirmedArea",
                            "landTransferYears",
                            "landUtilization",
                            "grainSubsidy",
                            "machinerySubsidy",
                            "otherSubsidy",
                            "insuranceCoverage",
                            "claimCount",
                            "claimAmount",
                            "claimRatio",
                            "yearsOperating",
                            "businessConcentration",
                            "annualRevenue",
                            "loanHistory",
                            "loanOverdueHistory",
                        ):
                            try:
                                payload[k] = float(v)
                            except ValueError:
                                payload[k] = None
                        else:
                            payload[k] = v
                if not payload.get("enterpriseName"):
                    continue
                result = assess(payload, model=model)
                rec = AssessmentRecord(
                    enterprise_name=payload.get("enterpriseName", ""),
                    business_type=payload.get("businessType", ""),
                    product_type=payload.get("productType", ""),
                    **{
                        FIELD_MAP[k]: payload.get(k)
                        for k in FIELD_MAP
                        if k not in ("enterpriseName", "businessType", "productType")
                    },
                    score=result["score"],
                    probability=result["probability"],
                    level=result["level"],
                    suggested_amount=result["suggestedAmount"],
                    suggested_rate=result["suggestedRate"],
                    input_json=payload,
                    result_json=result,
                    assessor_name="cli-import",
                )
                db.add(rec)
                count += 1
        db.commit()
    finally:
        db.close()
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python scripts/import_csv.py <csv文件路径>")
        sys.exit(1)
    n = import_csv(sys.argv[1])
    print(f"✅ 已导入 {n} 条评估记录")
