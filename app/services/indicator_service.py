"""指标配置业务逻辑：类别树、渐进式表单字段、枚举选项解析。"""

from sqlalchemy.orm import Session

from app.models.indicator import IndicatorCategory, IndicatorConfig
from app.schemas.indicator import CategoryNode, IndicatorConfigOut, IndicatorField, IndicatorTree

# 枚举取值说明中用于分隔选项的符号
_OPTION_SEP = ["/", "／", "、", "，"]


def _parse_options(value_range: str) -> list[str]:
    """从枚举指标的『取值说明』解析选项列表（如 '无/省级/国家级地理标志' → 3 项）。"""
    v = (value_range or "").strip()
    if not v:
        return []
    # 取说明中最可能的选项段：优先按分隔符拆分，去掉数量/单位等描述
    for sep in _OPTION_SEP:
        if sep in v:
            parts = [p.strip() for p in v.split(sep) if p.strip()]
            # 过滤明显不是选项的描述性短语（含数字区间/大于小于/年月等）
            filtered = [p for p in parts if not any(
                c in p for c in ("≥", "≤", ">", "<", "0-", "%", "年", "月", "小时", "亩")
            )]
            return filtered or parts
    return [v] if v and len(v) <= 12 else []


def _to_field(c: IndicatorConfig) -> IndicatorField:
    return IndicatorField(
        code=c.code,
        name=c.name,
        level=c.level,
        category_code=c.category_code,
        category_name=c.category_name,
        indicator_type=c.indicator_type,  # type: ignore[arg-type]
        unit=c.unit,
        value_range=c.value_range,
        options=_parse_options(c.value_range) if c.indicator_type == "枚举" else [],
        data_source=c.data_source,
        is_feature=c.is_feature,
        risk_meaning=c.risk_meaning,
        weight_star=c.weight_star,
        region=c.region,
        is_veto=c.is_veto,
        cycle=c.cycle,
        scoring_rule=c.scoring_rule,
        required=c.indicator_type != "文本",
    )


def get_indicator_tree(db: Session) -> IndicatorTree:
    """构建指标树：基本项字段 + 大类→中类→小类 类别树（含指标数）。"""
    basic = (
        db.query(IndicatorConfig)
        .filter(IndicatorConfig.level == "基本项")
        .order_by(IndicatorConfig.display_order)
        .all()
    )
    cats = db.query(IndicatorCategory).all()
    cat_by_code = {c.code: c for c in cats}
    counts = _indicator_counts(db)

    def build_node(cat: IndicatorCategory) -> CategoryNode:
        children = [
            build_node(child)
            for child in cats
            if child.parent_code == cat.code
        ]
        children.sort(key=lambda n: n.code)
        return CategoryNode(
            code=cat.code,
            name=cat.name,
            level=cat.level,
            display=f"{cat.code} {cat.name}",
            indicator_count=counts.get(cat.code, 0),
            children=children,
        )

    roots = [build_node(c) for c in cats if c.parent_code is None]
    roots.sort(key=lambda n: n.code)
    return IndicatorTree(
        basic=[_to_field(b) for b in basic],
        categories=roots,
    )


def _indicator_counts(db: Session) -> dict[str, int]:
    from collections import Counter

    rows = db.query(IndicatorConfig.category_code, IndicatorConfig.level).all()
    return Counter(code for code, _ in rows)


def get_indicator_config(
    db: Session,
    business_type: str,
    middle_type: str = "",
    small_type: str = "",
) -> IndicatorConfigOut:
    """渐进式表单配置：基本项 + 按所选类别逐级追加指标。"""
    basic = (
        db.query(IndicatorConfig)
        .filter(IndicatorConfig.level == "基本项")
        .order_by(IndicatorConfig.display_order)
        .all()
    )
    indicators: list[IndicatorConfig] = []

    levels: list[tuple[str, str]] = [
        ("大类", business_type),
    ]
    if middle_type:
        levels.append(("中类", middle_type))
    if small_type:
        levels.append(("小类", small_type))

    for level, cat_code in levels:
        if not cat_code:
            continue
        rows = (
            db.query(IndicatorConfig)
            .filter(IndicatorConfig.level == level, IndicatorConfig.category_code == cat_code)
            .order_by(IndicatorConfig.display_order)
            .all()
        )
        indicators.extend(rows)

    return IndicatorConfigOut(
        basic=[_to_field(b) for b in basic],
        indicators=[_to_field(i) for i in indicators],
        selected={
            "businessType": business_type,
            "middleType": middle_type,
            "smallType": small_type,
        },
    )
