"""风险评估接口"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.record import AssessmentRecordOut
from app.schemas.risk import DynamicRiskInput, RiskInput, RiskResult
from app.services import record_service, risk_service

router = APIRouter(prefix="/risk", tags=["椋庨櫓璇勪及"])


@router.post("/assess", response_model=ApiResponse[RiskResult], summary="鎻愪氦椋庨櫓璇勪及")
def assess(
    req: RiskInput,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    payload = req.model_dump()
    result = risk_service.assess_and_store(db, payload, assessor_name=user.username if user else None)
    return ok(result)


@router.post("/assess-dynamic", response_model=ApiResponse[RiskResult], summary="动态指标体系评估（专家引擎）")
def assess_dynamic(
    req: DynamicRiskInput,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    payload = req.model_dump()
    result = risk_service.assess_dynamic_and_store(
        db, payload, assessor_name=user.username if user else None
    )
    return ok(result)


@router.get("/records", response_model=ApiResponse[PageData[AssessmentRecordOut]], summary="评估记录分页")
def records(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    level: str | None = None,
    businessType: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    data = record_service.list_records(db, page, size, keyword, level, businessType)
    return ok(data)


@router.get("/records/{record_id}", response_model=ApiResponse[AssessmentRecordOut], summary="记录详情")
def record_detail(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(record_service.get_record(db, record_id))


@router.delete("/records/{record_id}", response_model=ApiResponse, summary="删除记录")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    record_service.delete_record(db, record_id)
    return ok(message="删除成功")
