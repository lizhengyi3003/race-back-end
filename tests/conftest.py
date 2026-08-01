"""pytest 全局配置：使用独立临时 SQLite 数据库，避免污染开发数据"""

import os
import sys
import tempfile
from pathlib import Path

# 必须在导入 app 模块前设置环境变量
_tmpdir = tempfile.mkdtemp(prefix="race_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["AUTO_TRAIN_ON_STARTUP"] = "false"
os.environ["MODEL_DIR"] = f"{_tmpdir}/models"
os.environ["SAMPLE_DIR"] = f"{_tmpdir}/samples"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.init_db import full_init  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.ml.training import run_training  # noqa: E402

# 单测样本（优质客户）
SAMPLE_INPUT = {
    "enterpriseName": "测试农场",
    "businessType": "种植",
    "productType": "玉米",
    "age": 48,
    "education": "初中",
    "familyMembers": 4,
    "landConfirmedArea": 800,
    "landTransferYears": 8,
    "plantingStructure": "主粮种植",
    "landUtilization": 92,
    "grainSubsidy": 42000,
    "machinerySubsidy": 26000,
    "otherSubsidy": 8000,
    "insuranceCoverage": 95,
    "claimCount": 0,
    "claimAmount": 0,
    "claimRatio": 3,
    "yearsOperating": 12,
    "businessConcentration": 82,
    "annualRevenue": 160,
    "revenueStability": "稳定",
    "creditStatus": "无不良记录",
    "loanHistory": 3,
    "loanOverdueHistory": 0,
}


@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """初始化测试库 + 训练一个小模型"""
    full_init()
    db = SessionLocal()
    try:
        run_training(n_samples=800, db=db, trained_by="test")
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def token(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.json()["code"] == 200
    return r.json()["data"]["token"]


@pytest.fixture()
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
