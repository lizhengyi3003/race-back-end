"""训练编排：生成/加载样本 → 训练评分卡 → 评估 → 保存产物 → 注册模型版本。

供启动自动训练、管理平台“模型训练”接口、命令行脚本共用。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.ml import model_artifact
from app.ml.scorecard import Scorecard
from app.ml.seed import generate_samples


def _sample_path() -> Path:
    Path(settings.SAMPLE_DIR).mkdir(parents=True, exist_ok=True)
    return Path(settings.SAMPLE_DIR) / "synthetic_samples.csv"


def load_or_generate_samples(n_samples: int | None = None) -> pd.DataFrame:
    """优先读取已生成的样本 CSV，否则重新生成"""
    path = _sample_path()
    n = n_samples or settings.SEED_SAMPLES
    if path.exists() and n_samples is None:
        df = pd.read_csv(path)
        if len(df) >= 500:
            return df
    df = generate_samples(n=n, default_rate=settings.SEED_DEFAULT_RATE)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def run_training(
    n_samples: int | None = None,
    db=None,
    trained_by: str | None = None,
    version: str | None = None,
    use_smote: bool | None = None,
) -> dict:
    """执行一次完整训练，返回结果摘要"""
    df = load_or_generate_samples(n_samples)

    version = version or f"v{datetime.now():%Y%m%d%H%M%S}"
    scorecard = Scorecard(
        version=version,
        use_smote=settings.SMOTE_ENABLED if use_smote is None else use_smote,
    )
    scorecard.fit(df, target_col="default")

    # 保存模型文件
    artifact_path = model_artifact.save_scorecard(scorecard)

    # 三组对比实验（对齐计划书 3.3.3）
    try:
        from app.ml.experiments import run_experiments

        experiments = run_experiments(df, target="default")
        scorecard.metrics["experiments"] = experiments
    except Exception:
        scorecard.metrics["experiments"] = None

    # 汇总指标
    metrics = dict(scorecard.metrics)
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
        "accuracy": metrics.get("accuracy"),
        "defaultRate": metrics.get("defaultRate"),
        "psi": metrics.get("psi"),
        "cvScores": metrics.get("cvScores", []),
        "smoteApplied": metrics.get("smoteApplied", False),
        "featureNames": scorecard.feature_names,
        "trainedBy": trained_by,
        "metrics": metrics,
    }

    # 注册模型版本（若提供 db）
    if db is not None:
        from app.models.model_version import ModelVersion

        # 旧版本置为非激活
        db.query(ModelVersion).filter(ModelVersion.status == "active").update({"status": "inactive"})
        mv = ModelVersion(
            version=version,
            status="active",
            n_samples=scorecard.n_samples,
            n_features=len(scorecard.feature_names),
            auc=metrics.get("auc"),
            ks=metrics.get("ks"),
            recall=metrics.get("recall"),
            precision=metrics.get("precision"),
            f1=metrics.get("f1"),
            metrics_json=metrics,
            artifact_path=artifact_path,
            trained_by=trained_by,
        )
        db.add(mv)
        db.commit()

    return result


def load_active_model(db=None):
    """加载当前激活模型（优先 DB 中的 active 版本，其次最新模型文件）"""
    if db is not None:
        from app.models.model_version import ModelVersion

        mv = db.query(ModelVersion).filter(ModelVersion.status == "active").order_by(ModelVersion.id.desc()).first()
        if mv and mv.artifact_path:
            model = model_artifact.load_scorecard(mv.artifact_path)
            if model is not None:
                return model
    path = model_artifact.latest_artifact()
    if path:
        return model_artifact.load_scorecard(path)
    return None
