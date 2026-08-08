"""Phase 2: 每个数据源独立清洗 + 版本化输出。

流程：
1. 读取数据源 dta（按 SOURCE_FIELDS 最小化字段）
2. 对 MAPPINGS 中该源的所有映射，用 clean_engine 执行 clean_rule → 生成指标列
3. 输出 data/cleaned/{source}_v{version}.csv（不可变版本）
4. 输出清洗报告 data/cleaned/report_{source}_v{version}.json（覆盖率/缺失率/样本量）
5. 清洗版本元数据追加到 data/cleaned/versions.json（文件级版本管理）

用法：python clean_sources.py [--sources CMES,CHFS,CFPS] [--version v1]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_engine import eval_rule  # noqa: E402
from mappings import MAPPINGS, SOURCE_FIELDS, SOURCE_FILES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN_DIR = ROOT / "data" / "cleaned"


def _default_version() -> str:
    return "v" + time.strftime("%Y%m%d%H%M")


def _wave_label(path: str, wave: str) -> str:
    m = re.search(r"(20\d\d)", Path(path).name)
    return m.group(1) if m else wave


def clean_file(source: str, wave: str, path: str, version: str) -> Path | None:
    full = ROOT / path
    if not full.exists():
        print(f"[跳过] {source}/{path} 不存在")
        return None

    fields_needed = SOURCE_FIELDS[source].get(wave, [])
    print(f"读取 {source} {wave}: {full.name}（{len(fields_needed)} 字段）...")
    try:
        df = pd.read_stata(full, columns=fields_needed, convert_categoricals=False)
    except Exception as e:  # noqa: BLE001
        print(f"[错误] {source}/{wave} 读取失败: {e}")
        return None
    print(f"  样本 {len(df)} 行")

    # 执行映射（按 wave 匹配）
    out = pd.DataFrame(index=df.index)
    applied = 0
    for src, field, code, mtype, rule, rel, agg, note, wv in MAPPINGS:
        if src != source or wv != wave:
            continue
        try:
            out[code] = eval_rule(rule, df)
            applied += 1
        except Exception as e:  # noqa: BLE001
            print(f"[规则错误] {source}.{field}->{code}: {rule} => {e}")
    out["source"] = source
    out["source_wave"] = wave
    out["source_version"] = version

    # 异常值处理：数值列超出 [P1, P99] 截断
    num_cols = [c for c in out.columns if c not in ("source", "source_wave", "source_version")]
    for c in num_cols:
        s = out[c]
        if s.dtype.kind not in "fi":
            continue
        lo, hi = s.quantile(0.01), s.quantile(0.99)
        out[c] = s.clip(lo, hi)

    # 输出清洗版本文件（按波次区分文件名）
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    label = _wave_label(path, wave)
    out_path = CLEAN_DIR / f"{source}_{label}_{version}.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  清洗完成: {applied} 规则, {len(num_cols)} 指标列 -> {out_path.name}")

    # 清洗报告
    report = {
        "source": source,
        "wave": wave,
        "version": version,
        "n_rows": int(len(out)),
        "n_features": len(num_cols),
        "missing_rate": {c: round(float(out[c].isna().mean()), 4) for c in num_cols},
    }
    rep_path = CLEAN_DIR / f"report_{source}_{label}_{version}.json"
    rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  报告: {rep_path.name}")

    # 文件级版本元数据
    versions_path = CLEAN_DIR / "versions.json"
    records = json.loads(versions_path.read_text(encoding="utf-8")) if versions_path.exists() else []
    records.append(
        {
            "source": source,
            "wave": wave,
            "version": version,
            "file": out_path.name,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mapping_count": applied,
        }
    )
    versions_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="CMES,CHFS,CFPS")
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    version = args.version or _default_version()
    for s in args.sources.split(","):
        s = s.strip().upper()
        if s not in SOURCE_FILES:
            print(f"[跳过] 未知数据源: {s}")
            continue
        for wave, path in SOURCE_FILES[s]:
            clean_file(s, wave, path, version)


if __name__ == "__main__":
    main()
