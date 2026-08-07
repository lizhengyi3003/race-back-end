"""校准关键数值指标的 scoring_config（参考上限 max + 越低越好 lower_better）。

专家引擎对数值指标默认 ref_max=100，导致年限/营收/面积等指标被系统性低估。
本脚本为 775 项中最具判别力的数值/枚举指标配置合理参考上限（领域经验值），
改善动态评分质量。幂等：对列出的编码总是覆盖为校准值。

用法：python scripts/fix_scoring_config.py [--check-only]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal
from app.models.indicator import IndicatorConfig

# 数值指标：code → {"max": 参考上限, "lower_better": 是否越低越好}
NUMERIC_CONFIG: dict[str, dict] = {
    # ---- 基本项 ----
    "BASIC_003": {"max": 30},  # 注册成立年限（年）
    "BASIC_004": {"max": 30},  # 实际经营年限（年）
    "BASIC_005": {"max": 100},  # 从业人员数（人）
    "BASIC_008": {"max": 500},  # 年营业收入（万元）
    "BASIC_009": {"max": 100, "lower_better": True},  # 资产负债率（%）
    "BASIC_010": {"max": 300},  # 对外担保余额（万元）
    "BASIC_018": {"max": 5, "lower_better": True},  # 个人征信近2年逾期次数
    "BASIC_019": {"max": 500},  # 个人经营性贷款余额（万元）
    "BASIC_020": {"max": 300},  # 个人对外担保余额（万元）
    "BASIC_021": {"max": 5},  # 信用意识评分（1-5 分）
    "BASIC_025": {"max": 100000},  # 耕地地力保护补贴金额（元）
    "BASIC_026": {"max": 100},  # 农业保险保费财政补贴比例（%）
    "BASIC_028": {"max": 15},  # 农业保险投保年限（年）
    "BASIC_029": {"max": 5, "lower_better": True},  # 历史保险理赔频次（次）
    "BASIC_030": {"max": 3, "lower_better": True},  # 现金流季节性波动系数（倍）
    "BASIC_035": {"max": 100},  # 绿色/有机/地标产品销售占比（%）
    "BASIC_036": {"max": 5000},  # 月均用电量（度）
    # ---- 大类 01 农林牧渔业 ----
    "01_02": {"max": 5000},  # 主要农产品年产量（吨）
    "01_05": {"max": 3000},  # 土地/水域经营总面积（亩）
    "01_07": {"max": 300},  # 年度种养物资投入（万元）
    "01_09": {"max": 100},  # 规模化/设施化经营占比（%）
    # ---- 小类 0111 谷物种植 ----
    "0111_01": {"max": 3000},  # 主要谷物播种面积（亩）
    "0111_03": {"max": 1000},  # 玉米单产水平（公斤/亩）
    "0111_05": {"max": 2000},  # 玉米种植面积（亩）
    "0111_08": {"max": 1500},  # 粳稻种植面积（亩）
    "0111_09": {"max": 800},  # 谷物单产水平（公斤/亩）
    "0112_04": {"max": 1000},  # 大豆种植面积（亩）
    "0114_01": {"max": 1000},  # 蔬菜种植面积（亩）
    # ---- 金融服务类 ----
    "1041_01": {"max": 100, "lower_better": True},  # 涉农贷款不良率（%）
    "1041_02": {"max": 5000},  # 涉农贷款余额（万元）
    "104_01": {"max": 5000},  # 涉农贷款/服务规模（万元）
}

# 枚举指标档位映射：code → {"map": {选项: 得分}}
ENUM_CONFIG: dict[str, dict] = {
    "BASIC_011": {"map": {"无逾期": 100, "逾期已结清": 60, "有逾期": 15}},  # 银行信贷履约记录
    "BASIC_022": {"map": {"好": 100, "中": 60, "差": 20}},  # 社区/村镇口碑
    "BASIC_023": {"map": {"无": 100, "轻度": 60, "明显": 15}},  # 经营者不良嗜好情况
    "BASIC_024": {"map": {"正常到账": 100, "延迟": 55, "未到账": 20}},  # 涉农补贴到账情况
    "BASIC_031": {"map": {"已认证": 100, "申报中": 60, "无": 25}},  # 绿色食品认证
    "BASIC_032": {"map": {"已认证": 100, "申报中": 60, "无": 25}},  # 有机产品认证
    "BASIC_033": {"map": {"国家级地理标志": 100, "省级地理标志": 80, "无": 25}},  # 农产品地理标志
    "01_06": {"map": {"低": 90, "中": 55, "高": 15}},  # 寒地低温冻害风险等级
    "01_10": {"map": {"无": 100, "轻": 75, "中": 50, "重": 15}},  # 近三年自然灾害受灾程度
}


def run(db, dry_run: bool = False) -> dict:
    updated = 0
    for code, cfg in {**NUMERIC_CONFIG, **ENUM_CONFIG}.items():
        c = db.query(IndicatorConfig).filter(IndicatorConfig.code == code).first()
        if not c:
            continue
        if dry_run:
            updated += 1
            continue
        c.scoring_config = cfg
        updated += 1
    if not dry_run:
        db.commit()
    return {"updated": updated, "numeric": len(NUMERIC_CONFIG), "enum": len(ENUM_CONFIG)}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        dry = "--check-only" in sys.argv
        r = run(db, dry_run=dry)
        print(f"{'[校验] ' if dry else ''}校准 {r['updated']} 个指标（数值 {r['numeric']} + 枚举 {r['enum']}）")
    finally:
        db.close()
