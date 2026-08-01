"""系统监控接口：服务器状态 / 数据库状态 / 健康检查"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.monitor import DatabaseStatus, HealthStatus, ServerStatus
from app.services import monitor_service

router = APIRouter(prefix="/monitor", tags=["系统监控"])


@router.get("/server", response_model=ApiResponse[ServerStatus], summary="服务器状态")
def server(_: User = Depends(get_current_user)):
    return ok(monitor_service.server_status())


@router.get("/database", response_model=ApiResponse[DatabaseStatus], summary="数据库状态")
def database(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(monitor_service.database_status(db))


@router.get("/health", response_model=ApiResponse[HealthStatus], summary="健康检查")
def health(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(monitor_service.health(db))
