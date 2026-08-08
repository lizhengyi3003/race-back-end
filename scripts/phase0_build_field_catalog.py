"""Phase 0: 生成各数据源字段清单（变量 code + 中文标签 + 波次）。

扫描 data/raw/{chfs,cmes,cfps} 下所有 .dta，用 StataReader 读取变量标签（不加载全量数据）。
输出：data/samples/field_catalog.csv（source, wave, file, field, label）
字段清单供 Phase 1 映射字典自动预匹配使用。

说明：CFPS 2018/2020/2022 压缩包加密/嵌套（需 Instructions 中的密码），未解压，不在此列。
"""

import sys
from pathlib import Path

import pandas as pd
from pandas.io.stata import StataReader

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "samples" / "field_catalog.csv"


def _iter_dta():
    for src in ("chfs", "cmes", "cfps"):
        d = RAW / src
        if not d.exists():
            continue
        for f in sorted(d.glob("*.dta")):
            yield src, f


def main() -> None:
    rows: list[dict] = []
    for source, f in _iter_dta():
        wave = ""
        # 从文件名推断波次年份
        import re

        m = re.search(r"(20\d\d)", f.name)
        if m:
            wave = m.group(1)
        try:
            with StataReader(f) as r:
                labels = r.variable_labels()
                nobs = getattr(r, "nobs", None)
        except Exception as e:  # noqa: BLE001
            print(f"[错误] {source}/{f.name}: {e}")
            continue
        for field, label in labels.items():
            rows.append(
                {
                    "source": source,
                    "wave": wave,
                    "file": f.name,
                    "field": field,
                    "label": (label or "").strip(),
                    "nobs": nobs or "",
                }
            )
        print(f"[OK] {source}/{f.name}: {len(labels)} 字段, nobs={nobs}")

    df = pd.DataFrame(rows, columns=["source", "wave", "file", "field", "label", "nobs"])
    df = df.drop_duplicates(subset=["source", "wave", "field"])
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\n字段清单: {len(df)} 条 -> {OUT}")
    print(df.groupby("source").size().to_string())


if __name__ == "__main__":
    main()
