"""模型评估：AUC / KS / 混淆矩阵 / 精确率召回率 F1 / 5折CV / PSI / ROC-KS 曲线数据"""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def _finite_threshold(t) -> float:
    """roc_curve 首阈值恒为 np.inf（表示不设阈值），JSON 序列化会变 null；
    概率范围 [0,1]，统一替换为非无穷有限值，避免前端展示异常。"""
    v = float(t)
    if not math.isfinite(v):
        return 1.0
    return v


def evaluate_binary(y_true, y_prob, threshold: float | None = None) -> dict:
    """二分类评估，返回指标 + ROC/KS 曲线数据

    threshold: 业务判定阈值（违约概率）。传入时按该阈值计算混淆矩阵/精确率/召回率；
               不传则用 bestThreshold（TPR-FPR 最大化）。信用评分场景建议传评分卡业务阈值
               （如评分<500 高风险对应概率），否则严重类不平衡下 bestThreshold 会过低、
               导致精确率失真。
    """
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)

    auc = float(roc_auc_score(y_true, y_prob))
    fpr, tpr, th = roc_curve(y_true, y_prob)

    diff = tpr - fpr
    ks = float(diff.max())
    best_idx = int(np.argmax(diff))
    best_th = _finite_threshold(th[best_idx])

    th_used = float(threshold) if threshold is not None else best_th
    pred = (y_prob >= th_used).astype(int)
    cm = confusion_matrix(y_true, pred).tolist()

    return {
        "auc": round(auc, 6),
        "ks": round(ks, 6),
        "bestThreshold": round(best_th, 6),
        "threshold": round(th_used, 6),
        "accuracy": round(float(accuracy_score(y_true, pred)), 6),
        "precision": round(float(precision_score(y_true, pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_true, pred, zero_division=0)), 6),
        "confusionMatrix": cm,
        "rocCurve": [{"fpr": round(float(a), 6), "tpr": round(float(b), 6)} for a, b in zip(fpr, tpr, strict=False)],
        "ksCurve": [
            {
                "threshold": round(_finite_threshold(t), 6),
                "tpr": round(float(a), 6),
                "fpr": round(float(b), 6),
                "diff": round(float(a - b), 6),
            }
            for t, a, b in zip(th, tpr, fpr, strict=False)
        ],
    }


def compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """群体稳定性指数 PSI"""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        return 0.0
    edges = np.quantile(expected, np.linspace(0, 1, bins + 1))
    edges[0] = -np.inf
    edges[-1] = np.inf
    exp_hist = np.histogram(expected, edges)[0]
    act_hist = np.histogram(actual, edges)[0]
    exp_ratio = exp_hist / max(len(expected), 1)
    act_ratio = act_hist / max(len(actual), 1)
    psi = 0.0
    for e, a in zip(exp_ratio, act_ratio, strict=False):
        if e > 0 and a > 0:
            psi += (a - e) * np.log(a / e)
        elif a > 0:
            psi += a * np.log(a / 1e-6)
    return float(psi)
