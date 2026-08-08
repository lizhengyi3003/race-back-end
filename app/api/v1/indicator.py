"""指标配置路由：类别树。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.schemas.indicator import IndicatorTree
from app.services import indicator_service

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/tree", response_model=ApiResponse[IndicatorTree], summary="指标类别树")
def indicator_tree(db: Session = Depends(get_db)) -> ApiResponse[IndicatorTree]:
    """指标类别树（基本项 + 大类→中类→小类，含各节点指标数）。"""
    return ok(indicator_service.get_indicator_tree(db))
