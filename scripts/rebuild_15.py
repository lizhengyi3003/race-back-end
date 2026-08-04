"""校赛 15 项体系：生成 10000 条模拟数据 + 正式训练并注册模型"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.init_db import full_init  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.ml.seed import generate_samples  # noqa: E402
from app.ml.training import run_training  # noqa: E402

# 1) 重建数据库表结构（assessment_record 改为 15 项字段）
print("[1/3] 重建数据库表结构（15 项字段）...")
with engine.begin() as conn:
    conn.exec_driver_sql("DROP TABLE IF EXISTS assessment_record")
Base.metadata.create_all(bind=engine)
full_init()

# 2) 生成 10000 条模拟数据并保存 CSV
print("[2/3] 生成 10000 条模拟数据 →", settings.SAMPLE_DIR)
df = generate_samples(10000, seed=42)
Path(settings.SAMPLE_DIR).mkdir(parents=True, exist_ok=True)
df.to_csv(Path(settings.SAMPLE_DIR) / "synthetic_samples.csv", index=False, encoding="utf-8-sig")
print("      违约率:", round(df["default"].mean(), 4), "行数:", len(df))

# 3) 正式训练并注册模型
print("[3/3] 训练 15 项评分卡并注册模型版本...")
db = SessionLocal()
try:
    res = run_training(n_samples=10000, db=db, trained_by="校赛15项重构")
    m = res["metrics"]
    print("      版本:", res["version"])
    print("      AUC:", m["auc"], "KS:", m["ks"], "准确率:", m["accuracy"], "召回率:", m["recall"])
    print("      入模特征数:", res["nFeatures"], "违约率:", m["defaultRate"], "PSI:", m["psi"])
    print(
        "      businessThreshold:", m["businessThreshold"], "评分中心 A:", round(res.get("metrics", {}).get("A", 0), 2)
    )
finally:
    db.close()
