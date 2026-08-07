# -*- coding: utf-8 -*-
"""联调测试：tree 带 indicators、config specificType、assess-dynamic selectedCategories"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8002/api/v1"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


# 1. tree 带 indicators
t = get("/indicators/tree")["data"]
print(f"1) tree: basic={len(t['basic'])} 大类={len(t['categories'])}")
node = t["categories"][0]["children"][0]["children"][0]
print(f"   小类 {node['display']} 自带指标 {len(node.get('indicators') or [])} 个")
leaf = node["children"][0]
print(f"   叶子 {leaf['display']} 自带指标 {len(leaf.get('indicators') or [])} 个, 首条={leaf['indicators'][0]['name']}")

# 2. config specificType
c = get("/indicators/config?businessType=01&middleType=011&smallType=0111&specificType=0111_0111")["data"]
print(f"2) config selected={c['selected']}")
print(f"   indicators 层级={sorted(set(i['level'] for i in c['indicators']))}")

# 3. assess-dynamic selectedCategories
body = {
    "enterpriseName": "联调测试社",
    "businessType": "01",
    "productType": "水稻",
    "selectedCategories": ["0111_0111"],
    "mixedBusiness": {},
    "indicators": {
        "BASIC_001": "联调测试社",
        "0111_0111_01": "1200",   # 稻谷播种面积
        "0111_0111_02": "650",    # 稻谷年产量
        "011_0111_01": "80",      # 中类测土配方
    },
}
res = post("/risk/assess-dynamic", body)["data"]
print(f"3) assess-dynamic: score={res['score']} level={res['level']} amount={res['suggestedAmount']} completeness={res['completeness']}")
print(f"   contributions={len(res['contributions'])}")

# 4. 混合经营：跨大类
body2 = {
    "enterpriseName": "混合测试社",
    "businessType": "MIXED",
    "productType": "种养结合",
    "selectedCategories": ["0111_0113", "0131_0311"],
    "mixedBusiness": {"01": 0.5, "01": 0.5},
    "indicators": {
        "BASIC_001": "混合测试社",
        "0111_0113_01": "1000",
        "0131_0311_01": "200",
    },
}
res2 = post("/risk/assess-dynamic", body2)["data"]
print(f"4) mixed: score={res2['score']} level={res2['level']} amount={res2['suggestedAmount']}")
print("DONE")
