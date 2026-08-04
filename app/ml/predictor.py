"""预测器：将输入转为 RiskResult（严格对齐前端契约）。

- 有训练模型：评分卡贡献分（-B·coef·(WOE-mean)）驱动总分与贡献度
- 无训练模型：规则评分卡兜底（对齐前端 riskModel.ts）
"""

from __future__ import annotations

from app.ml.indicators import (
    CAMEL_TO_SNAKE,
    INDICATOR_META,
    INDICATOR_ORDER,
    rule_sub_score,
)
from app.ml.scorecard import Scorecard


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np_exp(-x))


def np_exp(x: float) -> float:
    import math

    return math.exp(x)


def normalize_input(input_data: dict) -> dict:
    """将前端 camelCase 输入转换为模型 snake_case 字段（同时兼容 snake_case 输入）"""
    norm: dict = {}
    for key, value in input_data.items():
        if key in CAMEL_TO_SNAKE:
            norm[CAMEL_TO_SNAKE[key]] = value
        elif key in INDICATOR_META:
            norm[key] = value
        else:
            norm[key] = value
    return norm


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _f(x) -> float:
    """统一转 float，避免 np 类型泄漏"""
    return float(x)


def _deduction_reason(factor: str, score: float) -> str:
    if score >= 80:
        return f"{factor}表现良好"
    if score >= 60:
        return f"{factor}尚可，仍有提升空间"
    if score >= 40:
        return f"{factor}偏弱，对信用评分造成一定拖累"
    return f"{factor}明显不足，是拉低信用评分的重要因素"


def _build_advice(score: float, prob: float, level: str, amount: float, rate: float) -> str:
    if level == "低风险":
        return (
            f"该企业信用评分 {int(score)} 分，违约概率仅 {prob * 100:.1f}%，综合风险可控。"
            f"建议优先审批，授信额度 {amount} 万元，执行优惠利率 {rate}%。"
        )
    if level == "中等风险":
        return (
            f"该企业信用评分 {int(score)} 分，违约概率 {prob * 100:.1f}%，信用状况一般。"
            f"建议审慎授信，额度控制在 {amount} 万元以内，适当上浮利率至 {rate}%，并要求补充担保措施。"
        )
    return (
        f"该企业信用评分 {int(score)} 分，违约概率 {prob * 100:.1f}%，存在较高信贷风险。"
        f"建议暂缓放贷，或要求提供足额抵押物、引入第三方担保后酌情考虑小额授信。"
    )


# ---------------------------------------------------------------
# 兜底规则（对齐商业计划书 3.3.1：极端客户无论评分如何，强制高风险人工复核）
# ---------------------------------------------------------------
def _build_override_rules(thresholds: dict | None = None) -> list[dict]:
    t = thresholds or {}
    claim_count_th = int(t.get("overrideClaimCount", 2))
    insurance_low = float(t.get("overrideInsuranceLow", 2.0))  # 投保年限 < 此值
    black_soil_ratio = float(t.get("overrideBlackSoilRatio", 0.4))  # 黑土地保护占比 < 此值
    area_min = float(t.get("overrideAreaMin", 100.0))
    catastrophe_claims = int(t.get("overrideCatastropheClaims", 5))

    return [
        {
            "name": "连续两年绝收（高频理赔 + 投保年限不足）",
            "check": lambda i: (
                (i.get("claim_count") or 0) >= claim_count_th and (i.get("insurance_years") or 10) < insurance_low
            ),
        },
        {
            "name": "黑土地保护缺失（保护面积占比极低 + 经营面积大）",
            "check": lambda i: (
                (i.get("black_soil_protection") or 0) < (i.get("land_confirmed_area") or 0) * black_soil_ratio
                and (i.get("land_confirmed_area") or 0) >= area_min
            ),
        },
        {
            "name": "重大自然灾害（高频理赔 + 投保年限不足）",
            "check": lambda i: (
                (i.get("claim_count") or 0) >= catastrophe_claims and (i.get("insurance_years") or 10) < insurance_low
            ),
        },
    ]


def apply_overrides(input_data: dict, result: dict, thresholds: dict | None = None) -> dict:
    """极端场景兜底：触发任一规则即强制高风险并建议人工复核"""
    triggered = [r["name"] for r in _build_override_rules(thresholds) if r["check"](input_data)]
    if triggered:
        result["score"] = int(_clamp(result["score"], 0, 450))
        result["probability"] = round(max(result["probability"], 0.7), 4)
        result["level"] = "高风险"
        result["suggestedAmount"] = int(result["suggestedAmount"] * 0.4)
        result["overrides"] = triggered
        extra = "；".join(f"触发兜底规则：{t}" for t in triggered)
        result["advice"] = (
            f"【人工复核】{extra}。系统已将风险等级强制标记为高风险，"
            f"建议信贷员实地尽调并核实受灾/经营状况后复核授信。{result['advice']}"
        )
    else:
        result["overrides"] = []
    return result


