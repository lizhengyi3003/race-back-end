"""API 依赖：JWT 认证"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import BizException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise BizException("未登录或登录已过期", 401)
    payload = decode_token(credentials.credentials)
    if not payload:
        raise BizException("登录凭证无效", 401)
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user:
        raise BizException("用户不存在", 401)
    if user.status != 1:
        raise BizException("账号已被禁用", 403)
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """可选认证：无凭证时返回 None（用于公开的评估接口记录操作人）"""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if user and user.status == 1:
        return user
    return None
