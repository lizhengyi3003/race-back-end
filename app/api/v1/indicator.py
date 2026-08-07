"""指标配置路由：类别树 + 渐进式表单字段配置。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.schemas.indicator import IndicatorConfigOut, IndicatorTree
from app.services import indicator_service

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/tree", response_model=ApiResponse[IndicatorTree], summary="指标类别树")
def indicator_tree(db: Session = Depends(get_db)) -> ApiResponse[IndicatorTree]:
    """指标类别树（基本项 + 大类→中类→小类，含各节点指标数）。"""
    return ok(indicator_service.get_indicator_tree(db))


@router.get("/config", response_model=ApiResponse[IndicatorConfigOut], summary="渐进式表单字段配置")
def indicator_config(
    business_type: str = Query(..., alias="businessType", description="经营类型大类编码 01~10"),
    middle_type: str = Query("", alias="middleType", description="中类编码（可选，选中后追加该中类指标）"),
    small_type: str = Query("", alias="smallType", description="小类编码（可选，选中后追加该小类指标）"),
    db: Session = Depends(get_db),
) -> ApiResponse[IndicatorConfigOut]:
    """渐进式表单配置：基本项 + 按所选类别逐级追加指标字段。"""
    cfg = indicator_service.get_indicator_config(db, business_type, middle_type, small_type)
    return ok(cfg)
