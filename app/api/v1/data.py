"""数据导入导出接口"""

import csv
import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.ml.predictor import assess
from app.ml.training import load_active_model
from app.models.assessment import AssessmentRecord
from app.models.user import User
from app.services import model_service, record_service
from app.services.risk_service import _COLUMN_MAP

router = APIRouter(prefix="/data", tags=["数据管理"])

# CSV 列（camelCase，与前端契约一致）
CSV_COLUMNS = [
    "enterpriseName",
    "businessType",
    "productType",
    "age",
    "education",
    "familyMembers",
    "landConfirmedArea",
    "landTransferYears",
    "plantingStructure",
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
    "revenueStability",
    "creditStatus",
    "loanHistory",
    "loanOverdueHistory",
]

NUMERIC_FIELDS = {
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
}


@router.get("/template", summary="下载 CSV 导入模板")
def download_template():
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerow(
        {
            "enterpriseName": "示例：黑龙江XX家庭农场",
            "businessType": "种植",
            "productType": "玉米",
            "age": 48,
            "education": "初中",
            "familyMembers": 4,
            "landConfirmedArea": 800,
            "landTransferYears": 8,
            "plantingStructure": "主粮种植",
            "landUtilization": 92,
            "grainSubsidy": 42000,
            "machinerySubsidy": 26000,
            "otherSubsidy": 8000,
            "insuranceCoverage": 95,
            "claimCount": 0,
            "claimAmount": 0,
            "claimRatio": 3,
            "yearsOperating": 12,
            "businessConcentration": 82,
            "annualRevenue": 160,
            "revenueStability": "稳定",
            "creditStatus": "无不良记录",
            "loanHistory": 3,
            "loanOverdueHistory": 0,
        }
    )
    content = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=risk_import_template.csv"},
    )


@router.post("/import", response_model=ApiResponse, summary="批量导入评估记录（CSV）")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    model = load_active_model(db)
    thresholds = model_service.get_thresholds(db)

    imported = 0
    errors: list[dict] = []
    for idx, row in enumerate(reader, start=2):
        payload: dict = {}
        try:
            for col in CSV_COLUMNS:
                val = row.get(col, "")
                if val in (None, ""):
                    continue
                if col in NUMERIC_FIELDS:
                    try:
                        payload[col] = float(val)
                    except ValueError:
                        continue
                else:
                    payload[col] = str(val)
            if not payload.get("enterpriseName"):
                continue
            result = assess(payload, model=model, thresholds=thresholds)
            rec = AssessmentRecord(
                enterprise_name=payload.get("enterpriseName", ""),
                business_type=payload.get("businessType", ""),
                product_type=payload.get("productType", ""),
                **{_COLUMN_MAP[k]: payload.get(k) for k in CSV_COLUMNS[3:]},
                score=result["score"],
                probability=result["probability"],
                level=result["level"],
                suggested_amount=result["suggestedAmount"],
                suggested_rate=result["suggestedRate"],
                input_json=payload,
                result_json=result,
                assessor_name=user.username,
            )
            db.add(rec)
            imported += 1
        except Exception as e:  # noqa: BLE001
            errors.append({"row": idx, "error": str(e)})
    db.commit()
    return ok({"imported": imported, "errors": errors}, message=f"成功导入 {imported} 条记录")


@router.get("/export", summary="导出评估记录（CSV）")
def export_csv(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    records = record_service.all_records(db)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id"]
        + CSV_COLUMNS
        + ["score", "probability", "level", "suggestedAmount", "suggestedRate", "createdAt"],
    )
    writer.writeheader()
    for r in records:
        row = {
            "id": r.id,
            "enterpriseName": r.enterprise_name,
            "businessType": r.business_type,
            "productType": r.product_type,
            "age": r.age,
            "education": r.education,
            "familyMembers": r.family_members,
            "landConfirmedArea": r.land_confirmed_area,
            "landTransferYears": r.land_transfer_years,
            "plantingStructure": r.planting_structure,
            "landUtilization": r.land_utilization,
            "grainSubsidy": r.grain_subsidy,
            "machinerySubsidy": r.machinery_subsidy,
            "otherSubsidy": r.other_subsidy,
            "insuranceCoverage": r.insurance_coverage,
            "claimCount": r.claim_count,
            "claimAmount": r.claim_amount,
            "claimRatio": r.claim_ratio,
            "yearsOperating": r.years_operating,
            "businessConcentration": r.business_concentration,
            "annualRevenue": r.annual_revenue,
            "revenueStability": r.revenue_stability,
            "creditStatus": r.credit_status,
            "loanHistory": r.loan_history,
            "loanOverdueHistory": r.loan_overdue_history,
            "score": r.score,
            "probability": r.probability,
            "level": r.level,
            "suggestedAmount": r.suggested_amount,
            "suggestedRate": r.suggested_rate,
            "createdAt": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        }
        writer.writerow(row)
    content = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=assessment_records.csv"},
    )
