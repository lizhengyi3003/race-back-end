# -*- coding: utf-8 -*-
"""线上 API 验证评分方向：登录 → 找指标编码 → 两轮 assess 对比。"""
import json
import urllib.request
import urllib.error
import ssl

BASE = "https://api.intellicoretech.cn/api/v1"
ctx = ssl.create_default_context()


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def call(path, data=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


try:
    t = call("/auth/login", {"username": "admin", "password": "admin123"})
    token = t["data"]["token"]
except urllib.error.HTTPError as e:
    print("登录失败:", e.code, e.read().decode()[:300])
    raise SystemExit(1)

tree = call("/indicators/tree", token=token)["data"]
# 找基本项编码
loan_code = None
for b in tree["basic"]:
    if "个人经营性贷款" in b["name"]:
        loan_code = b["code"]
print("贷款余额编码:", loan_code)

# 大类 config 找灾害程度编码
cfg = call("/indicators/config?businessType=01", token=token)["data"]
disaster_code = None
for i in cfg["indicators"]:
    if "自然灾害受灾" in i["name"]:
        disaster_code = i["code"]
print("灾害程度编码:", disaster_code)


def assess(ind_map, label):
    body = {
        "enterpriseName": "方向验证",
        "businessType": "01",
        "indicators": ind_map,
    }
    r = call("/risk/assess-dynamic", body, token=token)["data"]
    print(f"{label}: score={r['score']} level={r['level']}")
    return r["score"]


# 灾害程度：无 vs 重
if disaster_code:
    a = assess({disaster_code: "无"}, "灾害=无")
    b = assess({disaster_code: "重"}, "灾害=重")
    print("灾害方向:", "正确(无>重)" if a > b else "!!!反了")

# 贷款余额：低 vs 高
if loan_code:
    c = assess({loan_code: "10"}, "贷款余额=10(低)")
    d = assess({loan_code: "500"}, "贷款余额=500(高)")
    print("贷款方向:", "正确(低>高)" if c > d else "!!!反了")
