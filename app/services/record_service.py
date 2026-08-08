"""评估记录管理服务"""

from sqlalchemy.orm import Session

from app.core.exceptions import BizException
from app.models.assessment import AssessmentRecord
from app.models.indicator import IndicatorConfig, IndicatorValue
from app.schemas.common import PageData
from app.schemas.record import AssessmentRecordOut, IndicatorValueOut

# 15 项传统评估（v1.0 表单）字段元数据：input_json 键 → 名称/层级/单位
LEGACY_15_FIELDS: list[tuple[str, str, str, str]] = [
    ("landConfirmedArea", "确权耕地总面积", "维度一：土地经营", "亩"),
    ("landTransferYears", "土地流转合同年限", "维度一：土地经营", "年"),
    ("landTransferStability", "土地流转稳定性", "维度一：土地经营", ""),
    ("blackSoilProtection", "黑土地保护性耕作面积", "维度一：土地经营", "亩"),
    ("grainSubsidy", "耕地地力保护补贴", "维度二：农业补贴", "元"),
    ("machinerySubsidy", "大型农机购置补贴", "维度二：农业补贴", "元"),
    ("grainScaleSubsidy", "粮食规模种植专项补贴", "维度二：农业补贴", "元"),
    ("specialtyCropSubsidy", "特色经济作物补贴", "维度二：农业补贴", "元"),
    ("insuranceYears", "农业保险连续投保年限", "维度三：农业保险", "年"),
    ("claimCount", "历史保险理赔频次", "维度三：农业保险", "次"),
    ("facilityInsurance", "设施农业附加保险", "维度三：农业保险", ""),
    ("yearsOperating", "主体持续经营年限", "维度四：产销经营", "年"),
    ("purchaseOrder", "长期农产品收购订单", "维度四：产销经营", ""),
    ("annualRevenue", "农产品年稳定营收", "维度四：产销经营", "万元"),
    ("creditRecord", "历年涉农信贷履约记录", "维度四：产销经营", ""),
]


def _legacy_indicator_values(input_json) -> list[IndicatorValueOut] | None:
    """旧 15 项评估记录：从 input_json 快照解析原始表单明细（无动态指标明细时回退）。"""
    if isinstance(input_json, str):
        # 兼容历史字符串化 JSON 快照
        try:
            import json

            input_json = json.loads(input_json)
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(input_json, dict):
        return None
    out = []
    for key, name, level, unit in LEGACY_15_FIELDS:
        v = input_json.get(key)
        if v is None or v == "":
            continue
        out.append(
            IndicatorValueOut(
                code=key, name=name, level=level, unit=unit, value=str(v), quality="直接"
            )
        )
    return out or None


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
    user_id: int | None = None,
) -> PageData[AssessmentRecordOut]:
    """评估记录分页；user_id 非 None 时仅返回该用户自己的记录。"""
    query = db.query(AssessmentRecord)
    if user_id is not None:
        query = query.filter(AssessmentRecord.user_id == user_id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(AssessmentRecord.enterprise_name.like(like))
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


def _check_owner(r: AssessmentRecord, user_id: int | None) -> None:
    """归属校验：非空 user_id 时仅允许操作本人记录。"""
    if user_id is not None and r.user_id != user_id:
        raise BizException("无权访问该记录", 403)


def get_record(db: Session, record_id: int, user_id: int | None = None) -> AssessmentRecordOut:
    r = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not r:
        raise BizException("记录不存在", 404)
    _check_owner(r, user_id)
    values = _indicator_values(db, record_id)
    # 兼容旧 15 项评估：无动态指标明细时，从 input_json 快照解析原始表单
    if not values:
        values = _legacy_indicator_values(r.input_json)
    return AssessmentRecordOut.from_model(r, indicator_values=values or None)


def delete_record(db: Session, record_id: int, user_id: int | None = None) -> None:
    r = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not r:
        raise BizException("记录不存在", 404)
    _check_owner(r, user_id)
    db.delete(r)
    db.commit()


def all_records(db: Session, limit: int | None = None) -> list[AssessmentRecord]:
    query = db.query(AssessmentRecord).order_by(AssessmentRecord.id.desc())
    if limit:
        query = query.limit(limit)
    return query.all()
