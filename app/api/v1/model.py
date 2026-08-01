"""模型管理接口"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.model import ModelInfo, ModelVersionOut, Thresholds, TrainRequest
from app.services import model_service

router = APIRouter(prefix="/model", tags=["模型管理"])


@router.get("/info", response_model=ApiResponse[ModelInfo], summary="当前模型信息")
def model_info(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(model_service.get_active_model_info(db))


@router.get("/versions", response_model=ApiResponse[list[ModelVersionOut]], summary="模型版本列表")
def model_versions(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(model_service.list_versions(db))


@router.get("/metrics", response_model=ApiResponse, summary="模型评估指标与曲线")
def model_metrics(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(model_service.get_metrics(db))


@router.get("/monitor", response_model=ApiResponse, summary="模型持续监控（PSI/客群迁移预警）")
def model_monitor(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(model_service.get_monitor(db))


@router.get("/simulate", response_model=ApiResponse, summary="业务仿真验证（极端场景模拟）")
def model_simulate(
    nSamples: int = Query(2000, ge=100, le=10000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(model_service.run_simulation(db, n_samples=nSamples))


@router.post("/train", response_model=ApiResponse, summary="训练 / 重训评分卡")
def train(
    req: TrainRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = req or TrainRequest()
    result = model_service.train(db, n_samples=req.nSamples, trained_by=user.username)
    return ok(result, message="训练完成")


@router.get("/thresholds", response_model=ApiResponse[Thresholds], summary="获取业务阈值")
def get_thresholds(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(model_service.get_thresholds(db))


@router.put("/thresholds", response_model=ApiResponse[Thresholds], summary="更新业务阈值")
def put_thresholds(
    req: Thresholds,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(model_service.save_thresholds(db, req.model_dump()))
