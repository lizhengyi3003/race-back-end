"""模型文件持久化：pickle 保存 / 加载评分卡"""

from __future__ import annotations

import pickle
from pathlib import Path

from app.core.config import settings
from app.ml.scorecard import Scorecard


def artifact_dir() -> Path:
    Path(settings.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    return Path(settings.MODEL_DIR)


def _resolve(path: str) -> Path:
    """兼容历史相对路径（如 data\\models\\xxx.pkl）：相对路径解析到项目根。"""
    p = Path(path)
    if p.is_absolute():
        return p
    from app.core.config import PROJECT_ROOT

    return PROJECT_ROOT / p


def save_scorecard(model: Scorecard) -> str:
    """保存评分卡，返回文件路径（绝对路径，跨 cwd 可加载）"""
    path = artifact_dir() / f"scorecard_{model.version}.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    return str(path)


def load_scorecard(path: str) -> Scorecard | None:
    try:
        with open(_resolve(path), "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def latest_artifact() -> str | None:
    """返回最新模型文件路径（按文件名排序）"""
    files = sorted(artifact_dir().glob("scorecard_*.pkl"))
    return str(files[-1]) if files else None
