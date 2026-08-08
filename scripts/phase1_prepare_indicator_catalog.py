"""Phase 1 准备: 从 indicator_dump.sql 解析指标清单（code + name + level + category）。

输出 data/samples/indicator_catalog.csv，供自动预匹配脚本使用。
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMP = ROOT / "data" / "indicator_dump.sql"
OUT = ROOT / "data" / "samples" / "indicator_catalog.csv"


def _split_sql_vals(s: str) -> list[str]:
    """按逗号分割 SQL VALUES 行，跳过单引号内的逗号，剥离引号（NULL 保持为空串）。"""
    parts: list[str] = []
    cur = ""
    in_q = False
    for ch in s:
        if ch == "'":
            in_q = not in_q
            cur += ch
        elif ch == "," and not in_q:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip().strip("'") for p in parts]


def main() -> None:
    text = DUMP.read_text(encoding="utf-8")
    if "INSERT INTO `indicator_config`" not in text:
        print("未找到 indicator_config INSERT")
        return
    cols = []
    rows = []
    for line in text.splitlines():
        if "INSERT INTO `indicator_config`" not in line or "VALUES (" not in line:
            continue
        # 表头：INSERT INTO `indicator_config` (`id`,`code`,...)
        h = line.find("(`")
        if h >= 0 and not cols:
            k = line.find(")", h)
            if k > h:
                cols = [c.strip().strip("`") for c in line[h + 1 : k].split(",")]
        # 数据：VALUES (...) 取最后一对括号
        v = line.find("VALUES (")
        e = line.rfind(");")
        if v < 0 or e < 0:
            continue
        vals = _split_sql_vals(line[v + len("VALUES (") : e])
        if not cols or "code" not in cols or len(vals) <= cols.index("category_code"):
            continue
        rows.append(
            {
                "code": vals[cols.index("code")],
                "name": vals[cols.index("name")],
                "level": vals[cols.index("level")],
                "category": vals[cols.index("category_code")],
            }
        )
    if not cols:
        print("未找到 indicator_config INSERT 表头")
        return

    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["code", "name", "level", "category"])
        w.writeheader()
        w.writerows(rows)

    print(f"指标清单: {len(rows)} 条 -> {OUT}")
    from collections import Counter

    print("层级分布:", dict(Counter(r["level"] for r in rows)))
    print("示例:", rows[:3])


if __name__ == "__main__":
    main()
