"""管理平台服务：用户管理 / API 日志 / 系统概览"""

from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.security import hash_password
from app.models.api_log import ApiLog
from app.models.assessment import AssessmentRecord
from app.models.model_version import ModelVersion
from app.models.sys_config import SystemConfig
from app.models.user import User
from app.schemas.admin import ApiLogOut, SystemOverview, UserCreate, UserUpdate
from app.schemas.auth import UserOut
from app.schemas.common import PageData


# ---------- 用户管理 ----------
def list_users(db: Session, page: int, size: int, keyword: str | None) -> PageData[UserOut]:
    query = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(User.username.like(like), User.real_name.like(like)))
    total = query.count()
    items = query.order_by(User.id.asc()).offset((page - 1) * size).limit(size).all()
    return PageData(total=total, page=page, size=size, items=[UserOut.model_validate(u) for u in items])


def create_user(db: Session, req: UserCreate) -> UserOut:
    exists = db.query(User).filter(User.username == req.username).first()
    if exists:
        raise BizException("用户名已存在")
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        real_name=req.realName,
        role=req.role,
        status=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def update_user(db: Session, user_id: int, req: UserUpdate) -> UserOut:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BizException("用户不存在", 404)
    if req.realName is not None:
        user.real_name = req.realName
    if req.role is not None:
        user.role = req.role
    if req.status is not None:
        user.status = req.status
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def delete_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BizException("用户不存在", 404)
    if user.username == settings.DEFAULT_ADMIN_USERNAME:
        raise BizException("默认管理员不可删除")
    db.delete(user)
    db.commit()


def reset_password(db: Session, user_id: int, new_password: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BizException("用户不存在", 404)
    user.password_hash = hash_password(new_password)
    db.commit()


# ---------- API 日志 ----------
def list_api_logs(
    db: Session,
    page: int,
    size: int,
    method: str | None,
    path: str | None,
    status: int | None,
) -> PageData[ApiLogOut]:
    query = db.query(ApiLog)
    if method:
        query = query.filter(ApiLog.method == method.upper())
    if path:
        query = query.filter(ApiLog.path.like(f"%{path}%"))
    if status:
        query = query.filter(ApiLog.status_code == status)
    total = query.count()
    items = query.order_by(ApiLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return PageData(
        total=total,
        page=page,
        size=size,
        items=[
            ApiLogOut(
                id=log.id,
                method=log.method,
                path=log.path,
                statusCode=log.status_code,
                durationMs=log.duration_ms,
                clientIp=log.client_ip,
                username=log.username,
                reqBody=log.req_body,
                respPreview=log.resp_preview,
                createdAt=log.created_at,
            )
            for log in items
        ],
    )


def cleanup_api_logs(db: Session, days: int | None = None) -> int:
    days = days or settings.API_LOG_RETENTION_DAYS
    cutoff = datetime.now() - timedelta(days=days)
    deleted = db.query(ApiLog).filter(ApiLog.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return int(deleted)


# ---------- 系统概览 ----------
def system_overview(db: Session) -> SystemOverview:
    users = db.query(func.count(User.id)).scalar() or 0
    records = db.query(func.count(AssessmentRecord.id)).scalar() or 0
    models = db.query(func.count(ModelVersion.id)).scalar() or 0
    api_logs = db.query(func.count(ApiLog.id)).scalar() or 0
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    api_today = db.query(func.count(ApiLog.id)).filter(ApiLog.created_at >= today_start).scalar() or 0
    return SystemOverview(
        users=users,
        records=records,
        models=models,
        apiLogs=api_logs,
        apiLogsToday=api_today,
        database="MySQL" if not settings.is_sqlite else "SQLite",
        version=settings.APP_VERSION,
        serverTime=datetime.now(),
    )


def list_system_configs(db: Session) -> list[dict]:
    rows = db.query(SystemConfig).order_by(SystemConfig.id.asc()).all()
    return [
        {"key": r.config_key, "value": r.config_value, "description": r.description, "updatedAt": r.updated_at}
        for r in rows
    ]


def update_system_config(db: Session, key: str, value: str) -> dict:
    row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if not row:
        raise BizException("配置项不存在", 404)
    row.config_value = value
    row.updated_at = datetime.now()
    db.commit()
    return {
        "key": row.config_key,
        "value": row.config_value,
        "description": row.description,
        "updatedAt": row.updated_at,
    }
