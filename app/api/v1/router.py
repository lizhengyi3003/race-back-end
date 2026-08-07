"""v1 路由汇总"""

from fastapi import APIRouter

from app.api.v1 import admin, auth, dashboard, data, indicator, model, monitor, risk

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(risk.router)
api_router.include_router(dashboard.router)
api_router.include_router(model.router)
api_router.include_router(data.router)
api_router.include_router(admin.router)
api_router.include_router(monitor.router)
api_router.include_router(indicator.router)
