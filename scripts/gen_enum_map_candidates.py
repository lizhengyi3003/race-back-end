"""辅助工具：为缺失 scoring_config.map 的枚举指标生成候选分值映射（供人工审核）。

- 只读不写库：输出 data/enum_map_candidates.csv（code/name/value_range/options/候选map/依据）
- 复用 import_indicators 的 parse_enum_options / build_enum_map 逻辑
用法：python scripts/gen_enum_map_candidates.py
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from sqlalchemy import text  # noqa: E402

from app.db.session import engine  # noqa: E402

from import_indicators import build_enum_map, parse_enum_options  # noqa: E402


def main() -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT code, name, value_range FROM indicator_config "
                "WHERE (value_range LIKE '%/%' OR value_range LIKE '%、%' OR value_range LIKE '%／%') "
                "AND (scoring_config IS NULL OR JSON_EXTRACT(scoring_config, '$.map') IS NULL)"
            )
        ).fetchall()
    print(f"无 map 的枚举指标: {len(rows)}")

    out = ROOT / "data" / "enum_map_candidates.csv"
    generated = skipped = 0
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "value_range", "options", "candidate_map", "依据"])
        for code, name, vr in rows:
            opts = parse_enum_options(vr or "")
            if not opts or len(opts) < 2:
                skipped += 1
                continue
            cand = build_enum_map(opts, name or "")
            if cand is None:
                skipped += 1
                w.writerow([code, name, vr, " / ".join(opts), "", "中性/无配置"])
                continue
            generated += 1
            w.writerow([code, name, vr, " / ".join(opts), json.dumps(cand, ensure_ascii=False), "启发生成（需人工审核）"])
    print(f"可生成候选: {generated}  中性跳过: {skipped}")
    print(f"输出: {out}")


if __name__ == "__main__":
    main()
