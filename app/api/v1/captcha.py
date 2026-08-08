"""行为验证码接口：代理 go-captcha-service（生成 / 校验 / 状态查询）。

go-captcha-service 是官方 Go 验证码服务（Docker 部署），本模块将其
HTTP 接口包装为业务 API，并供登录等场景强制校验。
"""

import json
import logging
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.response import ApiResponse, ok

router = APIRouter(prefix="/captcha", tags=["验证码"])

logger = logging.getLogger("app")


class CaptchaCheckRequest(BaseModel):
    """点选校验请求：captchaKey + 用户点击坐标列表 [[x, y], ...]"""

    captchaKey: str
    dots: list[list[int]]


def _call_captcha(path: str, method: str = "GET", body: dict | None = None, timeout: float = 10) -> dict | None:
    """调用 go-captcha-service 公共接口；失败返回 None（不阻断业务时由调用方兜底）。"""
    if not settings.CAPTCHA_ENABLED:
        return None
    url = f"{settings.CAPTCHA_SERVICE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        logger.warning("[captcha] 调用 go-captcha-service 失败: %s", path, exc_info=True)
        return None


@router.get("", response_model=ApiResponse, summary="获取行为验证码")
def get_captcha():
    """获取点选验证码：主图/缩略图 base64 与 captchaKey。"""
    if not settings.CAPTCHA_ENABLED:
        return ok(
            {
                "captchaKey": "",
                "image": "",
                "thumb": "",
                "width": 0,
                "height": 0,
                "thumbWidth": 0,
                "thumbHeight": 0,
            }
        )
    data = _call_captcha(f"/api/v1/public/get-data?id={settings.CAPTCHA_ID}")
    if not data or not data.get("data"):
        raise BizException("验证码服务暂不可用，请稍后重试", 500)
    d = data["data"]
    return ok(
        {
            "captchaKey": d.get("captcha_key", ""),
            "image": d.get("master_image_base64", ""),
            "thumb": d.get("thumb_image_base64", ""),
            "width": d.get("master_width", 300),
            "height": d.get("master_height", 220),
            "thumbWidth": d.get("thumb_width", 150),
            "thumbHeight": d.get("thumb_height", 40),
        }
    )


@router.post("/check", response_model=ApiResponse, summary="校验验证码点选")
def check_captcha(req: CaptchaCheckRequest):
    """校验用户点选坐标；通过后 go-captcha-service 缓存该 captchaKey 为已通过状态。"""
    if not settings.CAPTCHA_ENABLED:
        return ok({"passed": True})
    value = ",".join(f"{x},{y}" for x, y in req.dots)
    data = _call_captcha(
        "/api/v1/public/check-data",
        method="POST",
        body={"id": settings.CAPTCHA_ID, "captchaKey": req.captchaKey, "value": value},
    )
    return ok({"passed": bool(data and data.get("data") == "ok")})


def check_captcha_status(captchaKey: str) -> bool:
    """供登录等场景查询验证码是否已通过校验（服务端缓存 status=1）。"""
    if not settings.CAPTCHA_ENABLED or not captchaKey:
        return False
    data = _call_captcha(f"/api/v1/public/check-status?captchaKey={captchaKey}")
    return bool(data and data.get("data") == "ok")
