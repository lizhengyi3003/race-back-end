"""评估记录管理服务"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import BizException
from app.models.assessment import AssessmentRecord
from app.models.indicator import IndicatorConfig, IndicatorValue
from app.schemas.common import PageData
from app.schemas.record import AssessmentRecordOut, IndicatorValueOut


def _indicator_values(db: Session, record_id: int) -> list[IndicatorValueOut]:
    """加载一次评估的动态指标明细（code→名称/层级/单位）。"""
    rows = (
        db.query(IndicatorValue, IndicatorConfig)
        .outerjoin(IndicatorConfig, IndicatorConfig.code == IndicatorValue.indicator_code)
        .filter(IndicatorValue.assessment_id == record_id)
        .order_by(IndicatorValue.id)
        .all()
    )
    return [
        IndicatorValueOut(
            code=v.indicator_code,
            name=c.name if c else v.indicator_code,
            level=c.level if c else "",
            unit=c.unit if c else "",
            value=v.value,
            quality=v.quality,
        )
        for v, c in rows
    ]


def list_records(
    db: Session,
    page: int = 1,
    size: int = 20,
    keyword: str | None = None,
    level: str | None = None,
    business_type: str | None = None,
) -> PageData[AssessmentRecordOut]:
    query = db.query(AssessmentRecord)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                AssessmentRecord.enterprise_name.like(like),
                AssessmentRecord.product_type.like(like),
            )
        )
    if level:
        query = query.filter(AssessmentRecord.level == level)
    if business_type:
        query = query.filter(AssessmentRecord.business_type == business_type)

    total = query.count()
    items = query.order_by(AssessmentRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    return PageData(
        total=total,
        page=page,
        size=size,
        items=[AssessmentRecordOut.from_model(r) for r in items],
    )


def get_record(db: Session, record_id: int) -> AssessmentRecordOut:
    r = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not r:
        raise BizException("记录不存在", 404)
    values = _indicator_values(db, record_id)
    return AssessmentRecordOut.from_model(r, indicator_values=values or None)


def delete_record(db: Session, record_id: int) -> None:
    r = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not r:
        raise BizException("记录不存在", 404)
    db.delete(r)
    db.commit()


def all_records(db: Session, limit: int | None = None) -> list[AssessmentRecord]:
    query = db.query(AssessmentRecord).order_by(AssessmentRecord.id.desc())
    if limit:
        query = query.limit(limit)
    return query.all()
