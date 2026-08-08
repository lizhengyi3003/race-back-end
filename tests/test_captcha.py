"""验证码接口与登录强制校验测试。

conftest 默认 CAPTCHA_ENABLED=false 跳过验证码；本测试通过 monkeypatch
将验证码开关打开并 mock go-captcha-service 调用层，验证：
1. /captcha 代理接口字段转换
2. /captcha/check 校验结果透传
3. 登录强制校验：验证码未通过 → 400；已通过 → 正常登录
"""

from unittest import mock

from app.core.config import settings

# go-captcha-service get-data 模拟返回（与官方 HTTP 响应结构一致）
_MOCK_GET_DATA = {
    "code": 200,
    "message": "success",
    "data": {
        "captcha_key": "mock-key-123",
        "master_image_base64": "data:image/jpeg;base64,AAAA",
        "thumb_image_base64": "data:image/png;base64,BBBB",
        "master_width": 300,
        "master_height": 220,
        "thumb_width": 150,
        "thumb_height": 40,
        "id": "click-default-ch",
    },
}


def _enable_captcha(monkeypatch):
    monkeypatch.setattr(settings, "CAPTCHA_ENABLED", True)


def test_get_captcha_fields(monkeypatch, client):
    """/captcha 应透传验证码数据并转换为前端友好字段"""
    _enable_captcha(monkeypatch)
    with mock.patch("app.api.v1.captcha._call_captcha", return_value=_MOCK_GET_DATA) as m:
        r = client.get("/api/v1/captcha")
    assert r.json()["code"] == 200
    d = r.json()["data"]
    assert d["captchaKey"] == "mock-key-123"
    assert d["image"].startswith("data:image/jpeg")
    assert d["thumb"].startswith("data:image/png")
    assert d["width"] == 300 and d["height"] == 220
    assert d["thumbWidth"] == 150 and d["thumbHeight"] == 40
    # 代理应携带 click 配置 id
    assert "id=click-default-ch" in m.call_args.args[0]


def test_check_captcha_passed(monkeypatch, client):
    """点选校验通过时返回 passed=true"""
    _enable_captcha(monkeypatch)
    with mock.patch(
        "app.api.v1.captcha._call_captcha",
        return_value={"code": 200, "data": "ok"},
    ) as m:
        r = client.post("/api/v1/captcha/check", json={"captchaKey": "k1", "dots": [[10, 20], [30, 40]]})
    assert r.json()["data"]["passed"] is True
    # 转发给 go-captcha-service 的 value 应为逗号分隔坐标
    body = m.call_args.kwargs["body"]
    assert body["value"] == "10,20,30,40"


def test_check_captcha_failed(monkeypatch, client):
    """点选校验失败时返回 passed=false"""
    _enable_captcha(monkeypatch)
    with mock.patch(
        "app.api.v1.captcha._call_captcha",
        return_value={"code": 200, "data": "failure"},
    ):
        r = client.post("/api/v1/captcha/check", json={"captchaKey": "k1", "dots": [[1, 2]]})
    assert r.json()["data"]["passed"] is False


def test_login_blocked_without_captcha(monkeypatch, client):
    """验证码未通过时登录应被拦截（400）"""
    _enable_captcha(monkeypatch)
    with mock.patch("app.api.v1.auth.check_captcha_status", return_value=False):
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123", "captchaKey": "k1"})
    assert r.json()["code"] == 400
    assert "安全验证" in r.json()["message"]


def test_login_allowed_with_passed_captcha(monkeypatch, client):
    """验证码已通过时登录应成功（200 + token）"""
    _enable_captcha(monkeypatch)
    with mock.patch("app.api.v1.auth.check_captcha_status", return_value=True):
        r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123", "captchaKey": "k1"})
    assert r.json()["code"] == 200
    assert r.json()["data"]["token"]
