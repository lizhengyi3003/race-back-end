"""一次性迁移：评估记录表 assessment_record 结构调整（2026-08）。

1. ADD COLUMN user_id（归属用户，可空）—— 历史评估记录归属当前账号用
2. 回填归属：按 assessor_name（用户名）关联 sys_user.username，找不到的保持 NULL
3. DROP COLUMN product_type —— 主营产品已整体下线（测试阶段，无需兼容旧数据）
4. 为 user_id 建索引

用法（在 back-end 目录、激活 .venv）：
    python scripts/migrate_202608_assessment.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.db.session import engine


def _columns(conn) -> set[str]:
    rows = conn.execute(text("SHOW COLUMNS FROM assessment_record"))
    return {r[0] for r in rows}


def _indexes(conn) -> set[str]:
    rows = conn.execute(text("SHOW INDEX FROM assessment_record"))
    return {r[2] for r in rows}


def main() -> None:
    with engine.begin() as conn:
        # 1) 加 user_id 列（幂等）
        cols = _columns(conn)
        if "user_id" not in cols:
            conn.execute(text("ALTER TABLE assessment_record ADD COLUMN user_id INTEGER NULL"))
            print("[OK] 已添加 user_id 列")
        else:
            print("[SKIP] user_id 列已存在")

        # 2) 回填归属：assessor_name -> sys_user.username
        conn.execute(
            text(
                "UPDATE assessment_record r "
                "LEFT JOIN sys_user u ON u.username = r.assessor_name "
                "SET r.user_id = u.id "
                "WHERE r.user_id IS NULL AND u.id IS NOT NULL"
            )
        )
        print("[OK] 已按 assessor_name 回填 user_id（未匹配用户保持 NULL）")

        # 3) 删除 product_type 列（主营产品整体下线）
        cols = _columns(conn)
        if "product_type" in cols:
            conn.execute(text("ALTER TABLE assessment_record DROP COLUMN product_type"))
            print("[OK] 已删除 product_type 列")
        else:
            print("[SKIP] product_type 列不存在")

        # 4) user_id 索引
        idxs = _indexes(conn)
        if "ix_assessment_record_user_id" not in idxs:
            conn.execute(
                text("CREATE INDEX ix_assessment_record_user_id ON assessment_record(user_id)")
            )
            print("[OK] 已创建 user_id 索引")
        else:
            print("[SKIP] user_id 索引已存在")

    print("=" * 50)
    print("迁移完成：assessment_record 已增加 user_id 归属、移除 product_type")


if __name__ == "__main__":
    main()
