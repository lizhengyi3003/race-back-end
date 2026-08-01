"""模型文件持久化：pickle 保存 / 加载评分卡"""

from __future__ import annotations

import pickle
from pathlib import Path

from app.core.config import settings
from app.ml.scorecard import Scorecard


def artifact_dir() -> Path:
    Path(settings.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    return Path(settings.MODEL_DIR)


def save_scorecard(model: Scorecard) -> str:
    """保存评分卡，返回文件路径"""
    path = artifact_dir() / f"scorecard_{model.version}.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    return str(path)


def load_scorecard(path: str) -> Scorecard | None:
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def latest_artifact() -> str | None:
    """返回最新模型文件路径（按文件名排序）"""
    files = sorted(artifact_dir().glob("scorecard_*.pkl"))
    return str(files[-1]) if files else None
