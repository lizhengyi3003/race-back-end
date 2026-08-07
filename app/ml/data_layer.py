"""数据层评分卡（混合引擎数据层）：加载 CMES/CHFS 代理训练的数据层模型，与专家层混合。

设计（训练群体分位校准）：
- 数据层模型注册为 ModelVersion（model_type=data_layer，inactive 附加模型）
- 当提交指标含数据层已知特征（BASIC_004 实际经营年限、BASIC_005 从业人员数等）≥2 项时，
  用数据层模型预测分并映射为训练群体风险分位（低分=高风险）：
  - 分位 ≤ 0.15（最差 15%）→ 独立高风险警报，较强下修（0.5 专家 + 0.5 数据）
  - 分位 ≥ 0.85（最优 15%）→ 确认低风险，轻度上修（0.9 专家 + 0.1 数据）
  - 中间带 → 无强判断，保持专家分权威（弱模型不稀释区分度）
- 全部 try/except 兜底：数据层不可用时静默降级为纯专家分
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.ml import model_artifact

logger = logging.getLogger(__name__)

# 至少需要多少个已知特征值才启用数据层混合
MIN_FEATURES = 2


def _latest_data_layer(db: Session) -> tuple[str | None, dict | None]:
    """取最新已注册的数据层模型：(产物路径, 训练群体评分分位数)。"""
    try:
        from app.models.model_version import ModelVersion

        rows = db.query(ModelVersion).order_by(ModelVersion.id.desc()).all()
        for r in rows:
            meta = r.metrics_json or {}
            if meta.get("model_type") == "data_layer" and r.artifact_path:
                return r.artifact_path, meta.get("scoreQuantiles")
    except Exception:  # noqa: BLE001
        logger.exception("查询数据层模型版本失败")
    return None, None


def data_layer_score(
    db: Session,
    indicators: dict[str, Any],
    expert_score: int,
) -> tuple[int | None, dict]:
    """计算数据层混合调整（训练群体分位校准）。

    返回 (blended_score, info)；数据层不可用/特征不足/无强信号时返回 (None, {})，调用方沿用专家分。
    """
    path, quantiles = _latest_data_layer(db)
    if not path:
        return None, {}
    model = model_artifact.load_scorecard(path)
    if model is None:
        return None, {}

    # 过滤出数据层已知且可数值化的特征
    inputs: dict[str, Any] = {}
    for f in model.feature_names:
        v = indicators.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        try:
            float(v)
            inputs[f] = v
        except (TypeError, ValueError):
            continue

    if len(inputs) < MIN_FEATURES:
        return None, {"features": sorted(inputs), "skip": "insufficient"}

    try:
        data_score = model.predict_score(inputs)  # 0-1000
    except Exception:  # noqa: BLE001
        logger.exception("数据层模型预测失败")
        return None, {}

    # 训练群体分位：把当前评分映射为风险分位，仅在极端分位触发调整
    if not quantiles:
        return None, {"features": sorted(inputs), "dataScore": round(data_score, 1), "skip": "no_quantiles"}

    pct = _percentile(quantiles, data_score)
    if pct <= 0.15:
        # 数据层判定为最差 15% 客群（低分=高风险）：独立高风险警报，较强下修
        blended = round(0.5 * expert_score + 0.5 * data_score)
        mode = "alarm_high_risk"
    elif pct >= 0.85:
        # 数据层判定为最优 15% 客群（高分=低风险）：确认低风险，轻度上修
        blended = round(0.9 * expert_score + 0.1 * data_score)
        mode = "confirm_low_risk"
    else:
        return None, {"features": sorted(inputs), "dataScore": round(data_score, 1), "percentile": round(pct, 3), "skip": "no_strong_signal"}

    info = {
        "features": sorted(inputs),
        "dataScore": round(data_score, 1),
        "expertScore": expert_score,
        "percentile": round(pct, 3),
        "mode": mode,
    }
    return blended, info


def _percentile(quantiles: dict, score: float) -> float:
    """用训练群体分位数把评分插值为 0-1 风险分位（越低风险越高）。"""
    keys = [("p5", 0.05), ("p10", 0.10), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p90", 0.90), ("p95", 0.95)]
    pts = [(float(quantiles[k]), p) for k, p in keys if k in quantiles]
    if not pts:
        return 0.5
    pts.sort()
    if score <= pts[0][0]:
        return 0.0
    if score >= pts[-1][0]:
        return 1.0
    for i in range(len(pts) - 1):
        x0, p0 = pts[i]
        x1, p1 = pts[i + 1]
        if x0 <= score <= x1:
            if x1 == x0:
                return p0
            return p0 + (score - x0) / (x1 - x0) * (p1 - p0)
    return 0.5
