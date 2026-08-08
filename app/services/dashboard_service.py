"""数据看板统计服务"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assessment import AssessmentRecord
from app.models.indicator import IndicatorCategory
from app.schemas.dashboard import DashboardStats, IndustryItem, ScoreDistItem, TrendItem


def stats(db: Session) -> DashboardStats:
    total = db.query(func.count(AssessmentRecord.id)).scalar() or 0
    if total == 0:
        return DashboardStats(
            totalAssess=0,
            avgScore=0,
            highRiskRate=0,
            passRate=0,
            lowCount=0,
            midCount=0,
            highCount=0,
        )
    avg_score = db.query(func.avg(AssessmentRecord.score)).scalar() or 0
    low = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "低风险").scalar() or 0
    mid = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "中等风险").scalar() or 0
    high = db.query(func.count(AssessmentRecord.id)).filter(AssessmentRecord.level == "高风险").scalar() or 0
    return DashboardStats(
        totalAssess=total,
        avgScore=round(float(avg_score), 1),
        highRiskRate=round(high / total * 100, 1),
        passRate=round((low + mid) / total * 100, 1),
        lowCount=low,
        midCount=mid,
        highCount=high,
    )


def industry_distribution(db: Session) -> list[IndustryItem]:
    # 大类编码 → 名称映射（来自指标类别树 level=大类；MIXED 为混合经营特殊处理）
    name_map = {
        c: n
        for c, n in db.query(IndicatorCategory.code, IndicatorCategory.name)
        .filter(IndicatorCategory.level == "大类")
        .all()
    }
    name_map["MIXED"] = "混合经营"
    rows = (
        db.query(
            AssessmentRecord.business_type,
            func.count(AssessmentRecord.id),
        )
        .group_by(AssessmentRecord.business_type)
        .all()
    )
    items = []
    for code, cnt in rows:
        label = name_map.get(code) or (code or "未填写")
        # 统计该行业各风险等级数，取占比最高者作为行业风险标签
        level_cnt = {
            lv: db.query(func.count(AssessmentRecord.id))
            .filter(AssessmentRecord.business_type == code, AssessmentRecord.level == lv)
            .scalar()
            or 0
            for lv in ("低风险", "中等风险", "高风险")
        }
        risk = max(level_cnt, key=level_cnt.get) if sum(level_cnt.values()) else "中"
        items.append(IndustryItem(name=label, value=int(cnt), risk=risk))
    return items


def score_distribution(db: Session) -> list[ScoreDistItem]:
    ranges = [
        (0, 300, "0-300"),
        (300, 500, "300-500"),
        (500, 600, "500-600"),
        (600, 700, "600-700"),
        (700, 800, "700-800"),
        (800, 901, "800-1000"),
    ]
    items = []
    for lo, hi, label in ranges:
        cnt = (
            db.query(func.count(AssessmentRecord.id))
            .filter(AssessmentRecord.score >= lo, AssessmentRecord.score < hi)
            .scalar()
            or 0
        )
        items.append(ScoreDistItem(range=label, count=cnt))
    return items


def trend(db: Session, days: int = 30) -> list[TrendItem]:
    start = datetime.now() - timedelta(days=days - 1)
    rows = (
        db.query(
            func.date(AssessmentRecord.created_at).label("d"),
            func.count(AssessmentRecord.id),
            func.avg(AssessmentRecord.score),
        )
        .filter(AssessmentRecord.created_at >= start)
        .group_by(func.date(AssessmentRecord.created_at))
        .all()
    )
    by_date = {str(d): (c, s) for d, c, s in rows}
    items = []
    for i in range(days):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        cnt, avg = by_date.get(day, (0, 0))
        items.append(TrendItem(date=day, count=cnt, avgScore=round(float(avg or 0), 1)))
    return items
