"""认证接口"""

import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BizException
from app.core.response import ApiResponse, ok
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])

# ---------- 登录暴力破解防护（按 IP 内存计数，超阈值锁定）----------
_LOGIN_FAIL: dict[str, list] = {}  # ip -> [失败次数, 锁定截止时间戳]
_MAX_FAILS = 10
_LOCK_SECONDS = 15 * 60


def _check_login_lock(ip: str) -> None:
    rec = _LOGIN_FAIL.get(ip)
    if rec:
        if rec[1] > time.time():
            raise BizException("登录失败次数过多，请 15 分钟后再试", 429)
        if rec[0] >= _MAX_FAILS:
            _LOGIN_FAIL[ip] = [0, time.time() + _LOCK_SECONDS]
            raise BizException("登录失败次数过多，请 15 分钟后再试", 429)


def _record_login_fail(ip: str) -> None:
    rec = _LOGIN_FAIL.get(ip, [0, 0])
    _LOGIN_FAIL[ip] = [rec[0] + 1, rec[1]]


def _record_login_success(ip: str) -> None:
    _LOGIN_FAIL.pop(ip, None)


@router.post("/login", response_model=ApiResponse[LoginResponse], summary="用户登录")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    _check_login_lock(ip)
    try:
        user = auth_service.authenticate(db, req.username, req.password)
    except BizException as e:
        if e.code == 401:
            _record_login_fail(ip)
        raise
    _record_login_success(ip)
    auth_service.update_last_login(db, user)
    token = create_access_token(user.username, user.role)
    return ok(LoginResponse(token=token, user=UserOut.model_validate(user)))


@router.get("/me", response_model=ApiResponse[UserOut], summary="当前用户信息")
def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user))
