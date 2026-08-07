# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r"e:\Project\Web\race\back-end")
from scripts.import_indicators import parse_rows, build

data = parse_rows(r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系_v5.xlsx")
cats, inds = build(data)

checks = [
    "近三年自然灾害受灾程度", "经营者不良嗜好情况", "社区/村镇口碑",
    "绿色食品认证情况", "农产品地理标志使用", "寒地低温冻害风险等级",
    "经营者个人经营性贷款余额", "产成品库存周转天数", "稻谷销售渠道稳定性",
    "疫病防控体系", "银行信贷履约记录", "种植面积稳定性",
    "林下参/野山参经营", "马匹用途结构", "粮食为主", "天然草场退化程度",
]
for i in inds:
    if i["name"] in checks or "马匹用途" in i["name"]:
        print(
            f"{i['name']} [{i['indicator_type']}] cfg="
            f"{json.dumps(i['scoring_config'], ensure_ascii=False)} | 规则={i['scoring_rule'][:20]}"
        )

# 统计：多少枚举带 map、多少数值带 lower_better、未配置数量
enum_total = sum(1 for i in inds if i["indicator_type"] == "枚举")
enum_with_map = sum(1 for i in inds if i["indicator_type"] == "枚举" and (i["scoring_config"] or {}).get("map"))
num_total = sum(1 for i in inds if i["indicator_type"] == "数值")
num_with_cfg = sum(1 for i in inds if i["indicator_type"] == "数值" and i["scoring_config"])
print(f"\n枚举 {enum_total} 个，带 map {enum_with_map} 个")
print(f"数值 {num_total} 个，带 lower_better 配置 {num_with_cfg} 个")
