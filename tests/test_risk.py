"""风险评估接口契约测试（对齐前端 types.ts）"""

from tests.conftest import SAMPLE_INPUT


def test_assess_contract(client):
    r = client.post("/api/v1/risk/assess", json=SAMPLE_INPUT)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    data = body["data"]

    # 契约字段
    assert 0 <= data["score"] <= 1000
    assert 0 < data["probability"] < 1
    assert data["level"] in ("低风险", "中等风险", "高风险")
    assert data["suggestedAmount"] >= 0
    assert data["suggestedRate"] > 0
    assert len(data["contributions"]) == 15
    assert len(data["deductions"]) == 3
    assert data["advice"]

    # 贡献度结构
    c0 = data["contributions"][0]
    assert {"factor", "category", "weight", "score"} <= set(c0.keys())
    assert 0 <= c0["score"] <= 100

    # 扣分项结构
    d0 = data["deductions"][0]
    assert {"factor", "score", "reason"} <= set(d0.keys())


def test_assess_discriminates(client):
    """优质客户与高风险客户应得到不同等级"""
    good = client.post("/api/v1/risk/assess", json=SAMPLE_INPUT).json()["data"]
    bad_input = dict(SAMPLE_INPUT)
    bad_input.update(
        {
            "landConfirmedArea": 30,
            "landTransferYears": 0,
            "landTransferStability": "频繁变更",
            "blackSoilProtection": 0,
            "grainSubsidy": 800,
            "machinerySubsidy": 0,
            "grainScaleSubsidy": 0,
            "specialtyCropSubsidy": 0,
            "insuranceYears": 0,
            "claimCount": 6,
            "facilityInsurance": "未投保",
            "yearsOperating": 1,
            "purchaseOrder": "无稳定渠道",
            "annualRevenue": 5,
            "creditRecord": "有逾期",
        }
    )
    bad = client.post("/api/v1/risk/assess", json=bad_input).json()["data"]
    assert good["score"] > bad["score"]


def test_records_requires_auth(client):
    r = client.get("/api/v1/risk/records")
    assert r.json()["code"] == 401


def test_records_list_and_detail(client, auth_headers):
    client.post("/api/v1/risk/assess", json=SAMPLE_INPUT)
    r = client.get("/api/v1/risk/records", headers=auth_headers, params={"page": 1, "size": 5})
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["total"] >= 1
    item = body["data"]["items"][0]
    assert item["score"] > 0

    r2 = client.get(f"/api/v1/risk/records/{item['id']}", headers=auth_headers)
    assert r2.json()["code"] == 200
    assert r2.json()["data"]["input"] is not None


def test_delete_record(client, auth_headers):
    client.post("/api/v1/risk/assess", json=SAMPLE_INPUT)
    r = client.get("/api/v1/risk/records", headers=auth_headers, params={"size": 1})
    rid = r.json()["data"]["items"][0]["id"]
    r2 = client.delete(f"/api/v1/risk/records/{rid}", headers=auth_headers)
    assert r2.json()["code"] == 200


def test_override_rules_extreme(client):
    """极端灾损客户应触发兜底规则并强制高风险"""
    extreme = {
        "enterpriseName": "灾损户",
        "landConfirmedArea": 300,
        "blackSoilProtection": 0,
        "insuranceYears": 0,
        "claimCount": 6,
        "annualRevenue": 20,
        "creditRecord": "有逾期",
    }
    r = client.post("/api/v1/risk/assess", json=extreme)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["level"] == "高风险"
    assert data["score"] <= 450
    assert data["probability"] >= 0.7
    assert len(data["overrides"]) >= 1
    assert "人工复核" in data["advice"]


def test_override_rules_not_triggered_for_good(client):
    """优质客户不应误触发兜底规则"""
    r = client.post("/api/v1/risk/assess", json=SAMPLE_INPUT)
    data = r.json()["data"]
    assert data["overrides"] == []
