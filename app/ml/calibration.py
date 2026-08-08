"""专家引擎违约概率校准：用真实回填数据（outcome）Platt 校准 score→P(overdue)。

- 回填样本（outcome ∈ normal/overdue）足够时，用 Logistic 回归拟合 分数→逾期概率
- 数据不足/拟合失败返回 None，调用方回退默认 sigmoid((score-550)/80) 逻辑映射
- 模块级缓存（TTL 5 分钟），避免每次评估都重查数据库
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 50      # 最少回填样本数
_MIN_POS = 5           # 最少逾期样本数
_CACHE_TTL = 300       # 缓存秒数

_cache: dict = {"ts": 0.0, "model": None, "n": 0, "bad": 0}


def calibrated_probability(db, score: float) -> float | None:
    """返回校准后的违约概率；数据不足或失败返回 None（回退默认映射）。"""
    now = time.time()
    if now - _cache.get("ts", 0.0) > _CACHE_TTL or _cache.get("n", 0) == 0:
        _refresh(db)
    m = _cache.get("model")
    if m is None:
        return None
    import numpy as np

    p = float(m.predict_proba(np.array([[score]]))[0][1])
    return min(max(p, 0.001), 0.999)


def _refresh(db) -> None:
    from app.models.assessment import AssessmentRecord

    try:
        rows = db.query(AssessmentRecord).all()
    except Exception:  # noqa: BLE001
        logger.exception("读取回填样本失败")
        _cache.update(ts=time.time(), model=None, n=0, bad=0)
        return
    xs, ys = [], []
    for r in rows:
        oc = r.outcome or "pending"
        if oc == "overdue":
            xs.append(r.score)
            ys.append(1)
        elif oc == "normal":
            xs.append(r.score)
            ys.append(0)
    n = len(xs)
    bad = sum(ys)
    if n < _MIN_SAMPLES or bad < _MIN_POS or (n - bad) < _MIN_POS:
        _cache.update(ts=time.time(), model=None, n=n, bad=bad)
        return
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression

        X = np.array(xs, dtype=float).reshape(-1, 1)
        m = LogisticRegression(max_iter=300).fit(X, np.array(ys, dtype=int))
        _cache.update(ts=time.time(), model=m, n=n, bad=bad)
        logger.info("概率校准已启用 n=%d 逾期=%d", n, bad)
    except Exception:  # noqa: BLE001
        logger.exception("概率校准拟合失败")
        _cache.update(ts=time.time(), model=None, n=n, bad=bad)
