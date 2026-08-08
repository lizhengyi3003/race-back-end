"""核心映射字典（Phase 1/2）：数据源字段 → 模型指标，含可执行清洗规则。

每个映射元组：
(source, field, indicator_code, mapping_type, clean_rule, reliability, aggregation, note)

clean_rule 为可执行表达式（由 clean_engine 解析执行）：
- {field}      引用数据源字段（缺失为 NaN）
- 算术         + - * / （如 2015-{a1006}）
- clip(x,lo,hi) 截断
- sum(a,b,...)  加总（缺失按 0）
- div(x,n)      除以 n
- map(x,{1:1,2:0}) 枚举映射（缺失保持 NaN）
- coalesce(x,y,...) 依次取首个非空
- fill(x,y)     x 缺失用 y
- mask(x,cond)  按布尔条件掩码
- int(x)       取整
mapping_type: direct（直接）/ proxy（代理）/ derived（派生）/ label（标签辅助）
aggregation: 直接 / 加权平均（多源融合用）
"""

# (source, field, indicator_code, mapping_type, clean_rule, reliability, aggregation, note, wave)
MAPPINGS: list[tuple] = [
    # ============ CMES 2015（小微企业调查，已验证）============
    ("CMES", "a1006", "BASIC_003", "derived", "clip(2015-{a1006},0,60)", 0.78, "直接", "注册成立年限", "all"),
    ("CMES", "a1006", "BASIC_004", "derived", "clip(2015-{a1006},0,60)", 0.78, "直接", "实际经营年限", "all"),
    ("CMES", "c1002", "BASIC_005", "direct", "fill({c1002},0)", 0.80, "直接", "从业人员数", "all"),
    ("CMES", "bi3006", "BASIC_008", "derived", "div(sum({bi3006},{bi3011}),10000)", 0.78, "加权平均", "农产品+畜牧销售收入→年营收(万元)", "all"),
    ("CMES", "bi3011", "BASIC_008", "derived", "div(sum({bi3006},{bi3011}),10000)", 0.72, "加权平均", "同上（第二来源）", "all"),
    ("CMES", "bi2101", "01_05", "direct", "fill({bi2101},{bi2101a})", 0.80, "加权平均", "土地面积(亩)", "all"),
    ("CMES", "bi2101a", "01_05", "direct", "fill({bi2101},{bi2101a})", 0.74, "加权平均", "流转承包面积(亩)", "all"),
    ("CMES", "bi3001_1", "0111_01", "derived", "sum({bi3001_1},{bi3001_2},{bi3001_3},{bi3001_4},{bi3001_6})", 0.80, "加权平均", "谷物播种面积(加总)", "all"),
    ("CMES", "bi3001_2", "0111_01", "derived", "sum({bi3001_1},{bi3001_2},{bi3001_3},{bi3001_4},{bi3001_6})", 0.80, "加权平均", "", "all"),
    ("CMES", "bi3001_3", "0111_01", "derived", "sum({bi3001_1},{bi3001_2},{bi3001_3},{bi3001_4},{bi3001_6})", 0.80, "加权平均", "", "all"),
    ("CMES", "bi3001_4", "0111_01", "derived", "sum({bi3001_1},{bi3001_2},{bi3001_3},{bi3001_4},{bi3001_6})", 0.80, "加权平均", "", "all"),
    ("CMES", "bi3001_6", "0111_01", "derived", "sum({bi3001_1},{bi3001_2},{bi3001_3},{bi3001_4},{bi3001_6})", 0.80, "加权平均", "", "all"),
    ("CMES", "bi3001_3", "0111_05", "direct", "{bi3001_3}", 0.80, "直接", "玉米面积", "all"),
    ("CMES", "bi3001_1", "0111_08", "direct", "{bi3001_1}", 0.78, "直接", "粳稻面积", "all"),
    ("CMES", "bi3001_6", "0112_04", "direct", "{bi3001_6}", 0.78, "直接", "大豆面积", "all"),
    ("CMES", "e1021", "BASIC_019", "derived", "div({e1021},10000)", 0.76, "加权平均", "总贷款金额(万元)", "all"),
    ("CMES", "e1023", "1041_02", "derived", "div({e1023},10000)", 0.74, "直接", "最大贷款金额(万元)", "all"),
    ("CMES", "e1014", "_cmes_had_loan", "label", "map({e1014},{1:1,2:0})", 0.78, "直接", "是否有未还清贷款", "all"),
    ("CMES", "bi4004", "_cmes_profit", "label", "coalesce(map({bi4004},{1:1,2:0}),0.5)", 0.72, "直接", "是否有利润", "all"),
    ("CMES", "e1045", "_cmes_credit", "label", "map({e1045},{1:1,2:0})", 0.70, "直接", "是否有未还清民间借款(负面)", "all"),
    ("CMES", "bi2204", "_cmes_purchase_credit", "label", "map({bi2204},{1:1,2:0})", 0.70, "直接", "农资赊销/借款(负面)", "all"),
    # ============ CHFS（家庭金融调查，已验证）============
    ("CHFS", "agri_inc", "BASIC_008", "derived", "div(sum({agri_inc},{busi_inc}),10000)", 0.80, "加权平均", "农业+经营收入→年营收(万元)", "all"),
    ("CHFS", "busi_inc", "BASIC_008", "derived", "div(sum({agri_inc},{busi_inc}),10000)", 0.76, "加权平均", "", "all"),
    ("CHFS", "land_asset", "01_05", "proxy", "{land_asset}", 0.74, "加权平均", "土地资产(代理规模)", "all"),
    ("CHFS", "agri_debt", "BASIC_019", "derived", "div(sum({agri_debt},{busi_debt}),10000)", 0.80, "加权平均", "农业+经营贷款(万元)", "all"),
    ("CHFS", "busi_debt", "BASIC_019", "derived", "div(sum({agri_debt},{busi_debt}),10000)", 0.76, "加权平均", "", "all"),
    ("CHFS", "total_debt", "BASIC_009", "derived", "div({total_debt},sum({total_asset},1))", 0.76, "直接", "资产负债率", "all"),
    ("CHFS", "agri_asset", "_chfs_agri", "label", "mask({agri_asset},sum({agri_asset},{agri_inc})>0)", 0.80, "直接", "是否涉农家庭", "all"),
    ("CHFS", "total_income", "_chfs_income", "direct", "{total_income}", 0.80, "直接", "家庭总收入", "all"),
    # ============ CFPS 2016（famecon 2016 波）============
    ("CFPS", "fl3", "_cfps_agri", "label", "map({fl3},{1:1,2:0})", 0.72, "直接", "是否从事种植业/林业", "2016"),
    ("CFPS", "ft501", "BASIC_019", "derived", "div({ft501},10000)", 0.72, "加权平均", "待偿贷款额(元→万元)", "2016"),
    ("CFPS", "ft901", "_cfps_private_debt", "label", "div({ft901},10000)", 0.68, "直接", "尚未归还借款总额(万元,负面)", "2016"),
    ("CFPS", "fl6", "_cfps_livestock", "label", "map({fl6},{1:1,2:0})", 0.70, "直接", "是否养过牲畜/水产品", "2016"),
    ("CFPS", "fl805", "_cfps_hus_input", "direct", "{fl805}", 0.70, "直接", "牲畜水产投入(元,规模代理)", "2016"),
    # ============ CFPS 2018/2020/2022（famecon，字段一致）============
    ("CFPS", "fl3", "_cfps_agri", "label", "map({fl3},{1:1,2:0})", 0.72, "直接", "是否从事种植业/林业", "2018plus"),
    ("CFPS", "ft501", "BASIC_019", "derived", "div({ft501},10000)", 0.72, "加权平均", "待偿贷款额(元→万元)", "2018plus"),
    ("CFPS", "ft602", "_cfps_private_debt", "label", "div({ft602},10000)", 0.68, "直接", "待偿民间借贷(万元,负面)", "2018plus"),
    ("CFPS", "foperate_1", "BASIC_008", "proxy", "div({foperate_1},10000)", 0.70, "加权平均", "经营性收入→营收代理(万元)", "2018plus"),
    ("CFPS", "fincome1", "_cfps_income", "direct", "div({fincome1},10000)", 0.72, "直接", "全部家庭纯收入(万元)", "2018plus"),
    ("CFPS", "land_asset", "01_05", "proxy", "{land_asset}", 0.70, "加权平均", "土地资产(元,代理规模)", "2018plus"),
    ("CFPS", "fm401", "_cfps_assets", "direct", "{fm401}", 0.68, "直接", "全部经营总资产(万元)", "2018plus"),
    ("CFPS", "total_asset", "_cfps_total_asset", "direct", "{total_asset}", 0.68, "直接", "家庭净资产(元)", "2018plus"),
]

