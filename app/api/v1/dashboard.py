"""数据看板接口（公开，供竞赛前端使用）"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.schemas.dashboard import DashboardStats, IndustryItem, ScoreDistItem, TrendItem
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/stats", response_model=ApiResponse[DashboardStats], summary="看板统计概览")
def stats(db: Session = Depends(get_db)):
    return ok(dashboard_service.stats(db))


@router.get("/industry-distribution", response_model=ApiResponse[list[IndustryItem]], summary="行业风险分布")
def industry_distribution(db: Session = Depends(get_db)):
    return ok(dashboard_service.industry_distribution(db))


@router.get("/score-distribution", response_model=ApiResponse[list[ScoreDistItem]], summary="信用评分分布")
def score_distribution(db: Session = Depends(get_db)):
    return ok(dashboard_service.score_distribution(db))


@router.get("/trend", response_model=ApiResponse[list[TrendItem]], summary="评估趋势")
def trend(days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    return ok(dashboard_service.trend(db, days))
