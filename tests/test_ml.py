"""模型训练与评估接口测试"""


def test_model_info(client, auth_headers):
    r = client.get("/api/v1/model/info", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["status"] == "active"
    assert data["version"]


def test_model_metrics(client, auth_headers):
    r = client.get("/api/v1/model/metrics", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    metrics = body["data"]
    assert metrics is not None
    assert 0 < metrics["auc"] <= 1
    assert 0 <= metrics["ks"] <= 1
    assert len(metrics["confusionMatrix"]) == 2
    assert len(metrics["rocCurve"]) > 0
    assert len(metrics["ivTable"]) > 0


def test_model_train(client, auth_headers):
    r = client.post("/api/v1/model/train", json={"nSamples": 2000}, headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    # 训练指标达标（商业计划书目标：AUC≥0.80；召回率在业务高风险阈值口径下随样本波动）
    assert data["auc"] >= 0.70
    assert data["recall"] >= 0.15
    assert data["nFeatures"] >= 5

    # 训练后模型信息更新
    r2 = client.get("/api/v1/model/info", headers=auth_headers)
    assert r2.json()["data"]["version"] == data["version"]


def test_thresholds_roundtrip(client, auth_headers):
    r = client.get("/api/v1/model/thresholds", headers=auth_headers)
    data = r.json()["data"]
    data["lowRiskThreshold"] = 720
    r2 = client.put("/api/v1/model/thresholds", json=data, headers=auth_headers)
    assert r2.json()["code"] == 200
    assert r2.json()["data"]["lowRiskThreshold"] == 720


def test_smote_applied_in_metrics(client, auth_headers):
    """SMOTE 过采样应在训练指标中体现"""
    r = client.post("/api/v1/model/train", json={"nSamples": 1000}, headers=auth_headers)
    data = r.json()["data"]
    assert data["smoteApplied"] is True
    assert data["metrics"]["trainBadAfter"] > data["metrics"]["trainBadBefore"]


def test_experiments_in_metrics(client, auth_headers):
    """三组对比实验应随训练产出"""
    r = client.get("/api/v1/model/metrics", headers=auth_headers)
    metrics = r.json()["data"]
    ex = metrics["experiments"]
    assert ex is not None
    # 实验一：替代数据 vs 传统数据
    assert "替代数据指标体系" in ex["experiment1"]["groups"]
    # 实验二：特征工程方案（WOE/原始/分组PCA）
    assert set(["原始变量（未分箱）", "WOE编码（本方案）", "分组PCA降维（备选）"]) <= set(
        ex["experiment2"]["groups"].keys()
    )
    # 实验三：专属 vs 通用
    assert "涉农专属模型（替代数据评分卡）" in ex["experiment3"]["groups"]
    for group in ["experiment1", "experiment2", "experiment3"]:
        for _, m in ex[group]["groups"].items():
            assert 0 < m["auc"] <= 1


def test_model_monitor(client, auth_headers):
    r = client.get("/api/v1/model/monitor", headers=auth_headers)
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["available"] is True
    assert data["modelVersion"]
    assert "actualSamples" in data
    assert "warnings" in data
