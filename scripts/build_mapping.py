"""数据-指标映射字典：CMES/CHFS 字段 → 指标体系编码，写入 data_source_mapping。

映射依据（Phase 0 探索结论）：
- CMES 2015 小微企业调查：最贴合目标客群（涉农小微企业），含农业板块 bi* 字段
- CHFS 家庭金融调查 master_hh：家庭层面收入/资产/负债，作为家庭农场代理

字段可信度 reliability（0-1）：来源可靠性 × 完整度 × 时效
- CMES 2015：0.78（企业自报，2015 年）
- CHFS 2021：0.80（家庭金融权威调查，最新）
- CHFS 2015：0.72

多源冲突：conflict_policy = 加权平均（按 reliability）/ 取最大 / 取最小
聚合：aggregation = 加权平均 / 最大 / 加总 / 直接
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.indicator import DataSourceMapping, IndicatorConfig

# ---------- 映射字典 ----------
# (data_source, data_field, indicator_code, transform_rule, aggregation, reliability, conflict_policy, note)
MAPPINGS: list[tuple] = [
    # ===== CMES 2015 小微企业（目标客群最贴合）=====
    # --- 基本项 ---
    ("CMES", "a1006", "BASIC_003", "2015 - a1006", "直接", 0.78, "加权平均", "注册成立年限=调查年-成立年份"),
    ("CMES", "a1006", "BASIC_004", "2015 - a1006", "直接", 0.78, "加权平均", "实际经营年限=调查年-实际经营开始年份"),
    ("CMES", "c1002", "BASIC_005", "直接取值", "直接", 0.80, "加权平均", "从业人员数=目前员工数"),
    ("CMES", "bi3006", "BASIC_008", "万元：bi3006/10000", "直接", 0.78, "加权平均", "年营业收入=去年农产品销售收入"),
    ("CMES", "bi3011", "BASIC_008", "万元：bi3011/10000", "直接", 0.72, "加权平均", "年营业收入=牲畜/水产销售收入"),
    ("CMES", "e1021", "BASIC_019", "万元：e1021/10000", "直接", 0.76, "加权平均", "经营性贷款余额=总贷款金额"),
    ("CMES", "e1014", "BASIC_011", "1/2→无逾期/有逾期", "规则", 0.78, "加权平均", "银行信贷履约记录=是否有未还清贷款"),
    ("CMES", "bi4004", "BASIC_035", "有利润→高占比代理", "规则", 0.68, "加权平均", "绿色/有机产品销售占比代理"),
    # --- 大类 01 农林牧渔业 ---
    ("CMES", "bi2101", "01_05", "直接取值（亩）", "直接", 0.80, "加权平均", "土地/水域经营总面积=土地面积"),
    ("CMES", "bi2101a", "01_05", "直接取值（亩）", "直接", 0.76, "加权平均", "土地/水域经营总面积=流转承包面积"),
    ("CMES", "bi2104", "011_03", "合同期限≥3年→稳定", "规则", 0.74, "加权平均", "种植面积稳定性=流转合同年限代理"),
    ("CMES", "bi2204", "01_07", "赊销/借款→物资投入", "规则", 0.70, "加权平均", "年度种养物资投入代理（有农资赊购）"),
    ("CMES", "bi2212_1", "015_02", "直接取值（亩）", "直接", 0.72, "加权平均", "农机跨区作业面积=机器耕地面积"),
    # --- 小类 0111 谷物种植 ---
    ("CMES", "bi3001_1", "0111_01", "加总：水稻+小麦+玉米+大豆+其他", "加总", 0.80, "加权平均", "主要谷物播种面积=粮经作物面积加总"),
    ("CMES", "bi3001_2", "0111_01", "小麦面积（亩）", "加总", 0.80, "加权平均", "谷物播种面积分量"),
    ("CMES", "bi3001_3", "0111_01", "玉米面积（亩）", "加总", 0.80, "加权平均", "谷物播种面积分量"),
    ("CMES", "bi3001_6", "0111_01", "大豆面积（亩）", "加总", 0.80, "加权平均", "谷物播种面积分量"),
    ("CMES", "bi3001_4", "0111_01", "马铃薯面积（亩）", "加总", 0.78, "加权平均", "谷物播种面积分量"),
    ("CMES", "bi3001_1", "0111_08", "粳稻面积（亩）", "直接", 0.78, "加权平均", "粳稻种植面积=水稻面积"),
    ("CMES", "bi3001_3", "0111_05", "玉米面积（亩）", "直接", 0.80, "加权平均", "玉米种植面积"),
    ("CMES", "bi3001_6", "0112_04", "大豆面积（亩）", "直接", 0.80, "加权平均", "大豆种植面积"),
    ("CMES", "bi3001_7", "0112_06", "花生面积（亩）", "直接", 0.74, "加权平均", "花生种植面积"),
    ("CMES", "bi3001_14", "0114_01", "蔬菜面积（亩）", "直接", 0.76, "加权平均", "蔬菜种植面积分量"),
    ("CMES", "bi3001_15", "0115_01", "水果面积（亩）", "直接", 0.74, "加权平均", "水果种植面积分量"),
    # --- 融资信贷（04/10 类服务类指标）---
    ("CMES", "e1023", "1041_02", "万元：e1023/10000", "直接", 0.76, "加权平均", "涉农贷款余额=最大贷款金额"),
    ("CMES", "e1045", "1041_01", "有民间借款→不良代理", "规则", 0.68, "加权平均", "涉农贷款不良率代理（民间借款依赖）"),

    # ===== CHFS 家庭金融（家庭农场/农户代理）=====
    # --- 基本项 ---
    ("CHFS", "total_income", "BASIC_008", "万元：total_income/10000", "直接", 0.80, "加权平均", "年营业收入=家庭总收入"),
    ("CHFS", "agri_inc", "BASIC_008", "万元：agri_inc/10000", "直接", 0.80, "加权平均", "年营业收入=农业收入"),
    ("CHFS", "busi_inc", "BASIC_008", "万元：busi_inc/10000", "直接", 0.76, "加权平均", "年营业收入=工商业收入"),
    ("CHFS", "agri_debt", "BASIC_019", "万元：agri_debt/10000", "直接", 0.80, "加权平均", "经营性贷款余额=农业负债"),
    ("CHFS", "busi_debt", "BASIC_019", "万元：busi_debt/10000", "直接", 0.76, "加权平均", "经营性贷款余额=工商业负债"),
    ("CHFS", "agri_asset", "01_05", "农业资产→经营规模代理", "规则", 0.74, "加权平均", "土地/水域经营总面积代理（农业资产）"),
    ("CHFS", "land_asset", "01_05", "土地资产→经营规模代理", "规则", 0.74, "加权平均", "土地经营总面积代理（土地资产）"),
    ("CHFS", "agri_debt", "BASIC_010", "万元：agri_debt/10000", "直接", 0.72, "加权平均", "对外担保余额代理（农业负债）"),
    ("CHFS", "total_debt", "BASIC_009", "total_debt/(total_asset+1)*100", "规则", 0.76, "加权平均", "资产负债率=总负债/总资产"),
    ("CHFS", "agri_inc", "BASIC_008", "与 CMES 冲突时按可信度加权", "加权平均", 0.80, "加权平均", "多源融合示例：农业收入"),
]

# 各数据源可信度汇总（用于报告）
SOURCE_RELIABILITY = {"CMES": 0.78, "CHFS": 0.80, "CFPS": 0.70}


def run(db: Session, dry_run: bool = False) -> dict:
    # 校验指标编码
    codes = {c.code for c in db.query(IndicatorConfig.code).all()}
    missing = sorted({m[2] for m in MAPPINGS if m[2] not in codes})
    if missing:
        print(f"[警告] 以下指标编码不存在（已跳过）：{missing}")

    stats = {"CMES": 0, "CHFS": 0}
    for m in MAPPINGS:
        ds, field, code, rule, agg, rel, conflict, note = m
        if code not in codes:
            continue
        stats[ds] = stats.get(ds, 0) + 1
        if dry_run:
            continue
        row = (
            db.query(DataSourceMapping)
            .filter(
                DataSourceMapping.data_source == ds,
                DataSourceMapping.data_field == field,
                DataSourceMapping.indicator_code == code,
            )
            .first()
        )
        if row:
            row.transform_rule = rule
            row.aggregation = agg
            row.reliability = rel
            row.conflict_policy = conflict
            row.active = True
        else:
            db.add(
                DataSourceMapping(
                    data_source=ds,
                    data_field=field,
                    indicator_code=code,
                    transform_rule=rule,
                    aggregation=agg,
                    reliability=rel,
                    conflict_policy=conflict,
                    active=True,
                )
            )
    if not dry_run:
        db.commit()
    return {"total": sum(stats.values()), "by_source": stats}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        dry = "--check-only" in sys.argv
        result = run(db, dry_run=dry)
        print(f"{'[校验] ' if dry else ''}映射字典：共 {result['total']} 条，按数据源 {result['by_source']}")
        if not dry:
            n = db.query(DataSourceMapping).filter(DataSourceMapping.active.is_(True)).count()
            print(f"当前 data_source_mapping 活跃映射：{n} 条")
    finally:
        db.close()
