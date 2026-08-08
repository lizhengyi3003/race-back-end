"""一次性迁移：彻底下线 15 项传统表单（2026-08）。

开发阶段不再保留 15 项传统评估（v1.0 表单）及其数据：
1. 删除 15 项传统评估记录（input_json 无 `indicators` 键的旧表单记录）
2. DROP COLUMN 15 项 ORM 字段列（land_confirmed_area 等）

用法（在 back-end 目录、激活 .venv）：
    python scripts/migrate_202608_drop_legacy.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.db.session import engine

LEGACY_COLUMNS = [
    "land_confirmed_area",
    "land_transfer_years",
    "land_transfer_stability",
    "black_soil_protection",
    "grain_subsidy",
    "machinery_subsidy",
    "grain_scale_subsidy",
    "specialty_crop_subsidy",
    "insurance_years",
    "claim_count",
    "facility_insurance",
    "years_operating",
    "purchase_order",
    "annual_revenue",
    "credit_record",
]


def _columns(conn) -> set[str]:
    rows = conn.execute(text("SHOW COLUMNS FROM assessment_record"))
    return {r[0] for r in rows}


def main() -> None:
    with engine.begin() as conn:
        # 1) 删除 15 项传统评估记录（动态记录 input_json 均含 indicators 键）
        legacy_cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM assessment_record "
                "WHERE JSON_EXTRACT(input_json, '$.indicators') IS NULL"
            )
        ).scalar()
        if legacy_cnt:
            conn.execute(
                text(
                    "DELETE FROM assessment_record "
                    "WHERE JSON_EXTRACT(input_json, '$.indicators') IS NULL"
                )
            )
            print(f"[OK] 已删除 {legacy_cnt} 条 15 项传统评估记录")
        else:
            print("[SKIP] 无 15 项传统评估记录")

        # 2) 删除 15 项 ORM 字段列（幂等）
        cols = _columns(conn)
        dropped = 0
        for col in LEGACY_COLUMNS:
            if col in cols:
                conn.execute(text(f"ALTER TABLE assessment_record DROP COLUMN `{col}`"))
                dropped += 1
        if dropped:
            print(f"[OK] 已删除 {dropped} 个 15 项字段列")
        else:
            print("[SKIP] 15 项字段列均已不存在")

        # 3) 校验：当前剩余记录数
        remain = conn.execute(text("SELECT COUNT(*) FROM assessment_record")).scalar()
        print(f"[INFO] assessment_record 当前剩余 {remain} 条记录")


if __name__ == "__main__":
    main()
