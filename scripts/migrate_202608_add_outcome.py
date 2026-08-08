"""幂等迁移：assessment_record 增加真实回测 outcome 字段（2026-08-09）。

用法：python scripts/migrate_202608_add_outcome.py
可重复执行；列已存在则跳过。
"""

from sqlalchemy import text

from app.db.session import engine

COLUMNS = [
    ("outcome", "VARCHAR(16) NOT NULL DEFAULT 'pending'"),
    ("outcome_note", "VARCHAR(255) NULL"),
    ("outcome_at", "DATETIME NULL"),
]


def main() -> None:
    with engine.begin() as conn:
        for col, ddl in COLUMNS:
            exists = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'assessment_record' "
                    "AND COLUMN_NAME = :c"
                ),
                {"c": col},
            ).scalar()
            if not exists:
                conn.execute(text(f"ALTER TABLE assessment_record ADD COLUMN {col} {ddl}"))
                print(f"  ADD assessment_record.{col} {ddl}")
            else:
                print(f"  exists assessment_record.{col}")
    print("迁移完成")


if __name__ == "__main__":
    main()