def assess(
    input_data: dict,
    model: Scorecard | None = None,
    thresholds: dict | None = None,
) -> dict:
    """核心评估入口：返回 RiskResult 字典（对齐前端 types.ts）"""
    input_data = normalize_input(input_data)
    thresholds = thresholds or {}
    low_th = int(thresholds.get("lowRiskThreshold", 700))
    high_th = int(thresholds.get("highRiskThreshold", 500))
    base_rate = float(thresholds.get("baseRate", 3.5))
    premium_factor = float(thresholds.get("riskPremiumFactor", 6.0))

    if model is not None and model.coef is not None:
        result = _assess_with_model(input_data, model, low_th, high_th, base_rate, premium_factor)
    else:
        result = _assess_rule(input_data, low_th, high_th, base_rate, premium_factor)

    result["advice"] = _build_advice(
        result["score"], result["probability"], result["level"], result["suggestedAmount"], result["suggestedRate"]
    )
    # 兜底规则：极端场景强制高风险（无论模型评分）
    result = apply_overrides(input_data, result, thresholds)
    return result


# ---------------------------------------------------------------
def _assess_with_model(
    input_data: dict,
    model: Scorecard,
    low_th: int,
    high_th: int,
    base_rate: float,
    premium_factor: float,
) -> dict:
    prob = model.predict_proba(input_data)
    # 概率下限保护：信用极优客户 logit 极小可能浮点下溢为 0，业务上违约概率不应显示 0%
    prob = _clamp(prob, 1e-4, 1 - 1e-4)
    score_f = model.predict_score(input_data)
    score = int(round(score_f))
    score = int(_clamp(score, 0, 1000))

    level = "低风险" if score >= low_th else ("中等风险" if score >= high_th else "高风险")

    # 每指标贡献分（模型选中指标），未选中指标用规则子得分
    points = model.contribution_points(input_data)
    max_abs = max([abs(_f(v)) for v in points.values()] or [1.0]) or 1.0

    contributions = []
    for field in INDICATOR_ORDER:
        meta = INDICATOR_META[field]
        if field in points:
            disp = 50 + 50 * (_f(points[field]) / max_abs)
        else:
            disp = rule_sub_score(field, input_data.get(field))
        contributions.append(
            {
                "factor": meta["name"],
                "category": meta["category"],
                "weight": meta["weight"],
                "score": round(_clamp(_f(disp), 0, 100), 1),
            }
        )

    deductions = _top_deductions(contributions)

    annual_revenue = float(input_data.get("annual_revenue") or 0)
    suggested_amount, suggested_rate = _amount_and_rate(annual_revenue, score, level, base_rate, premium_factor)

    return {
        "score": score,
        "probability": round(prob, 4),
        "level": level,
        "suggestedAmount": suggested_amount,
        "suggestedRate": suggested_rate,
        "contributions": contributions,
        "deductions": deductions,
        "advice": "",
    }


# ---------------------------------------------------------------
def _assess_rule(
    input_data: dict,
    low_th: int,
    high_th: int,
    base_rate: float,
    premium_factor: float,
) -> dict:
    total, indicators = _rule_indicators(input_data)
    score = int(round(_clamp(total, 0, 1000)))

    logit_input = -(score - 550) / 150
    prob = round(_sigmoid(logit_input), 4)

    level = "低风险" if score >= low_th else ("中等风险" if score >= high_th else "高风险")

    contributions = [
        {"factor": i["factor"], "category": i["category"], "weight": i["weight"], "score": i["score"]}
        for i in indicators
    ]
    deductions = _top_deductions(contributions)

    annual_revenue = float(input_data.get("annual_revenue") or 0)
    suggested_amount, suggested_rate = _amount_and_rate(annual_revenue, score, level, base_rate, premium_factor)

    return {
        "score": score,
        "probability": prob,
        "level": level,
        "suggestedAmount": suggested_amount,
        "suggestedRate": suggested_rate,
        "contributions": contributions,
        "deductions": deductions,
        "advice": "",
    }


def _rule_indicators(input_data: dict) -> tuple[float, list[dict]]:
    indicators = []
    total = 0.0
    for field in INDICATOR_ORDER:
        meta = INDICATOR_META[field]
        s = rule_sub_score(field, input_data.get(field))
        total += meta["weight"] * s
        indicators.append({"factor": meta["name"], "category": meta["category"], "weight": meta["weight"], "score": s})
    return total * 10, indicators


def _top_deductions(contributions: list[dict]) -> list[dict]:
    sorted_items = sorted(contributions, key=lambda c: c["score"])
    return [
        {"factor": c["factor"], "score": c["score"], "reason": _deduction_reason(c["factor"], c["score"])}
        for c in sorted_items[:3]
    ]


def _amount_and_rate(
    annual_revenue: float, score: int, level: str, base_rate: float, premium_factor: float
) -> tuple[float, float]:
    base_amount = max(annual_revenue * 0.8, 5.0)
    discount = 1.0 if level == "低风险" else (0.7 if level == "中等风险" else 0.4)
    suggested_amount = round(base_amount * discount)
    risk_premium = (1 - score / 1000) * premium_factor
    suggested_rate = round(base_rate + risk_premium, 2)
    return suggested_amount, suggested_rate
