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


def _fused_samples_path() -> Path | None:
    """真实调查数据融合样本（CHFS + CMES + CFPS → fused_samples_v1.csv）"""
    p = Path(settings.SAMPLE_DIR) / "fused_samples_v1.csv"
    return p if p.exists() else None


def _fused_feature_cols(df: pd.DataFrame) -> list[str]:
    """融合样本入模特征：排除内部列（source/*_wave/_*）与标签，仅保留数值指标列。

    与 scripts/fusion/mappings.MODEL_FEATURES 对齐（按列是否存在过滤，缺失率<0.9）。
    """
    MODEL_FEATURES = [
        "BASIC_003", "BASIC_004", "BASIC_005", "BASIC_008", "BASIC_009", "BASIC_019",
        "01_05", "0111_01", "0111_05", "0111_08", "0112_04", "1041_02",
        "_cmes_had_loan", "_cmes_profit", "_cmes_credit", "_cmes_purchase_credit",
        "_chfs_agri", "_chfs_income",
        "_cfps_agri", "_cfps_livestock", "_cfps_hus_input", "_cfps_private_debt",
        "_cfps_income", "_cfps_assets",
        "_total_asset", "_hh_size",
    ]
    feats = []
    for c in MODEL_FEATURES:
        if c not in df.columns:
            continue
        if df[c].isna().mean() <= 0.9:
            feats.append(c)
    return feats


def run_fused_training(
    db=None,
    trained_by: str | None = None,
    version: str | None = None,
    use_smote: bool | None = None,
    default_rate: float = 0.05,
) -> dict | None:
    """真实调查数据融合训练（主路径）：读 fused_samples_v1.csv → 合成 A 标签 → 训练数据层评分卡。

    融合数据缺失时返回 None（由调用方回退合成样本）。
    """
    path = _fused_samples_path()
    if path is None:
        return None

    import numpy as np

    df = pd.read_csv(path)
    feats = _fused_feature_cols(df)
    if len(feats) < 2:
        return None

    # A 主标签：可解释风险因子加权 → sigmoid 校准违约率（与 scripts/fusion/train_fused_model 一致）
    def _std(x: pd.Series) -> pd.Series:
        s = x.astype(float)
        return (s - s.mean()) / (s.std() + 1e-9)

    rng = np.random.default_rng(42)
    z = _std(df["BASIC_008"].fillna(df["BASIC_008"].median())) * 0.40
    if "BASIC_003" in df and df["BASIC_003"].notna().mean() > 0.1:
        z = z + _std(df["BASIC_003"].fillna(df["BASIC_003"].median())) * 0.28
    if "BASIC_005" in df and df["BASIC_005"].notna().mean() > 0.1:
        z = z + _std(df["BASIC_005"].fillna(df["BASIC_005"].median())) * 0.16
    if "01_05" in df and df["01_05"].notna().mean() > 0.1:
        z = z + _std(df["01_05"].fillna(df["01_05"].median())) * 0.20
    if "BASIC_019" in df and df["BASIC_019"].notna().mean() > 0.1:
        z = z - _std(df["BASIC_019"].fillna(0)) * 0.45
    if "BASIC_009" in df and df["BASIC_009"].notna().mean() > 0.1:
        z = z - _std(df["BASIC_009"].fillna(df["BASIC_009"].median())) * 0.45
    neg = pd.Series(0.0, index=df.index)
    for c in ("_cmes_credit", "_cmes_purchase_credit", "_cfps_private_debt"):
        if c in df and df[c].notna().mean() > 0.1:
            neg = neg + df[c].fillna(0)
    if neg.abs().sum() > 0:
        z = z - _std(neg) * 0.30
    z = z + rng.standard_normal(len(df)) * 0.04

    z_std = (z - z.mean()) / max(z.std(), 1e-9)
    alpha = 2.8
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p = 1.0 / (1.0 + np.exp(alpha * z_std + mid))
        if p.mean() > default_rate:
            lo = mid
        else:
            hi = mid
    beta = (lo + hi) / 2
    df["default"] = (rng.random(len(df)) < (1.0 / (1.0 + np.exp(alpha * z_std + beta)))).astype(int)

    version = version or f"v{datetime.now():%Y%m%d%H%M%S}"
    scorecard = Scorecard(
        version=version,
        use_smote=settings.SMOTE_ENABLED if use_smote is None else use_smote,
        feature_cols=feats,
        categorical_cols=[],
        eval_threshold_mode="default_rate",
    )
    scorecard.fit(df[feats + ["default"]], target_col="default")

    artifact_path = model_artifact.save_scorecard(scorecard)
    metrics = dict(scorecard.metrics)
    metrics["model_type"] = "data_layer"
    metrics["trainSource"] = "fused_real_survey"
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
        "trainSource": "fused_real_survey",
        "metrics": metrics,
    }

    if db is not None:
        from app.models.model_version import ModelVersion

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
