"""行为验证码接口：代理 go-captcha-service（生成 / 校验 / 状态查询）。

go-captcha-service 是官方 Go 验证码服务（Docker 部署），本模块将其
HTTP 接口包装为业务 API，并供登录等场景强制校验。
支持四种交互模式随机轮换：click（点选）/ slide（滑块）/ drag（拖拽）/ rotate（旋转）。
"""

import json
import logging
import random
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import BizException
from app.core.response import ApiResponse, ok

router = APIRouter(prefix="/captcha", tags=["验证码"])

logger = logging.getLogger("app")

# 支持的验证码类型 → go-captcha-service 配置 id
CAPTCHA_TYPES: list[tuple[str, str]] = [
    ("click", "click-default-ch"),
    ("slide", "slide-default"),
    ("drag", "drag-default"),
    ("rotate", "rotate-default"),
]
_TYPE_ID_MAP = dict(CAPTCHA_TYPES)

# 内存记录 captchaKey → 类型（go-captcha-service 校验时需对应配置 id）
_KEY_TYPES: dict[str, str] = {}
_KEY_TYPES_MAX = 1000  # 上限，超出后清理最旧记录，避免长期运行内存增长


def _remember_key(captcha_key: str, captcha_type: str) -> None:
    """记录 captchaKey→类型；超上限时删除最旧记录（dict 保持插入顺序）。"""
    _KEY_TYPES[captcha_key] = captcha_type
    while len(_KEY_TYPES) > _KEY_TYPES_MAX:
        _KEY_TYPES.pop(next(iter(_KEY_TYPES)))


class CaptchaCheckRequest(BaseModel):
    """校验请求：captchaKey + 类型 + 统一 value 字符串。

    value 格式：click="x1,y1,x2,y2"；slide/drag="x,y"；rotate="角度数值"
    """

    captchaKey: str
    type: str = ""
    value: str = ""


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


@router.get("", response_model=ApiResponse, summary="获取行为验证码（四种模式随机）")
def get_captcha():
    """获取行为验证码：click/slide/drag/rotate 随机一种，返回 type 与对应数据。"""
    if not settings.CAPTCHA_ENABLED:
        return ok(
            {
                "type": "click",
                "captchaKey": "",
                "image": "",
                "thumb": "",
                "width": 0,
                "height": 0,
                "thumbWidth": 0,
                "thumbHeight": 0,
                "thumbSize": 0,
                "displayX": 0,
                "displayY": 0,
            }
        )
    captcha_type, captcha_id = random.choice(CAPTCHA_TYPES)
    data = _call_captcha(f"/api/v1/public/get-data?id={captcha_id}")
    if not data or not data.get("data"):
        raise BizException("验证码服务暂不可用，请稍后重试", 500)
    d = data["data"]
    captcha_key = d.get("captcha_key", "")
    _remember_key(captcha_key, captcha_type)
    return ok(
        {
            "type": captcha_type,
            "captchaKey": captcha_key,
            "image": d.get("master_image_base64", ""),
            "thumb": d.get("thumb_image_base64", ""),
            "width": d.get("master_width", 300),
            "height": d.get("master_height", 220),
            "thumbWidth": d.get("thumb_width", 150),
            "thumbHeight": d.get("thumb_height", 40),
            "thumbSize": d.get("thumb_size", 0),
            "displayX": d.get("display_x", 0),
            "displayY": d.get("display_y", 0),
        }
    )


@router.post("/check", response_model=ApiResponse, summary="校验验证码")
def check_captcha(req: CaptchaCheckRequest):
    """校验验证码作答；通过后 go-captcha-service 缓存该 captchaKey 为已通过状态。"""
    if not settings.CAPTCHA_ENABLED:
        return ok({"passed": True})
    captcha_type = req.type or _KEY_TYPES.get(req.captchaKey, "click")
    captcha_id = _TYPE_ID_MAP.get(captcha_type, "click-default-ch")
    data = _call_captcha(
        "/api/v1/public/check-data",
        method="POST",
        body={"id": captcha_id, "captchaKey": req.captchaKey, "value": req.value},
    )
    return ok({"passed": bool(data and data.get("data") == "ok")})


def check_captcha_status(captchaKey: str) -> bool:
    """供登录等场景查询验证码是否已通过校验（服务端缓存 status=1）。"""
    if not settings.CAPTCHA_ENABLED or not captchaKey:
        return False
    data = _call_captcha(f"/api/v1/public/check-status?captchaKey={captchaKey}")
    return bool(data and data.get("data") == "ok")
