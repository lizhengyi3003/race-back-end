"""Phase 5b: 模型选型对比 —— Logistic 评分卡 vs LightGBM（同数据、同标签、同验证）。

对比项：
- 5 折交叉验证 AUC / KS
- B 验证（真实 predict_proba + 独立信号 ft8 借款被拒，防泄漏）
- 特征重要性（LightGBM）

用法：python scripts/fusion/compare_models.py [--version v1]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from train_fused_model import real_risk_signal, select_features, synth_label  # noqa: E402
from app.ml.scorecard import Scorecard  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


def ks_metric(y, proba) -> float:
    from sklearn.metrics import roc_curve

    fpr, tpr, _ = roc_curve(y, proba)
    return float(np.max(tpr - fpr))


def cv_auc(y, X, model_fn) -> tuple[float, float, float]:
    """5 折 CV：返回 (AUC 均值, AUC 标准差, KS 均值)。"""
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    aucs, kss = [], []
    for tr, te in skf.split(X, y):
        m = model_fn()
        m.fit(X.iloc[tr], y.iloc[tr])
        p = m.predict_proba(X.iloc[te])[:, 1]
        aucs.append(float(__import__("sklearn.metrics", fromlist=["roc_auc_score"]).roc_auc_score(y.iloc[te], p)))
        kss.append(ks_metric(y.iloc[te], p))
    return float(np.mean(aucs)), float(np.std(aucs)), float(np.mean(kss))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1")
    ap.add_argument("--subset", default="all", help="all | cmes | hh(chfs+cfps)")
    args = ap.parse_args()

    df = pd.read_csv(ROOT / "data" / "samples" / f"fused_samples_{args.version}.csv")
    if args.subset == "cmes":
        df = df[df["source"] == "CMES"].reset_index(drop=True)
    elif args.subset == "hh":
        df = df[df["source"].isin(["CHFS", "CFPS"])].reset_index(drop=True)
    print(f"子集: {args.subset}, 样本 {len(df)} 行")

    feats = select_features(df)
    print(f"入模特征({len(feats)}): {feats}")
    df["default"] = synth_label(df)
    print(f"A 标签违约率: {df['default'].mean():.4f}")

    X = df[feats].copy()
    y = df["default"]
    # 缺失用中位数填充（LightGBM 也可原生处理缺失，填充后两模型一致可比）
    X_fill = X.fillna(X.median())

    # ---------- 1) Logistic 评分卡 ----------
    print("\n=== Logistic 评分卡 ===")
    sc = Scorecard(version=f"cmp{time.strftime('%H%M%S')}", use_smote=True, feature_cols=feats, categorical_cols=[], eval_threshold_mode="default_rate")
    sc.fit(df[feats + ["default"]], target_col="default")
    print(f"入选特征: {sc.feature_names}")
    print(f"5折CV AUC: {np.mean(sc.metrics['cvScores']):.4f} ± {np.std(sc.metrics['cvScores']):.4f}  KS: {sc.metrics.get('ks', 0):.4f}")

    # ---------- 2) LightGBM ----------
    print("\n=== LightGBM ===")
    import lightgbm as lgb

    def _lgb_model():
        return lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31, max_depth=6,
            subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
            class_weight="balanced", random_state=42, verbose=-1,
        )

    lgb_auc, lgb_std, lgb_ks = cv_auc(y, X_fill, _lgb_model)
    print(f"5折CV AUC: {lgb_auc:.4f} ± {lgb_std:.4f}  KS: {lgb_ks:.4f}")

    lgb_final = _lgb_model()
    lgb_final.fit(X_fill, y)
    lgb_proba = lgb_final.predict_proba(X_fill)[:, 1]
    print(f"全量 AUC: {float(__import__('sklearn.metrics', fromlist=['roc_auc_score']).roc_auc_score(y, lgb_proba)):.4f}")

    # ---------- 3) B 验证（防泄漏）----------
    sig = real_risk_signal(df, exclude=set(sc.feature_names))
    valid = sig.notna()
    print(f"\n=== B 验证（n={int(valid.sum())}）===")
    if valid.sum() > 50:
        # 评分卡：WOE → logit → proba
        fnames = sc.feature_names
        woe = pd.DataFrame(index=df.index)
        for f in fnames:
            woe[f] = df[f].apply(sc.binners[f].transform)
        sc_logit = sc.intercept + woe[fnames].values @ sc.coef
        sc_proba = 1.0 / (1.0 + np.exp(-sc_logit))
        rho_sc, p_sc = sp_stats.spearmanr(sc_proba[valid], sig[valid])
        rho_lgb, p_lgb = sp_stats.spearmanr(lgb_proba[valid], sig[valid])
        print(f"评分卡: Spearman={rho_sc:.3f} (p={p_sc:.2e})")
        print(f"LightGBM: Spearman={rho_lgb:.3f} (p={p_lgb:.2e})")

    # ---------- 4) 特征重要性 ----------
    imp = sorted(zip(feats, lgb_final.feature_importances_), key=lambda x: -x[1])
    print("\n=== LightGBM 特征重要性 TOP10 ===")
    for f, v in imp[:10]:
        print(f"  {f}: {v}")

    print("\n=== 对比结论 ===")
    print(f"评分卡 5折CV AUC: {np.mean(sc.metrics['cvScores']):.4f}±{np.std(sc.metrics['cvScores']):.4f}")
    print(f"LightGBM 5折CV AUC: {lgb_auc:.4f}±{lgb_std:.4f}")


if __name__ == "__main__":
    main()
