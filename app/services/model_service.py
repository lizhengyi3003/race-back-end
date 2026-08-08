"""模型管理服务：阈值 / 模型信息 / 训练 / 监控 / 仿真"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.training import load_active_model, run_training
from app.models.model_version import ModelVersion
from app.models.sys_config import SystemConfig

DEFAULT_THRESHOLDS = {
    "lowRiskThreshold": settings.LOW_RISK_THRESHOLD,
    "highRiskThreshold": settings.HIGH_RISK_THRESHOLD,
    "baseRate": settings.BASE_RATE,
    "riskPremiumFactor": settings.RISK_PREMIUM_FACTOR,
}


def get_thresholds(db: Session) -> dict:
    result = dict(DEFAULT_THRESHOLDS)
    rows = (
        db.query(SystemConfig)
        .filter(
            SystemConfig.config_key.in_(
                ["low_risk_threshold", "high_risk_threshold", "base_rate", "risk_premium_factor"]
            )
        )
        .all()
    )
    mapping = {
        "low_risk_threshold": "lowRiskThreshold",
        "high_risk_threshold": "highRiskThreshold",
        "base_rate": "baseRate",
        "risk_premium_factor": "riskPremiumFactor",
    }
    for row in rows:
        key = mapping.get(row.config_key)
        if key:
            try:
                result[key] = (
                    float(row.config_value)
                    if key not in ("lowRiskThreshold", "highRiskThreshold")
                    else int(float(row.config_value))
                )
            except (TypeError, ValueError):
                pass
    return result


def save_thresholds(db: Session, thresholds: dict) -> dict:
    mapping = {
        "lowRiskThreshold": "low_risk_threshold",
        "highRiskThreshold": "high_risk_threshold",
        "baseRate": "base_rate",
        "riskPremiumFactor": "risk_premium_factor",
    }
    from datetime import datetime

    for key, value in thresholds.items():
        config_key = mapping.get(key)
        if not config_key:
            continue
        row = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
        if row:
            row.config_value = str(value)
            row.updated_at = datetime.now()
        else:
            db.add(
                SystemConfig(config_key=config_key, config_value=str(value), description=key, updated_at=datetime.now())
            )
    db.commit()
    return get_thresholds(db)


def get_active_model_info(db: Session) -> dict:
    mv = db.query(ModelVersion).filter(ModelVersion.status == "active").order_by(ModelVersion.id.desc()).first()
    if not mv:
        return {
            "version": None,
            "status": "none",
            "trainedAt": None,
            "nSamples": 0,
            "nFeatures": 0,
            "auc": None,
            "ks": None,
            "recall": None,
            "precision": None,
            "f1": None,
        }
    return {
        "version": mv.version,
        "status": mv.status,
        "trainedAt": mv.created_at,
        "nSamples": mv.n_samples,
        "nFeatures": mv.n_features,
        "auc": mv.auc,
        "ks": mv.ks,
        "recall": mv.recall,
        "precision": mv.precision,
        "f1": mv.f1,
    }


def get_metrics(db: Session) -> dict | None:
    mv = db.query(ModelVersion).filter(ModelVersion.status == "active").order_by(ModelVersion.id.desc()).first()
    if not mv or not mv.metrics_json:
        return None
    return mv.metrics_json


def train(db: Session, n_samples: int | None, trained_by: str | None) -> dict:
    result = run_training(n_samples=n_samples, db=db, trained_by=trained_by)
    return result


# ---------------------------------------------------------------
# 模型监控（对齐计划书 3.3.1：PSI 群体稳定性监控 + 客群迁移预警）
# ---------------------------------------------------------------
def get_monitor(db: Session, n_samples: int = 200) -> dict:
    """返回当前模型的持续监控指标：
    - 模型训练评分分布 vs 实际评估记录评分分布 的 PSI
    - 近期（近 30 天）实际客群的平均分 / 高风险率趋势
    - 监控预警状态（PSI>0.1 或 高风险率显著上升时预警）
    """
    from datetime import datetime, timedelta

    import numpy as np

    from app.ml.evaluate import compute_psi
    from app.models.assessment import AssessmentRecord

    model = load_active_model(db)
    if model is None:
        return {"available": False, "message": "尚未训练模型"}

    low_th = int(get_thresholds(db).get("lowRiskThreshold", 700))
    high_th = int(get_thresholds(db).get("highRiskThreshold", 500))

    # 实际客群评分（最新 n 条评估记录）
    records = db.query(AssessmentRecord).order_by(AssessmentRecord.id.desc()).limit(n_samples).all()
    actual_scores = [r.score for r in records]

    # 训练集评分分布（从模型文件重算一份代表性样本）
    try:
        from app.ml.seed import generate_samples

        sample_df = generate_samples(n=2000, default_rate=0.04, seed=42)
        train_scores = []
        for _, row in sample_df.iterrows():
            r = model.predict_score({c: row[c] for c in sample_df.columns if c != "default"})
            train_scores.append(r)
    except Exception:
        train_scores = []

    psi = None
    if train_scores and actual_scores:
        try:
            psi = round(compute_psi(np.array(train_scores), np.array(actual_scores)), 6)
        except Exception:
            psi = None

    # 近期趋势（近 30 天按天）
    start = datetime.now() - timedelta(days=29)
    recent = (
        db.query(
            func.date(AssessmentRecord.created_at).label("d"),
            func.count(AssessmentRecord.id),
            func.avg(AssessmentRecord.score),
        )
        .filter(AssessmentRecord.created_at >= start)
        .group_by(func.date(AssessmentRecord.created_at))
        .all()
    )
    trend = [{"date": str(d), "count": c, "avgScore": round(float(s or 0), 1)} for d, c, s in recent]

    # 预警判定（样本量过少时暂不触发，提示数据积累中）
    recent_avg = float(np.mean(actual_scores)) if actual_scores else None
    warnings = []
    if len(actual_scores) < 30:
        warnings.append(f"实际评估记录仅 {len(actual_scores)} 条，样本量不足以评估客群偏移，建议持续积累数据后监控")
    else:
        if psi is not None and psi > 0.1:
            warnings.append(f"PSI={psi} > 0.1，客群分布发生显著偏移，建议启动模型再校准")
        if recent_avg is not None and recent_avg < high_th:
            warnings.append(f"近期实际客群平均分 {recent_avg:.0f} 低于高风险阈值 {high_th}，客群风险偏高")

    return {
        "available": True,
        "modelVersion": model.version,
        "psi": psi,
        "psiWarning": (psi is not None and psi > 0.1),
        "actualSamples": len(actual_scores),
        "actualAvgScore": round(recent_avg, 1) if recent_avg is not None else None,
        "highRiskRate": round(sum(1 for s in actual_scores if s < high_th) / max(len(actual_scores), 1) * 100, 1),
        "trend": trend,
        "warnings": warnings,
        "thresholds": {"lowRiskThreshold": low_th, "highRiskThreshold": high_th},
    }


def list_versions(db: Session) -> list[dict]:
    rows = db.query(ModelVersion).order_by(ModelVersion.id.desc()).limit(50).all()
    return [
        {
            "id": v.id,
            "version": v.version,
            "status": v.status,
            "nSamples": v.n_samples,
            "nFeatures": v.n_features,
            "auc": v.auc,
            "ks": v.ks,
            "recall": v.recall,
            "precision": v.precision,
            "f1": v.f1,
            "trainedBy": v.trained_by,
            "createdAt": v.created_at,
        }
        for v in rows
    ]
