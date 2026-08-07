"""训练数据层评分卡：基于 CMES/CHFS 代理样本（build_proxy_dataset.py 输出）。

区别于专家层/15 项合成评分卡：
- 特征 = 指标编码（BASIC_008 年营业收入、01_05 土地经营总面积、0111_01 谷物播种面积等）
- 样本 = 真实调查数据映射的代理特征 + 可解释规则合成违约标签
- 默认仅 CMES（小微企业调查，最贴合涉农小微企业目标客群，AUC≈0.77）；--source all 用全样本
- 注册为 model_type=data_layer 的非激活版本（附加模型，不替换主评分卡）
用法：python scripts/train_data_layer.py [--source cmes|all] [--check]
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from app.core.config import settings
from app.db.session import SessionLocal
from app.ml import model_artifact
from app.ml.scorecard import Scorecard

PROXY_CSV = Path(__file__).resolve().parent.parent / "data" / "samples" / "proxy_samples.csv"

# 代理数据集中的数值指标特征（排除 source/default/_* 内部列）
FEATURE_PREFIXES = ("BASIC_", "0", "1")


def _feature_cols(df: pd.DataFrame) -> list[str]:
    return [
        c for c in df.columns
        if (c.startswith(FEATURE_PREFIXES)) and c != "default" and not c.startswith("_")
    ]


def run_training(db=None, use_smote: bool | None = None, version: str | None = None, source: str = "cmes") -> dict:
    if not PROXY_CSV.exists():
        raise FileNotFoundError(f"代理样本缺失：{PROXY_CSV}，请先运行 scripts/build_proxy_dataset.py")
    df = pd.read_csv(PROXY_CSV)
    if source == "cmes":
        df = df[df["source"] == "CMES"]
    elif source == "all":
        pass
    else:
        raise ValueError(f"未知 source：{source}（可选 cmes/all）")
    df = df.reset_index(drop=True)
    features = _feature_cols(df)
    print(f"代理样本 {len(df)} 条（source={source}），特征 {len(features)} 个：{features}")

    version = version or f"data_v{datetime.now():%Y%m%d%H%M%S}"
    scorecard = Scorecard(
        version=version,
        use_smote=settings.SMOTE_ENABLED if use_smote is None else use_smote,
        feature_cols=features,
        categorical_cols=[],  # 代理特征全为数值
        eval_threshold_mode="default_rate",  # 独立数据层模型按违约率分位评估
    )
    scorecard.fit(df, target_col="default")
    artifact_path = model_artifact.save_scorecard(scorecard)

    # 训练群体评分分位数（供运行时把新评分映射为风险分位，确定报警/确认阈值）
    try:
        score_series = []
        sample = df.sample(min(5000, len(df)), random_state=42)
        for _, row in sample.iterrows():
            inputs = {f: row[f] for f in scorecard.feature_names}
            score_series.append(scorecard.predict_score(inputs))
        import numpy as np

        qs = np.quantile(score_series, [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
        score_quantiles = {
            "p5": round(float(qs[0]), 1),
            "p10": round(float(qs[1]), 1),
            "p25": round(float(qs[2]), 1),
            "p50": round(float(qs[3]), 1),
            "p75": round(float(qs[4]), 1),
            "p90": round(float(qs[5]), 1),
            "p95": round(float(qs[6]), 1),
        }
    except Exception:  # noqa: BLE001
        score_quantiles = None

    metrics = dict(scorecard.metrics)
    metrics["model_type"] = "data_layer"
    metrics["source"] = f"CMES/CHFS proxy ({source})"
    metrics["features"] = features
    metrics["scoreQuantiles"] = score_quantiles

    result = {
        "version": version,
        "artifactPath": artifact_path,
        "nSamples": scorecard.n_samples,
        "nFeatures": len(scorecard.feature_names),
        "auc": metrics.get("auc"),
        "ks": metrics.get("ks"),
        "recall": metrics.get("recall"),
        "precision": metrics.get("precision"),
        "f1": metrics.get("f1"),
        "modelType": "data_layer",
        "featureNames": scorecard.feature_names,
        "ivTable": metrics.get("ivTable"),
    }

    if db is not None:
        from app.models.model_version import ModelVersion

        mv = ModelVersion(
            version=version,
            status="inactive",  # 附加数据层模型，不替换主评分卡
            n_samples=scorecard.n_samples,
            n_features=len(scorecard.feature_names),
            auc=metrics.get("auc"),
            ks=metrics.get("ks"),
            recall=metrics.get("recall"),
            precision=metrics.get("precision"),
            f1=metrics.get("f1"),
            metrics_json=metrics,
            artifact_path=artifact_path,
            trained_by="data-pipeline",
        )
        db.add(mv)
        db.commit()
    return result


if __name__ == "__main__":
    db = SessionLocal()
    try:
        src = "cmes"
        if "--source" in sys.argv:
            i = sys.argv.index("--source")
            if i + 1 < len(sys.argv):
                src = sys.argv[i + 1]
        res = run_training(db=db, source=src)
        print(f"✅ 数据层模型 {res['version']}（source={src}）")
        print(f"   AUC={res['auc']} KS={res['ks']} 召回={res['recall']} 精确率={res['precision']} F1={res['f1']}")
        print(f"   特征数={res['nFeatures']} 特征={res['featureNames']}")
        print(f"   IV 表：")
        for row in (res.get("ivTable") or [])[:12]:
            print(f"     {row['factor']:12s} IV={row['iv']:.4f} bins={row['nBins']}")
    finally:
        db.close()