# 数据源整体可信度（用于多源 N:1 加权融合）
SOURCE_RELIABILITY: dict[str, float] = {
    "CMES": 0.78,
    "CHFS": 0.80,
    "CFPS": 0.72,
}

# 各数据源/波次读取字段（映射字段 + 清洗规则引用字段）
def _rule_fields(rule: str) -> set[str]:
    import re

    return set(re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}\s*", rule))


SOURCE_FIELDS: dict[str, dict[str, list[str]]] = {}
for _src in {m[0] for m in MAPPINGS}:
    SOURCE_FIELDS[_src] = {}
    for _wave in {m[8] for m in MAPPINGS if m[0] == _src} | {"all"}:
        _fs: set[str] = set()
        for m in MAPPINGS:
            if m[0] == _src and m[8] == _wave:
                _fs.add(m[1])
                _fs |= _rule_fields(m[4])
        SOURCE_FIELDS[_src][_wave] = sorted(_fs)

# 数据源文件（CFPS 按波次多个文件：wave, path）
SOURCE_FILES: dict[str, list[tuple[str, str]]] = {
    "CMES": [("all", "data/raw/cmes/cmes2015_191228.dta")],
    "CHFS": [("all", "data/raw/chfs/chfs2015_master_hh_pub_v1_20260707.dta")],
    "CFPS": [
        ("2016", "data/raw/cfps/cfps2016famecon_201807.dta"),
        ("2018plus", "data/raw/cfps/cfps2018famecon_202512.dta"),
        ("2018plus", "data/raw/cfps/cfps2020famecon_202306.dta"),
        ("2018plus", "data/raw/cfps/cfps2022famecon_202410.dta"),
    ],
}

# 目标指标（入模特征）：数值型评分卡特征
MODEL_FEATURES: list[str] = [
    "BASIC_003", "BASIC_004", "BASIC_005", "BASIC_008", "BASIC_009", "BASIC_019",
    "01_05", "0111_01", "0111_05", "0111_08", "0112_04", "1041_02",
    "_cmes_had_loan", "_cmes_profit", "_cmes_credit", "_cmes_purchase_credit",
    "_chfs_agri", "_chfs_income",
    "_cfps_agri", "_cfps_livestock", "_cfps_hus_input", "_cfps_private_debt",
    "_cfps_income", "_cfps_assets", "_cfps_total_asset",
]
