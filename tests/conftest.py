"""pytest 全局配置：使用独立 MySQL 测试库（race_test），避免污染开发数据。

前置条件：本地 Docker MySQL 已启动
  docker compose -f docker-compose.yml -f docker-compose.local.yml up -d mysql
（映射 127.0.0.1:3307，root/race123456）
"""

import os
import sys
import tempfile
from pathlib import Path

import pymysql

# 必须在导入 app 模块前：创建独立测试库并设置环境变量
_MYSQL_HOST = "127.0.0.1"
_MYSQL_PORT = 3307
_MYSQL_USER = "root"
_MYSQL_PASS = "race123456"
_TEST_DB = "race_test"

try:
    _conn = pymysql.connect(
        host=_MYSQL_HOST, port=_MYSQL_PORT, user=_MYSQL_USER, password=_MYSQL_PASS, charset="utf8mb4"
    )
except Exception as exc:  # noqa: BLE001
    raise RuntimeError(
        "无法连接本地 Docker MySQL（127.0.0.1:3307），请先启动：\n"
        "  docker compose -f docker-compose.yml -f docker-compose.local.yml up -d mysql"
    ) from exc
try:
    with _conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {_TEST_DB}")
        cur.execute(f"CREATE DATABASE {_TEST_DB} DEFAULT CHARACTER SET utf8mb4")
    _conn.commit()
finally:
    _conn.close()

_tmpdir = tempfile.mkdtemp(prefix="race_test_")
os.environ["DATABASE_URL"] = (
    f"mysql+pymysql://{_MYSQL_USER}:{_MYSQL_PASS}@{_MYSQL_HOST}:{_MYSQL_PORT}/{_TEST_DB}?charset=utf8mb4"
)
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

# 单测样本（动态指标体系：基本项 + 大类 01 指标，供造数用）
SAMPLE_INPUT = {
    "enterpriseName": "测试农场",
    "businessType": "01",
    "selectedCategories": [],
    "mixedBusiness": {},
    "indicators": {
        "BASIC_003": "10",
        "BASIC_008": "200",
        "01_05": "500",
    },
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
