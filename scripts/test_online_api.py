# -*- coding: utf-8 -*-
"""线上 API 验证：tree 4级 / config specificType / assess-dynamic"""
import json
import urllib.request
import ssl

BASE = "https://api.intellicoretech.cn/api/v1"
ctx = ssl.create_default_context()


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


t = get("/indicators/tree")["data"]
print(f"1) tree: basic={len(t['basic'])} 大类={len(t['categories'])}")
leaf = t["categories"][0]["children"][0]["children"][0]["children"][0]
print(f"   叶子 {leaf['display']} 自带指标 {len(leaf.get('indicators') or [])} 条, 首条={leaf['indicators'][0]['name']}")

c = get("/indicators/config?businessType=01&middleType=011&smallType=0111&specificType=0111_0111")["data"]
print(f"2) config selected={c['selected']}")
print(f"   levels={sorted(set(i['level'] for i in c['indicators']))}")

body = {
    "enterpriseName": "线上验证社",
    "businessType": "01",
        "selectedCategories": ["0111_0111"],
    "mixedBusiness": {},
    "indicators": {"BASIC_001": "线上验证社", "0111_0111_01": "1200", "0111_0111_02": "650"},
}
res = post("/risk/assess-dynamic", body)["data"]
print(f"3) assess: score={res['score']} level={res['level']} amount={res['suggestedAmount']} completeness={res['completeness']}")
print("ONLINE OK")
