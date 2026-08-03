"""三组对比实验（对齐商业计划书 3.3.3 模型验证和性能对比）。

实验一：替代数据指标体系的有效性验证 —— 替代数据 vs 传统信用数据
实验二：特征工程方案对比 —— 原始变量 / WOE编码 / 分组PCA
实验三：涉农专属模型 vs 通用风控模型（通用模型仅用传统指标）

所有实验使用相同的分层训练/测试划分与 Logistic 基模型，保证可比性。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.ml.binning import WOEBinner
from app.ml.evaluate import evaluate_binary
from app.ml.indicators import CATEGORICAL_FIELDS, INDICATOR_ORDER

# 传统信用数据（产销经营类中偏财报/征信指标）与替代数据分组
TRADITIONAL_FIELDS = [
    "years_operating",
    "annual_revenue",
    "credit_record",
    "purchase_order",
]
ALTERNATIVE_FIELDS = [f for f in INDICATOR_ORDER if f not in TRADITIONAL_FIELDS]

# 业务类别分组（用于分组 PCA，四大维度全量）
CATEGORY_GROUPS = {
    "土地经营类": [
        "land_confirmed_area",
        "land_transfer_years",
        "land_transfer_stability",
        "black_soil_protection",
    ],
    "农业补贴类": [
        "grain_subsidy",
        "machinery_subsidy",
        "grain_scale_subsidy",
        "specialty_crop_subsidy",
    ],
    "农业保险类": ["insurance_years", "claim_count", "facility_insurance"],
    "产销经营类": ["years_operating", "purchase_order", "annual_revenue", "credit_record"],
}


def _train_eval(X, y, seed: int = 42) -> dict:
    """用统一的 70/30 分层划分训练 Logistic 并评估"""
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    lr = LogisticRegression(class_weight="balanced", max_iter=3000, random_state=seed)
    lr.fit(Xtr, ytr)
    prob = lr.predict_proba(Xte)[:, 1]
    m = evaluate_binary(yte, prob)
    return {
        "auc": m["auc"],
        "ks": m["ks"],
        "recall": m["recall"],
        "precision": m["precision"],
        "f1": m["f1"],
        "bestThreshold": m["bestThreshold"],
    }


def _woe_matrix(df: pd.DataFrame, fields: list[str], binners: dict) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    for f in fields:
        X[f] = df[f].apply(binners[f].transform)
    return X


def _raw_matrix(df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """原始值 + 分类序号编码（实验二方案A）"""
    X = pd.DataFrame(index=df.index)
    for f in fields:
        if f in CATEGORICAL_FIELDS:
            X[f] = df[f].astype("category").cat.codes.astype(float)
        else:
            X[f] = df[f].astype(float)
    return X


def _grouped_pca_matrix(df: pd.DataFrame, fields: list[str], seed: int = 42) -> pd.DataFrame:
    """分组 PCA：按业务类别对连续指标提取主成分（保留 ≥85% 方差），
    分类指标保留 WOE 编码值。作为共线性极端场景下的备选降维方案。"""
    continuous_in = [f for f in fields if f not in CATEGORICAL_FIELDS]
    X = pd.DataFrame(index=df.index)
    scaler = StandardScaler()
    for group_name, group_fields in CATEGORY_GROUPS.items():
        usable = [f for f in group_fields if f in continuous_in and f in fields]
        if not usable:
            continue
        values = df[usable].astype(float).values
        if values.shape[1] < 2:
            # 单指标组：标准化后直接使用
            X[f"PCA_{group_name}"] = scaler.fit_transform(values).ravel()
            continue
        pca = PCA(n_components=0.85, random_state=seed)
        comps = pca.fit_transform(values)
        for j in range(comps.shape[1]):
            X[f"PCA_{group_name}_{j + 1}"] = comps[:, j]
    # 分类字段用 WOE（需外部 binners，此处由调用方提供）
    return X


def run_experiments(df: pd.DataFrame, target: str = "default", seed: int = 42) -> dict:
    """运行三组对比实验，返回结构化结果（供训练指标与前端展示）"""
    y = df[target].astype(int).values
    total_bad = int(y.sum())

    # 全量 WOE 分箱
    binners: dict[str, WOEBinner] = {}
    for f in INDICATOR_ORDER:
        b = WOEBinner(f, is_categorical=f in CATEGORICAL_FIELDS)
        b.fit(df[f], df[target])
        binners[f] = b

    # ---------- 实验一：替代数据 vs 传统数据 ----------
    exp1 = {
        "name": "实验一：替代数据指标体系有效性验证",
        "desc": "同一批涉农样本上，对比仅用传统信用数据（户主特征/经营稳定性/征信近似）"
        "与加入六大类替代数据指标后的模型性能",
        "groups": {
            "传统信用数据": _train_eval(_woe_matrix(df, TRADITIONAL_FIELDS, binners).values, y, seed),
            "替代数据指标体系": _train_eval(_woe_matrix(df, ALTERNATIVE_FIELDS, binners).values, y, seed),
            "全量指标（传统+替代）": _train_eval(_woe_matrix(df, INDICATOR_ORDER, binners).values, y, seed),
        },
    }

    # ---------- 实验二：特征工程方案对比 ----------
    # 方案A：原始变量直接建模
    raw_all = _raw_matrix(df, INDICATOR_ORDER)
    scaler = StandardScaler()
    raw_scaled = scaler.fit_transform(raw_all.values)
    # 方案B：WOE 编码（本方案默认）
    woe_all = _woe_matrix(df, INDICATOR_ORDER, binners).values
    # 方案C：分组 PCA 降维 + 分类 WOE
    pca_parts = []
    for _, group_fields in CATEGORY_GROUPS.items():
        usable = [f for f in group_fields if f not in CATEGORICAL_FIELDS]
        if not usable:
            continue
        values = df[usable].astype(float).values
        if values.shape[1] < 2:
            pca_parts.append(StandardScaler().fit_transform(values))
        else:
            pca_parts.append(PCA(n_components=0.85, random_state=seed).fit_transform(values))
    cat_woe = _woe_matrix(df, [f for f in INDICATOR_ORDER if f in CATEGORICAL_FIELDS], binners).values
    pca_all = np.hstack(pca_parts + [cat_woe]) if pca_parts else cat_woe

    exp2 = {
        "name": "实验二：特征工程方案对比",
        "desc": "同一批涉农样本上，对比三种特征处理方案：原始变量直接建模 / WOE编码 / 分组PCA降维",
        "groups": {
            "原始变量（未分箱）": _train_eval(raw_scaled, y, seed),
            "WOE编码（本方案）": _train_eval(woe_all, y, seed),
            "分组PCA降维（备选）": _train_eval(pca_all, y, seed),
        },
    }

    # ---------- 实验三：涉农专属模型 vs 通用风控模型 ----------
    exp3 = {
        "name": "实验三：涉农专属模型 vs 通用风控模型",
        "desc": "通用风控模型仅使用传统信用指标（户主特征/财报/征信近似），"
        "涉农专属模型使用东北涉农场景六大类替代数据指标",
        "groups": {
            "通用风控模型（传统指标）": _train_eval(_woe_matrix(df, TRADITIONAL_FIELDS, binners).values, y, seed),
            "涉农专属模型（替代数据评分卡）": _train_eval(_woe_matrix(df, ALTERNATIVE_FIELDS, binners).values, y, seed),
        },
    }

    return {
        "experiment1": exp1,
        "experiment2": exp2,
        "experiment3": exp3,
        "nSamples": len(df),
        "defaultRate": round(total_bad / len(df), 4),
    }
