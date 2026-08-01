"""业务异常与全局异常处理器。

统一约定：无论成功失败，HTTP 状态码均为 200，
响应体为 {code, message, data}，前端以 code 判断成败。
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import ApiResponse


class BizException(Exception):
    """业务异常"""

    def __init__(self, message: str = "业务处理失败", code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizException)
    async def biz_handler(request: Request, exc: BizException):
        return JSONResponse(
            status_code=200,
            content=ApiResponse(code=exc.code, message=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = ".".join(str(x) for x in first.get("loc", []))
        msg = first.get("msg", "参数校验失败")
        return JSONResponse(
            status_code=200,
            content=ApiResponse(code=422, message=f"参数错误：{loc} {msg}").model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=200,
            content=ApiResponse(code=exc.status_code, message=str(exc.detail)).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=200,
            content=ApiResponse(code=500, message=f"服务器内部错误：{exc}").model_dump(),
        )
