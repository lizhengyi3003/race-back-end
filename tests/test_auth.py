"""认证接口测试"""


def test_login_success(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert data["code"] == 200
    assert data["data"]["token"]
    assert data["data"]["user"]["username"] == "admin"


def test_login_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    data = r.json()
    assert data["code"] == 401


def test_me_requires_auth(client):
    r = client.get("/api/v1/auth/me")
    assert r.json()["code"] == 401


def test_me_with_token(client, auth_headers):
    r = client.get("/api/v1/auth/me", headers=auth_headers)
    data = r.json()
    assert data["code"] == 200
    assert data["data"]["username"] == "admin"
