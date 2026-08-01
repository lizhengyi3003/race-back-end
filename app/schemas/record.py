"""评估记录输出（camelCase，供管理平台/前端使用）"""

from datetime import datetime

from pydantic import BaseModel


class AssessmentRecordOut(BaseModel):
    id: int
    enterpriseName: str
    businessType: str
    productType: str

    age: float | None = None
    education: str | None = None
    familyMembers: float | None = None
    landConfirmedArea: float | None = None
    landTransferYears: float | None = None
    plantingStructure: str | None = None
    landUtilization: float | None = None
    grainSubsidy: float | None = None
    machinerySubsidy: float | None = None
    otherSubsidy: float | None = None
    insuranceCoverage: float | None = None
    claimCount: float | None = None
    claimAmount: float | None = None
    claimRatio: float | None = None
    yearsOperating: float | None = None
    businessConcentration: float | None = None
    annualRevenue: float | None = None
    revenueStability: str | None = None
    creditStatus: str | None = None
    loanHistory: float | None = None
    loanOverdueHistory: float | None = None

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
            age=r.age,
            education=r.education,
            familyMembers=r.family_members,
            landConfirmedArea=r.land_confirmed_area,
            landTransferYears=r.land_transfer_years,
            plantingStructure=r.planting_structure,
            landUtilization=r.land_utilization,
            grainSubsidy=r.grain_subsidy,
            machinerySubsidy=r.machinery_subsidy,
            otherSubsidy=r.other_subsidy,
            insuranceCoverage=r.insurance_coverage,
            claimCount=r.claim_count,
            claimAmount=r.claim_amount,
            claimRatio=r.claim_ratio,
            yearsOperating=r.years_operating,
            businessConcentration=r.business_concentration,
            annualRevenue=r.annual_revenue,
            revenueStability=r.revenue_stability,
            creditStatus=r.credit_status,
            loanHistory=r.loan_history,
            loanOverdueHistory=r.loan_overdue_history,
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
