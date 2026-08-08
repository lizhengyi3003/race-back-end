"""导出融合模型注册元数据 + 生成注册 SQL。

1. 加载 scorecard pkl
2. 用融合样本全量向量化预测 → 训练群体评分分位（p5-p95）
3. 输出 data/models/model_meta_{version}.json + data/models/register_{version}.sql

用法：python scripts/fusion/export_model_meta.py --pkl data/models/scorecard_vXXX.pkl [--data data/samples/fused_samples_v1.csv]
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", default="data/models/scorecard_v20260809001246.pkl")
    ap.add_argument("--data", default="data/samples/fused_samples_v1.csv")
    args = ap.parse_args()

    pkl_path = ROOT / args.pkl
    data_path = ROOT / args.data
    with open(pkl_path, "rb") as f:
        sc = pickle.load(f)
    feats = sc.feature_names
    print(f"模型: {pkl_path.name}")
    print(f"入模特征({len(feats)}): {feats}")

    df = pd.read_csv(data_path)
    # 向量化 WOE → 评分（与 predict_score 一致，缺失自动入缺失箱）
    woe = pd.DataFrame(index=df.index)
    for f in feats:
        woe[f] = df[f].apply(sc.binners[f].transform)
    logit = sc.intercept + woe[feats].values @ sc.coef
    scores = np.clip(sc.A - sc.B * logit, 0, 1000)

    qs = {f"p{int(p*100)}": round(float(np.quantile(scores, p)), 1) for p in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)}
    print(f"评分样本: {len(scores)}  分位: {qs}")

    metrics = sc.metrics or {}
    meta = {
        "model_type": "data_layer",
        "features": feats,
        "scoreQuantiles": qs,
        "auc": metrics.get("auc"),
        "ks": metrics.get("ks"),
        "cvScores": metrics.get("cvScores"),
        "psi": metrics.get("psi"),
        "defaultRate": metrics.get("defaultRate"),
        "nSamples": metrics.get("nSamples"),
        "nFeatures": len(feats),
    }
    meta_path = ROOT / f"data/models/model_meta_{sc.version}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"元数据: {meta_path}")

    # 生成注册 SQL（ModelVersion 表，metrics_json 含 model_type/scoreQuantiles）
    js = json.dumps(meta, ensure_ascii=False).replace("'", "''")
    sql = (
        f"INSERT INTO model_version (version, status, n_samples, n_features, auc, ks, "
        f"metrics_json, artifact_path, trained_by, created_at) VALUES ("
        f"'{sc.version}', 'active', {len(scores)}, {len(feats)}, "
        f"{meta['auc'] if meta['auc'] is not None else 'NULL'}, "
        f"{meta['ks'] if meta['ks'] is not None else 'NULL'}, "
        f"'{js}', 'data/models/{pkl_path.name}', 'fused-pipeline', NOW());\n"
    )
    sql_path = ROOT / f"data/models/register_{sc.version}.sql"
    sql_path.write_text(sql, encoding="utf-8")
    print(f"注册SQL: {sql_path}")


if __name__ == "__main__":
    main()
