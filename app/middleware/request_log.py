"""API 请求日志中间件：记录 /api/* 请求到 ApiLog 表（管理平台 API 管理数据源）"""

import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.api_log import ApiLog

_BODY_LIMIT = 2000
_RESP_LIMIT = 1000

# 敏感路径：请求体不落库（登录密码等）
_SENSITIVE_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}


def _mask_sensitive(text: str) -> str:
    """脱敏敏感字段值（password / token / authorization），防止明文落库。"""
    text = re.sub(r'(?i)("(?:password|passwd|new_password)"\s*:\s*")[^"]*(")', r"\1***\2", text)
    text = re.sub(r'(?i)("(?:token|access_token|refresh_token)"\s*:\s*")[^"]*(")', r"\1***\2", text)
    text = re.sub(r'(?i)("authorization"\s*:\s*")[^"]*(")', r"\1***\2", text)
    return text


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        path = request.url.path
        # 仅记录业务 API
        if not path.startswith("/api/"):
            return response

        try:
            # 请求体（仅 JSON，截断；敏感路径不记录）
            req_body = None
            if request.method in ("POST", "PUT", "DELETE") and request.headers.get("content-type", "").startswith(
                "application/json"
            ):
                raw = await request.body()
                if path in _SENSITIVE_PATHS:
                    req_body = None
                else:
                    req_body = _mask_sensitive(raw.decode("utf-8", errors="replace")[:_BODY_LIMIT])

            # 响应预览（JSONResponse 可读取 body；脱敏 token）
            resp_preview = None
            try:
                body = b"".join([chunk async for chunk in response.body_iterator])
                resp_preview = _mask_sensitive(body.decode("utf-8", errors="replace")[:_RESP_LIMIT])
                response.body_iterator = _iterate_bytes([body])
            except Exception:
                pass

            # 识别用户
            username = None
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                payload = decode_token(auth[7:])
                if payload:
                    username = payload.get("sub")

            client_ip = request.client.host if request.client else None

            log = ApiLog(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                username=username,
                req_body=req_body,
                resp_preview=resp_preview,
            )
            try:
                db = SessionLocal()
                try:
                    db.add(log)
                    db.commit()
                finally:
                    db.close()
            except Exception:
                pass
        except Exception:
            pass

        return response


def _iterate_bytes(bodies):
    async def _agen():
        for b in bodies:
            yield b

    return _agen()
