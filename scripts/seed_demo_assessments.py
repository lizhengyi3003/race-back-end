"""生成演示评估记录：覆盖 10 个经营类型 + 混合经营，含好/中/差/一票否决 四种场景。

用法：python scripts/seed_demo_assessments.py [--clear] [--count N]
- 通过 risk_service.assess_dynamic_and_store 直接落库（不依赖运行中的服务）
- 每个类型一条记录，按经营类型填充合理指标值
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.services.risk_service import assess_dynamic_and_store

# 各经营类型的演示指标值（指标编码 → 值）
SCENARIOS = [
    # 01 农林牧渔业·好
    ("01", "东北粮油种植合作社", {"BASIC_003": "12", "BASIC_004": "12", "BASIC_005": "45", "BASIC_008": "480", "01_05": "2600", "0111_01": "2400", "BASIC_009": "35"}),
    # 01 农林牧渔业·中
    ("01", "富民水稻家庭农场", {"BASIC_003": "5", "BASIC_004": "4", "BASIC_005": "8", "BASIC_008": "90", "01_05": "420", "0111_01": "380", "BASIC_009": "60"}),
    # 02 食用加工·好
    ("02", "黑土地粮油加工有限公司", {"BASIC_003": "15", "BASIC_004": "15", "BASIC_005": "60", "BASIC_008": "900", "BASIC_009": "40"}),
    # 03 非食用加工·中
    ("03", "寒地亚麻制品厂", {"BASIC_003": "8", "BASIC_004": "7", "BASIC_005": "25", "BASIC_008": "220", "BASIC_009": "58"}),
    # 04 生产资料制造·好
    ("04", "黑土农机具制造公司", {"BASIC_003": "18", "BASIC_004": "18", "BASIC_005": "80", "BASIC_008": "1500", "BASIC_009": "30"}),
    # 05 流通服务·中
    ("05", "北粮南运物流站", {"BASIC_003": "6", "BASIC_004": "5", "BASIC_005": "18", "BASIC_008": "350", "BASIC_009": "65"}),
    # 06 科研技术服务·好
    ("06", "寒地作物育种服务站", {"BASIC_003": "10", "BASIC_004": "10", "BASIC_005": "22", "BASIC_008": "300", "BASIC_009": "25"}),
    # 07 教育培训·中
    ("07", "乡村新型职业农民培训中心", {"BASIC_003": "4", "BASIC_004": "3", "BASIC_005": "12", "BASIC_008": "80", "BASIC_009": "55"}),
    # 08 生态环保·差
    ("08", "秸秆综合利用服务队", {"BASIC_003": "2", "BASIC_004": "1", "BASIC_005": "6", "BASIC_008": "45", "BASIC_009": "78"}),
    # 09 休闲观光·好
    ("09", "北大荒冰雪观光农庄", {"BASIC_003": "9", "BASIC_004": "9", "BASIC_005": "35", "BASIC_008": "600", "BASIC_009": "42"}),
    # 10 其他支持服务·差
    ("10", "乡村电商服务点", {"BASIC_003": "1", "BASIC_004": "1", "BASIC_005": "3", "BASIC_008": "30", "BASIC_009": "82"}),
    # 混合经营 01+02（触发协同因子）
    ("MIXED", "种养加工一体化合作社", {"BASIC_003": "10", "BASIC_004": "10", "BASIC_005": "40", "BASIC_008": "700", "BASIC_009": "38"}, {"01": 0.6, "02": 0.4}),
    # 一票否决（失信被执行人）
    ("01", "星月农机租赁户", {"BASIC_003": "6", "BASIC_004": "5", "BASIC_005": "9", "BASIC_008": "120", "01_05": "300", "BASIC_013": "是"}),
]


def run(db, clear: bool = False) -> list[dict]:
    if clear:
        from app.models.assessment import AssessmentRecord
        from app.models.indicator import IndicatorValue

        db.query(IndicatorValue).delete()
        db.query(AssessmentRecord).delete()
        db.commit()
        print("已清空评估记录")
    results = []
    for i, item in enumerate(SCENARIOS):
        business_type, name, indicators = item[0], item[1], item[2]
        mixed = item[3] if len(item) > 3 else None
        payload = {
            "enterpriseName": name,
            "businessType": business_type,
            "productType": "",
            "indicators": indicators,
        }
        if mixed:
            payload["mixedBusiness"] = mixed
        result = assess_dynamic_and_store(db, payload, assessor_name="seed-demo")
        results.append(
            {
                "name": name,
                "type": business_type,
                "score": result["score"],
                "level": result["level"],
                "overrides": result.get("overrides", []),
            }
        )
    return results


if __name__ == "__main__":
    db = SessionLocal()
    try:
        clear = "--clear" in sys.argv
        results = run(db, clear=clear)
        print(f"✅ 生成 {len(results)} 条演示评估记录")
        for r in results:
            ov = (" | " + "; ".join(r["overrides"])) if r["overrides"] else ""
            print(f"  {r['type']:6s} {r['name']:24s} score={r['score']:4d} {r['level']}{ov}")
    finally:
        db.close()
