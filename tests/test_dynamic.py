"""Phase 1-4 动态评估与数据管道契约测试。

需要指标配置（indicator_config）参与真实打分，故本模块先种子最小指标集：
- 基本项：BASIC_003 注册成立年限、BASIC_008 年营业收入、BASIC_013 失信被执行人（一票否决）
- 大类 01：01_05 土地/水域经营总面积
"""

import pytest

from app.db.session import SessionLocal
from app.models.indicator import IndicatorConfig

MIN_INDICATORS = [
    dict(
        code="BASIC_003",
        name="注册成立年限",
        level="基本项",
        category_code="BASIC",
        category_name="通用",
        indicator_type="数值",
        unit="年",
        value_range="≥0，截至评估时点",
        data_source="营业执照",
        is_feature=False,
        risk_meaning="主体存续时间",
        weight_star=4.5,
        region="东北全境",
        is_veto=False,
        cycle="实时",
        scoring_rule="数值：越高越好，参考上限 30 年",
        display_order=3,
    ),
    dict(
        code="BASIC_008",
        name="年营业收入",
        level="基本项",
        category_code="BASIC",
        category_name="通用",
        indicator_type="数值",
        unit="万元",
        value_range="近 12 个月主营业务收入",
        data_source="财务报表",
        is_feature=False,
        risk_meaning="经营规模",
        weight_star=5.0,
        region="东北全境",
        is_veto=False,
        cycle="年报",
        scoring_rule="数值：越高越好，参考上限 500 万元",
        display_order=8,
    ),
    dict(
        code="BASIC_013",
        name="当前被列为失信被执行人",
        level="基本项",
        category_code="BASIC",
        category_name="通用",
        indicator_type="布尔",
        unit="",
        value_range="是/否",
        data_source="法院执行信息",
        is_feature=False,
        risk_meaning="重大信用风险",
        weight_star=5.0,
        region="东北全境",
        is_veto=True,
        cycle="实时",
        scoring_rule="命中即拒贷",
        display_order=13,
    ),
    dict(
        code="01_05",
        name="土地/水域经营总面积",
        level="大类",
        category_code="01",
        category_name="农林牧渔业",
        indicator_type="数值",
        unit="亩",
        value_range="≥0",
        data_source="流转合同/村委",
        is_feature=False,
        risk_meaning="经营规模基础",
        weight_star=4.0,
        region="东北全境",
        is_veto=False,
        cycle="年报",
        scoring_rule="数值：越高越好，参考上限 3000 亩",
        display_order=5,
    ),
]


@pytest.fixture(scope="module", autouse=True)
def seed_indicators():
    db = SessionLocal()
    try:
        for m in MIN_INDICATORS:
            exists = db.query(IndicatorConfig).filter(IndicatorConfig.code == m["code"]).first()
            if not exists:
                db.add(IndicatorConfig(**m))
        db.commit()
    finally:
        db.close()
    yield


def _assess(client, indicators, business_type="01", mixed=None):
    payload = {
        "enterpriseName": "测试主体",
        "businessType": business_type,
        "productType": "玉米",
        "indicators": indicators,
    }
    if mixed:
        payload["mixedBusiness"] = mixed
    r = client.post("/api/v1/risk/assess-dynamic", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    return body["data"]


def test_assess_dynamic_contract(client):
    """动态评估契约：score/probability/level/建议/overrides/veto/completeness。"""
    data = _assess(
        client,
        {"BASIC_003": "10", "BASIC_008": "300", "01_05": "1500"},
    )
    assert 0 <= data["score"] <= 1000
    assert 0 < data["probability"] < 1
    assert data["level"] in ("低风险", "中等风险", "高风险")
    assert data["suggestedAmount"] >= 0
    assert data["suggestedRate"] >= 0
    assert isinstance(data["overrides"], list)
    assert data["veto"] is None
    assert 0 <= data["completeness"] <= 1
    assert len(data["contributions"]) >= 1


def test_assess_dynamic_discriminates(client):
    """优质指标与劣质指标应得到不同等级。"""
    good = _assess(
        client,
        {"BASIC_003": "25", "BASIC_008": "450", "01_05": "2800"},
    )
    bad = _assess(
        client,
        {"BASIC_003": "1", "BASIC_008": "10", "01_05": "20"},
    )
    assert good["score"] > bad["score"]
    assert good["level"] in ("低风险", "中等风险")


def test_assess_dynamic_veto(client):
    """一票否决命中 → 高风险 + veto 字段 + 不予授信建议。"""
    data = _assess(client, {"BASIC_013": "是", "BASIC_008": "300"})
    assert data["level"] == "高风险"
    assert data["veto"] == "当前被列为失信被执行人"
    assert "一票否决" in data["advice"]
    assert data["score"] == 200


def test_mixed_synergy(client):
    """混合经营 01+02 命中协同因子 → overrides 记录 synergy:01+02。"""
    data = _assess(
        client,
        {"BASIC_003": "10", "BASIC_008": "300", "01_05": "1500"},
        business_type="MIXED",
        mixed={"01": 0.6, "02": 0.4},
    )
    assert any(o.startswith("synergy:01+02") for o in data["overrides"])


def test_mixed_no_synergy(client):
    """混合经营 05+06（无协同配置）→ 无 synergy override。"""
    data = _assess(
        client,
        {"BASIC_003": "10", "BASIC_008": "300", "01_05": "1500"},
        business_type="MIXED",
        mixed={"05": 0.7, "06": 0.3},
    )
    assert not any(o.startswith("synergy:") for o in data["overrides"])


def test_indicator_admin_api(client, auth_headers):
    """指标管理 API：stats + 列表 + 详情 + 更新（改后还原）。"""
    stats = client.get("/api/v1/admin/indicators/stats", headers=auth_headers).json()
    assert stats["code"] == 200
    assert stats["data"]["total"] >= 4

    lst = client.get("/api/v1/admin/indicators", headers=auth_headers, params={"page": 1, "size": 5}).json()
    assert lst["code"] == 200
    assert lst["data"]["total"] >= 4

    detail = client.get("/api/v1/admin/indicators/BASIC_003", headers=auth_headers).json()
    assert detail["code"] == 200
    assert detail["data"]["code"] == "BASIC_003"

    upd = client.put(
        "/api/v1/admin/indicators/BASIC_003",
        headers=auth_headers,
        json={"weight_star": 4.0},
    ).json()
    assert upd["code"] == 200
    assert upd["data"]["weight_star"] == 4.0
    client.put("/api/v1/admin/indicators/BASIC_003", headers=auth_headers, json={"weight_star": 4.5})


def test_data_source_mapping_present(client, auth_headers):
    """数据源映射表存在且可查询（通过指标详情间接验证表结构）。"""
    db = SessionLocal()
    try:
        from app.models.indicator import DataSourceMapping

        count = db.query(DataSourceMapping).count()
        assert isinstance(count, int)
    finally:
        db.close()
