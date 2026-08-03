"""评估记录输出（camelCase，供管理平台/前端使用）"""

from datetime import datetime

from pydantic import BaseModel


class AssessmentRecordOut(BaseModel):
    id: int
    enterpriseName: str
    businessType: str
    productType: str

    landConfirmedArea: float | None = None
    landTransferYears: float | None = None
    landTransferStability: str | None = None
    blackSoilProtection: float | None = None
    grainSubsidy: float | None = None
    machinerySubsidy: float | None = None
    grainScaleSubsidy: float | None = None
    specialtyCropSubsidy: float | None = None
    insuranceYears: float | None = None
    claimCount: float | None = None
    facilityInsurance: str | None = None
    yearsOperating: float | None = None
    purchaseOrder: str | None = None
    annualRevenue: float | None = None
    creditRecord: str | None = None

    score: int
    probability: float
    level: str
    suggestedAmount: float
    suggestedRate: float
    assessorName: str | None = None
    createdAt: datetime | None = None

    # 完整快照（详情查看）
    input: dict | None = None
    result: dict | None = None

    @classmethod
    def from_model(cls, r) -> "AssessmentRecordOut":
        return cls(
            id=r.id,
            enterpriseName=r.enterprise_name,
            businessType=r.business_type,
            productType=r.product_type,
            landConfirmedArea=r.land_confirmed_area,
            landTransferYears=r.land_transfer_years,
            landTransferStability=r.land_transfer_stability,
            blackSoilProtection=r.black_soil_protection,
            grainSubsidy=r.grain_subsidy,
            machinerySubsidy=r.machinery_subsidy,
            grainScaleSubsidy=r.grain_scale_subsidy,
            specialtyCropSubsidy=r.specialty_crop_subsidy,
            insuranceYears=r.insurance_years,
            claimCount=r.claim_count,
            facilityInsurance=r.facility_insurance,
            yearsOperating=r.years_operating,
            purchaseOrder=r.purchase_order,
            annualRevenue=r.annual_revenue,
            creditRecord=r.credit_record,
            score=r.score,
            probability=r.probability,
            level=r.level,
            suggestedAmount=r.suggested_amount,
            suggestedRate=r.suggested_rate,
            assessorName=r.assessor_name,
            createdAt=r.created_at,
            input=r.input_json,
            result=r.result_json,
        )
