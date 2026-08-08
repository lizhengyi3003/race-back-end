"""系统监控与管理平台接口测试"""


def test_monitor_health(client, auth_headers):
    r = client.get("/api/v1/monitor/health", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["service"] == "ok"
    assert data["database"] == "ok"
    assert data["modelExists"] is True


def test_monitor_server(client, auth_headers):
    r = client.get("/api/v1/monitor/server", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert "cpu" in data and "memory" in data and "disk" in data
    assert 0 <= data["cpu"]["percent"] <= 100


def test_monitor_database(client, auth_headers):
    r = client.get("/api/v1/monitor/database", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["connected"] is True
    assert len(data["tables"]) >= 4  # user/record/model/config/api_log


def test_admin_stats(client, auth_headers):
    r = client.get("/api/v1/admin/stats", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["users"] >= 1


def test_admin_users_crud(client, auth_headers):
    # 创建
    r = client.post(
        "/api/v1/admin/users",
        json={"username": "testuser", "password": "test123", "realName": "测试用户", "role": "analyst"},
        headers=auth_headers,
    )
    assert r.json()["code"] == 200
    uid = r.json()["data"]["id"]

    # 列表
    r = client.get("/api/v1/admin/users", headers=auth_headers, params={"keyword": "testuser"})
    assert r.json()["data"]["total"] >= 1

    # 更新
    r = client.put(f"/api/v1/admin/users/{uid}", json={"status": 0}, headers=auth_headers)
    assert r.json()["data"]["status"] == 0

    # 重置密码
    r = client.post(f"/api/v1/admin/users/{uid}/reset-password", json={"newPassword": "newpass"}, headers=auth_headers)
    assert r.json()["code"] == 200

    # 删除
    r = client.delete(f"/api/v1/admin/users/{uid}", headers=auth_headers)
    assert r.json()["code"] == 200


def test_api_spec(client, auth_headers):
    r = client.get("/api/v1/admin/api-spec", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    assert len(body["data"]) >= 20


def test_api_logs(client, auth_headers):
    from tests.conftest import SAMPLE_INPUT

    client.post("/api/v1/risk/assess-dynamic", json=SAMPLE_INPUT)
    r = client.get("/api/v1/admin/api-logs", headers=auth_headers, params={"page": 1, "size": 5})
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["total"] >= 1
