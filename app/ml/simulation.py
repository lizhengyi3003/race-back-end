"""业务仿真验证：极端场景模拟（对齐商业计划书 3.3.3 业务仿真验证模块）。

模拟干旱减产、粮食价格下跌、补贴退坡等极端场景，对样本施加业务冲击后
重新评分，观察评分分布、风险等级迁移与错判率变化，验证模型在非正常
年份下的可靠性，同时为兜底规则提供依据。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.indicators import INDICATOR_ORDER
from app.ml.predictor import assess
from app.ml.scorecard import Scorecard

# 收购订单档位降级映射（产销经营冲击）
_PURCHASE_DOWN = {
    "年度订单": "零散收购",
    "零散收购": "无稳定渠道",
    "无稳定渠道": "无稳定渠道",
}

_SCENARIO_DEFS: dict[str, dict] = {
    "干旱减产": {
        "desc": "模拟严重干旱导致大面积减产：理赔频次上升、营收下滑、收购订单降级",
        "icon": "Sunny",
        "color": "#e76f51",
    },
    "粮价下跌": {
        "desc": "模拟粮食价格大幅下跌：年营收下降约 30%、收购订单降级",
        "icon": "TrendCharts",
        "color": "#e6a23c",
    },
    "补贴退坡": {
        "desc": "模拟农业补贴政策退坡：地力/农机/规模/特色四类补贴均下降，收入承压",
        "icon": "Money",
        "color": "#9b5de5",
    },
    "突发灾情": {
        "desc": "模拟重大自然灾害：理赔频次激增、投保中断、营收大幅下滑",
        "icon": "Warning",
        "color": "#f56c6c",
    },
}


def apply_scenario(inputs: dict, scenario: str) -> dict:
    """对单个样本（snake_case 字段）施加场景冲击"""
    out = dict(inputs)
    if scenario == "干旱减产":
        out["claim_count"] = min((out.get("claim_count") or 0) + 3, 8)
        out["annual_revenue"] = round((out.get("annual_revenue") or 0) * 0.7, 1)
        out["purchase_order"] = _PURCHASE_DOWN.get(out.get("purchase_order") or "零散收购", "无稳定渠道")
    elif scenario == "粮价下跌":
        out["annual_revenue"] = round((out.get("annual_revenue") or 0) * 0.7, 1)
        out["purchase_order"] = _PURCHASE_DOWN.get(out.get("purchase_order") or "零散收购", "无稳定渠道")
    elif scenario == "补贴退坡":
        # 补贴是收入底线：四类补贴退坡后收入下滑（业务联动冲击）
        out["grain_subsidy"] = round((out.get("grain_subsidy") or 0) * 0.3)
        out["machinery_subsidy"] = round((out.get("machinery_subsidy") or 0) * 0.2)
        out["grain_scale_subsidy"] = round((out.get("grain_scale_subsidy") or 0) * 0.3)
        out["specialty_crop_subsidy"] = round((out.get("specialty_crop_subsidy") or 0) * 0.3)
        out["annual_revenue"] = round((out.get("annual_revenue") or 0) * 0.85, 1)
    elif scenario == "突发灾情":
        out["claim_count"] = min((out.get("claim_count") or 0) + 4, 10)
        out["annual_revenue"] = round((out.get("annual_revenue") or 0) * 0.5, 1)
        out["insurance_years"] = 0
        out["purchase_order"] = "无稳定渠道"
    return out


def _level(score: int, low_th: int, high_th: int) -> str:
    if score >= low_th:
        return "低风险"
    if score >= high_th:
        return "中等风险"
    return "高风险"


def simulate(
    model: Scorecard,
    samples: pd.DataFrame,
    scenarios: list[str] | None = None,
    thresholds: dict | None = None,
    n_samples: int | None = None,
) -> dict:
    """对样本批量施加各场景冲击，返回基线 vs 各场景的评分/等级对比统计"""
    thresholds = thresholds or {}
    low_th = int(thresholds.get("lowRiskThreshold", 700))
    high_th = int(thresholds.get("highRiskThreshold", 500))

    df = samples.head(n_samples) if n_samples else samples
    scenario_names = scenarios or list(_SCENARIO_DEFS.keys())

    def _row_to_input(row: pd.Series) -> dict:
        return {f: row[f] for f in INDICATOR_ORDER}

    base_scores = []
    base_levels = []
    for _, row in df.iterrows():
        r = assess(_row_to_input(row), model=model, thresholds=thresholds)
        base_scores.append(r["score"])
        base_levels.append(r["level"])
    base_scores = np.array(base_scores, dtype=float)

    def _summarize(scores: list[float], levels: list[str]) -> dict:
        arr = np.array(scores, dtype=float)
        low = sum(1 for lv in levels if lv == "低风险")
        mid = sum(1 for lv in levels if lv == "中等风险")
        high = sum(1 for lv in levels if lv == "高风险")
        n = len(arr) or 1
        return {
            "avgScore": round(float(arr.mean()) if len(arr) else 0, 1),
            "highRiskRate": round(high / n * 100, 1),
            "lowRate": round(low / n * 100, 1),
            "midRate": round(mid / n * 100, 1),
        }

    base_summary = _summarize(base_scores, base_levels)
    results = []
    for sc in scenario_names:
        scores, levels = [], []
        for _, row in df.iterrows():
            r = assess(apply_scenario(_row_to_input(row), sc), model=model, thresholds=thresholds)
            scores.append(r["score"])
            levels.append(r["level"])
        summary = _summarize(scores, levels)
        # 等级迁移统计
        migrate_up = sum(1 for a, b in zip(base_levels, levels, strict=False) if _risk_rank(b) > _risk_rank(a))
        migrate_down = sum(1 for a, b in zip(base_levels, levels, strict=False) if _risk_rank(b) < _risk_rank(a))
        results.append(
            {
                "name": sc,
                **(_SCENARIO_DEFS.get(sc) or {}),
                "baseline": base_summary,
                "after": summary,
                "avgScoreDelta": round(summary["avgScore"] - base_summary["avgScore"], 1),
                "highRiskDelta": round(summary["highRiskRate"] - base_summary["highRiskRate"], 1),
                "migrateToHigh": migrate_up,
                "migrateToLow": migrate_down,
                "nSamples": len(scores),
            }
        )

    return {
        "scenarios": results,
        "nSamples": len(df),
        "thresholds": {"lowRiskThreshold": low_th, "highRiskThreshold": high_th},
    }


def _risk_rank(level: str) -> int:
    return {"低风险": 1, "中等风险": 2, "高风险": 3}.get(level, 2)


def scenario_defs() -> dict:
    return _SCENARIO_DEFS
