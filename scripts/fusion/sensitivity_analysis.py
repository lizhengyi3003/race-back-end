"""Phase 5c: 数据层混合参数敏感性分析。

模拟生产场景（仅 BASIC_009/BASIC_019/01_05 三特征可用），扫描：
- 极端分位阈值（低 0.10-0.25 / 高 0.80-0.90）
- 下修权重（0.4-0.6）
观察：下修/上修触发率、平均调整幅度、对整体评分的平均影响。

用法：python scripts/fusion/sensitivity_analysis.py --pkl data/models/scorecard_vXXX.pkl
"""

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

PROD_FEATURES = ["BASIC_009", "BASIC_019", "01_05"]  # 生产可用的数据层特征


def _percentile(quantiles: dict, score: float) -> float:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", default="data/models/scorecard_v20260809013727.pkl")
    ap.add_argument("--data", default="data/samples/fused_samples_v1.csv")
    args = ap.parse_args()

    with open(ROOT / args.pkl, "rb") as f:
        sc = pickle.load(f)
    df = pd.read_csv(ROOT / args.data)
    print(f"模型: {args.pkl}  样本: {len(df)}")

    # 生产打分：仅 3 特征有真实值，其余特征生产永不出现 → 全部走缺失箱（transform(NaN)）
    woe = pd.DataFrame(index=df.index)
    for feat in sc.feature_names:
        if feat in PROD_FEATURES:
            vals = df[feat]
        else:
            vals = pd.Series(np.nan, index=df.index)
        woe[feat] = vals.apply(sc.binners[feat].transform)
    logit = sc.intercept + woe[sc.feature_names].values @ sc.coef
    scores = np.clip(sc.A - sc.B * logit, 0, 1000)

    # 训练群体分位：优先读注册 meta（scoreQuantiles），否则按当前分数重算
    meta_path = ROOT / f"data/models/model_meta_{sc.version}.json"
    quantiles = {}
    if meta_path.exists():
        import json

        quantiles = json.loads(meta_path.read_text(encoding="utf-8")).get("scoreQuantiles") or {}
    if not quantiles:
        qs = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
        quantiles = {f"p{int(q*100)}": float(np.quantile(scores, q)) for q in qs}
    print(f"scoreQuantiles: {quantiles}")

    pcts = np.array([_percentile(quantiles, s) for s in scores])
    print(f"生产打分范围: {scores.min():.1f}-{scores.max():.1f}  分位均值: {pcts.mean():.3f}")

    # 模拟专家分（用生产分 0.7-1.0 缩放模拟中等专家分，观察调整方向）
    expert = np.clip(scores * 0.8 + 150, 0, 1000)

    print("\n=== 分位阈值敏感性（权重 0.5/0.5）===")
    print(f"{'低阈值':<6}{'高阈值':<6}{'下修触发':<10}{'上修触发':<10}{'下修均幅':<10}{'上修均幅':<10}")
    for low, high in [(0.10, 0.90), (0.15, 0.85), (0.20, 0.80), (0.25, 0.75)]:
        dn = (pcts <= low).mean()
        up = (pcts >= high).mean()
        dn_amp = np.mean(expert[pcts <= low] - (0.5 * expert[pcts <= low] + 0.5 * scores[pcts <= low])) if dn > 0 else 0
        up_amp = np.mean((0.9 * expert[pcts >= high] + 0.1 * scores[pcts >= high]) - expert[pcts >= high]) if up > 0 else 0
        print(f"{low:<6.2f}{high:<6.2f}{dn*100:<9.1f}%{up*100:<9.1f}%{dn_amp:<10.1f}{up_amp:<10.1f}")

    print("\n=== 下修权重敏感性（阈值 0.15/0.85）===")
    dn_mask = pcts <= 0.15
    print(f"{'下修权重':<8}{'混合后均分':<12}{'vs 专家分':<12}")
    for w in [0.3, 0.4, 0.5, 0.6, 0.7]:
        blended = (1 - w) * expert[dn_mask] + w * scores[dn_mask]
        print(f"{w:<8.1f}{np.mean(blended):<12.1f}{np.mean(blended - expert[dn_mask]):<+12.1f}")

    print(f"\n生产触发率（当前 0.15/0.85）: 下修 {(pcts<=0.15).mean()*100:.1f}%  上修 {(pcts>=0.85).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
