"""种子：business_type_config —— 10 个大类 + MIXED 的层级权重与混合经营协同因子。

层级基础权重（与 expert_engine 默认一致，可按业务微调）：
- 基本项 0.35 > 大类 0.28 > 中类 0.22 > 小类 0.15
协同因子（混合经营 v1 基础因子，Phase 4 完善）：
- 01+02 种植+食用加工 → 产销一体 ×1.06
- 01+08 种植+生态环保 → 生态循环 ×1.05
- 01+04 种植+生产资料 → 农资一体化 ×1.04
- 02+05 加工+流通 → 供应链闭环 ×1.04
- MIXED 通用：1.00（无叠加）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.indicator import BusinessTypeConfig, IndicatorCategory

# 默认层级权重（全部业务统一，可后续在管理端微调）
DEFAULT_LEVEL_WEIGHTS = {"基本项": 0.35, "大类": 0.28, "中类": 0.22, "小类": 0.15}

# 协同因子：key = "codeA+codeB"（升序），factor>1 为加成
SYNERGY_FACTORS: dict[str, dict] = {
    "01+02": {"factor": 1.06, "name": "种植+食用加工·产销一体"},
    "01+04": {"factor": 1.04, "name": "种植+生产资料·农资一体化"},
    "01+08": {"factor": 1.05, "name": "种植+生态环保·生态循环"},
    "01+05": {"factor": 1.04, "name": "种植+流通·产销衔接"},
    "02+05": {"factor": 1.04, "name": "加工+流通·供应链闭环"},
    "03+05": {"factor": 1.03, "name": "非食用加工+流通·原料直达"},
    "04+01": {"factor": 1.04, "name": "生产资料+种植·农资一体化"},
}

# 各业务可叠加的区域加成（东北特色）
REGION_BOOST = {"东北": 1.03, "全国": 1.0}


def run(db, dry_run: bool = False) -> dict:
    cats = db.query(IndicatorCategory).filter(IndicatorCategory.level == "大类").all()
    created, updated = 0, 0
    for cat in cats:
        row = (
            db.query(BusinessTypeConfig)
            .filter(BusinessTypeConfig.business_type_code == cat.code)
            .first()
        )
        payload = dict(
            name=cat.name,
            level_weights=dict(DEFAULT_LEVEL_WEIGHTS),
            feature_boost=1.1,
            region_boost=dict(REGION_BOOST),
            synergy_factors={},
            active=True,
        )
        if dry_run:
            created += 1
            continue
        if row:
            # 保留已配置的协同因子，仅补齐默认
            for k, v in payload.items():
                if not getattr(row, k):
                    setattr(row, k, v)
            updated += 1
        else:
            db.add(BusinessTypeConfig(business_type_code=cat.code, **payload))
            created += 1

    # MIXED 通用配置 + 协同因子
    mixed = db.query(BusinessTypeConfig).filter(BusinessTypeConfig.business_type_code == "MIXED").first()
    if not mixed:
        db.add(
            BusinessTypeConfig(
                business_type_code="MIXED",
                name="混合经营",
                level_weights=dict(DEFAULT_LEVEL_WEIGHTS),
                feature_boost=1.1,
                region_boost=dict(REGION_BOOST),
                synergy_factors=SYNERGY_FACTORS,
                active=True,
            )
        )
        created += 1
    elif mixed and not mixed.synergy_factors:
        mixed.synergy_factors = SYNERGY_FACTORS
        updated += 1

    if not dry_run:
        db.commit()
    return {"created": created, "updated": updated, "synergy": len(SYNERGY_FACTORS)}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        dry = "--check-only" in sys.argv
        r = run(db, dry_run=dry)
        print(f"{'[校验] ' if dry else ''}business_type_config：新建 {r['created']}，更新 {r['updated']}，协同因子 {r['synergy']} 个")
        if not dry:
            total = db.query(BusinessTypeConfig).filter(BusinessTypeConfig.active.is_(True)).count()
            print(f"当前活跃业务配置：{total} 个")
    finally:
        db.close()
