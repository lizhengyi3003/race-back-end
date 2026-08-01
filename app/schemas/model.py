"""模型管理相关"""

from datetime import datetime

from pydantic import BaseModel


class ModelInfo(BaseModel):
    version: str
    status: str
    trainedAt: datetime | None = None
    nSamples: int = 0
    nFeatures: int = 0
    auc: float | None = None
    ks: float | None = None
    recall: float | None = None
    precision: float | None = None
    f1: float | None = None


class TrainRequest(BaseModel):
    nSamples: int | None = None  # 不传则使用默认样本量


class Thresholds(BaseModel):
    lowRiskThreshold: int = 700
    highRiskThreshold: int = 500
    baseRate: float = 3.5
    riskPremiumFactor: float = 6.0


class MetricsOut(BaseModel):
    auc: float
    ks: float
    recall: float
    precision: float
    f1: float
    accuracy: float
    bestThreshold: float
    confusionMatrix: list[list[int]]
    rocCurve: list[dict]  # [{fpr, tpr}]
    ksCurve: list[dict]  # [{threshold, tpr, fpr, diff}]
    ivTable: list[dict]  # [{factor, iv, woeBins, nBins}]
    featureImportance: list[dict]  # [{factor, weight}]
    cvScores: list[float]  # 5 折 CV AUC
    psi: float | None = None  # 训练集 vs 测试集 PSI


class ModelVersionOut(BaseModel):
    id: int
    version: str
    status: str
    nSamples: int
    nFeatures: int
    auc: float | None = None
    ks: float | None = None
    recall: float | None = None
    precision: float | None = None
    f1: float | None = None
    trainedBy: str | None = None
    createdAt: datetime | None = None
