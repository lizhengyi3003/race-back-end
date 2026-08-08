"""Phase 3: 多源样本融合 + 缺失值分层处理。

各数据源是独立调查样本（CMES 企业 / CHFS 家庭 / CFPS 家庭），采用纵向堆叠合并：
- 指标列取并集，缺失为 NaN（评分卡 WOE 分箱会把缺失单独成箱，天然处理）
- 输出 data/samples/fused_samples_v{version}.csv + 缺失率报告
- 高缺失特征（>50%）在报告中标为建议剔除/降权

用法：python fuse_sources.py --version v1
"""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mappings import MODEL_FEATURES, SOURCE_RELIABILITY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN_DIR = ROOT / "data" / "cleaned"
OUT = ROOT / "data" / "samples"


def fuse(version: str) -> Path:
    # glob 所有清洗版本文件（{source}_{wave}_{version}.csv）
    csvs = sorted(CLEAN_DIR.glob(f"*_{version}.csv"))
    if not csvs:
        raise SystemExit(f"无清洗数据（{CLEAN_DIR}/*_{version}.csv）")
    frames = []
    for p in csvs:
        df = pd.read_csv(p)
        src = df["source"].iloc[0] if "source" in df else p.name.split("_")[0]
        df["source_reliability"] = SOURCE_RELIABILITY.get(src, 0.5)
        frames.append(df)
        print(f"  {p.name}: {len(df)} 行")
    if not frames:
        raise SystemExit("无清洗数据")

    fused = pd.concat(frames, ignore_index=True, sort=False)
    # 统一指标列（缺失补 NaN）
    for c in MODEL_FEATURES:
        if c not in fused.columns:
            fused[c] = float("nan")
    print(f"融合样本: {len(fused)} 行, 指标列 {len(MODEL_FEATURES)}")

    # 缺失率报告
    missing = fused[MODEL_FEATURES].isna().mean().round(4)
    report = {
        "version": version,
        "n_rows": int(len(fused)),
        "source_counts": fused["source"].value_counts().to_dict(),
        "feature_missing_rate": missing.to_dict(),
        "high_missing_features": sorted(
            [c for c, r in missing.items() if r > 0.5], key=lambda c: -missing[c]
        ),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    rep = OUT / f"fuse_report_{version}.json"
    rep.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"缺失率报告 -> {rep.name}")

    # 输出融合样本
    out_path = OUT / f"fused_samples_{version}.csv"
    fused.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"融合样本 -> {out_path.name}")
    print("\n各特征缺失率（>0.5 建议剔除/降权）:")
    for c, r in missing.items():
        flag = "  <-- 高缺失" if r > 0.5 else ""
        print(f"  {c}: {r:.2%}{flag}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    version = args.version or ("v" + time.strftime("%Y%m%d%H%M"))
    fuse(version)


if __name__ == "__main__":
    main()
