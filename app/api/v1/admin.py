"""管理平台接口：用户管理 / API 日志 / API 端点列表 / 系统配置"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.response import ApiResponse, ok
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    ApiLogOut,
    ResetPasswordRequest,
    SystemOverview,
    UserCreate,
    UserUpdate,
)
from app.schemas.auth import UserOut
from app.schemas.common import PageData
from app.schemas.indicator_admin import IndicatorUpdate
from app.services import admin_service, indicator_service

router = APIRouter(prefix="/admin", tags=["管理平台"])


@router.get("/stats", response_model=ApiResponse[SystemOverview], summary="系统概览")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(admin_service.system_overview(db))


# ---------- 用户管理 ----------
@router.get("/users", response_model=ApiResponse[PageData[UserOut]], summary="用户列表")
def users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(admin_service.list_users(db, page, size, keyword))


@router.post("/users", response_model=ApiResponse[UserOut], summary="新增用户")
def add_user(req: UserCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(admin_service.create_user(db, req))


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut], summary="更新用户")
def edit_user(
    user_id: int,
    req: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(admin_service.update_user(db, user_id, req))


@router.delete("/users/{user_id}", response_model=ApiResponse, summary="删除用户")
def remove_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    admin_service.delete_user(db, user_id)
    return ok(message="删除成功")


@router.post("/users/{user_id}/reset-password", response_model=ApiResponse, summary="重置密码")
def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    admin_service.reset_password(db, user_id, req.newPassword)
    return ok(message="密码已重置")


# ---------- API 日志 ----------
@router.get("/api-logs", response_model=ApiResponse[PageData[ApiLogOut]], summary="API 调用日志")
def api_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    method: str | None = None,
    path: str | None = None,
    status: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(admin_service.list_api_logs(db, page, size, method, path, status))


@router.delete("/api-logs", response_model=ApiResponse, summary="清理过期 API 日志")
def cleanup_logs(
    days: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    deleted = admin_service.cleanup_api_logs(db, days)
    return ok({"deleted": deleted}, message=f"已清理 {deleted} 条日志")


# ---------- API 端点列表（聚合 OpenAPI）----------
@router.get("/api-spec", response_model=ApiResponse, summary="API 端点列表")
def api_spec(request: Request, _: User = Depends(get_current_user)):
    schema = request.app.openapi()
    paths = schema.get("paths", {})
    items = []
    for path, methods in paths.items():
        if not path.startswith("/api/"):
            continue
        for method, op in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            security = op.get("security", [])
            auth_required = len(security) > 0
            params = []
            for p in op.get("parameters", []):
                params.append({"name": p.get("name"), "in": p.get("in"), "required": p.get("required", False)})
            req_example = None
            rb = op.get("requestBody")
            if rb:
                req_example = _build_example(rb, schema.get("components", {}).get("schemas", {}))
            items.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "summary": op.get("summary", ""),
                    "tags": op.get("tags", []),
                    "authRequired": auth_required,
                    "parameters": params,
                    "requestBodyExample": req_example,
                }
            )
    items.sort(key=lambda x: (x["path"], x["method"]))
    return ok(items)


def _build_example(rb: dict, schemas: dict) -> dict | None:
    try:
        content = rb.get("content", {})
        ref = content.get("application/json", {}).get("schema", {})
        return _example_from_ref(ref, schemas)
    except Exception:
        return None


def _example_from_ref(schema: dict, schemas: dict) -> dict | None:
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return _example_from_schema(schemas.get(name, {}), schemas)
    return _example_from_schema(schema, schemas)


def _example_from_schema(schema: dict, schemas: dict) -> dict | None:
    if schema.get("type") == "object" or "properties" in schema:
        example = {}
        for name, prop in (schema.get("properties") or {}).items():
            if "$ref" in prop:
                example[name] = _example_from_schema(schemas.get(prop["$ref"].split("/")[-1], {}), schemas)
            elif prop.get("type") == "object":
                example[name] = _example_from_schema(prop, schemas)
            elif prop.get("type") == "array":
                example[name] = []
            elif prop.get("type") in ("number", "integer"):
                example[name] = 0
            elif prop.get("type") == "boolean":
                example[name] = False
            else:
                example[name] = ""
        return example
    return None


# ---------- 系统配置 ----------
@router.get("/configs", response_model=ApiResponse, summary="系统配置列表")
def configs(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(admin_service.list_system_configs(db))


@router.put("/configs/{key}", response_model=ApiResponse, summary="更新系统配置")
def update_config(
    key: str,
    value: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(admin_service.update_system_config(db, key, value))


# ---------- 指标管理 ----------
@router.get("/indicators", response_model=ApiResponse, summary="指标分页列表")
def indicator_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    keyword: str | None = None,
    level: str | None = None,
    categoryCode: str | None = None,
    indicatorType: str | None = None,
    isFeature: bool | None = None,
    isVeto: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(
        indicator_service.list_indicators(
            db, page, size, keyword, level, categoryCode, indicatorType, isFeature, isVeto
        )
    )


@router.get("/indicators/stats", response_model=ApiResponse, summary="指标统计")
def indicator_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(indicator_service.indicator_stats(db))


@router.get("/indicators/{code}", response_model=ApiResponse, summary="指标详情")
def indicator_detail(code: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ok(indicator_service.get_indicator_detail(db, code))


@router.put("/indicators/{code}", response_model=ApiResponse, summary="更新指标")
def indicator_update(
    code: str,
    req: IndicatorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ok(indicator_service.update_indicator(db, code, req), message="已保存")
