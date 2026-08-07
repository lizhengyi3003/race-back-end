"""20 组不同输入的动态评估端到端测试（走本地后端 /risk/assess-dynamic API）。

覆盖：10 个经营类型（好/中/差）、混合经营（有/无协同）、5 个一票否决、数据层混合。
"""

import json
from urllib import request

BASE = "http://localhost:8001/api/v1"


def api(path, method="GET", data=None, token=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def login():
    r = api("/auth/login", "POST", {"username": "admin", "password": "admin123"})
    return r["data"]["token"]


# 20 组场景：(标题, 经营类型, 指标字典, 混合比例 or None)
SCENARIOS = [
    # ---- 10 个经营类型：好/中/差 ----
    ("01 农林牧渔业·优质", "01", {"BASIC_003": "25", "BASIC_004": "25", "BASIC_005": "80", "BASIC_008": "480", "BASIC_009": "20", "01_05": "2600", "0111_01": "2400"}, None),
    ("01 农林牧渔业·中等", "01", {"BASIC_003": "8", "BASIC_004": "7", "BASIC_005": "15", "BASIC_008": "120", "BASIC_009": "55", "01_05": "600"}, None),
    ("01 农林牧渔业·差", "01", {"BASIC_003": "1", "BASIC_004": "1", "BASIC_005": "2", "BASIC_008": "8", "BASIC_009": "88", "01_05": "30"}, None),
    ("02 食用加工·优质", "02", {"BASIC_003": "18", "BASIC_004": "18", "BASIC_005": "90", "BASIC_008": "480", "BASIC_009": "25"}, None),
    ("03 非食用加工·中等", "03", {"BASIC_003": "6", "BASIC_004": "5", "BASIC_005": "20", "BASIC_008": "150", "BASIC_009": "60"}, None),
    ("04 生产资料制造·优质", "04", {"BASIC_003": "20", "BASIC_004": "20", "BASIC_005": "95", "BASIC_008": "490", "BASIC_009": "18"}, None),
    ("05 流通服务·中等", "05", {"BASIC_003": "7", "BASIC_004": "6", "BASIC_005": "25", "BASIC_008": "180", "BASIC_009": "58"}, None),
    ("06 科研技术服务·优质", "06", {"BASIC_003": "12", "BASIC_004": "12", "BASIC_005": "40", "BASIC_008": "320", "BASIC_009": "22"}, None),
    ("07 教育培训·中等", "07", {"BASIC_003": "5", "BASIC_004": "4", "BASIC_005": "14", "BASIC_008": "90", "BASIC_009": "62"}, None),
    ("08 生态环保·差", "08", {"BASIC_003": "2", "BASIC_004": "1", "BASIC_005": "5", "BASIC_008": "35", "BASIC_009": "80"}, None),
    ("09 休闲观光·优质", "09", {"BASIC_003": "10", "BASIC_004": "10", "BASIC_005": "35", "BASIC_008": "420", "BASIC_009": "30"}, None),
    ("10 其他支持·差", "10", {"BASIC_003": "1", "BASIC_004": "1", "BASIC_005": "3", "BASIC_008": "25", "BASIC_009": "85"}, None),
    # ---- 混合经营：协同 / 无协同 ----
    ("混合 01+02·产销一体协同", "MIXED", {"BASIC_003": "10", "BASIC_004": "10", "BASIC_005": "45", "BASIC_008": "380", "BASIC_009": "35"}, {"01": 0.6, "02": 0.4}),
    ("混合 01+08·生态循环协同", "MIXED", {"BASIC_003": "9", "BASIC_004": "9", "BASIC_005": "30", "BASIC_008": "260", "BASIC_009": "40"}, {"01": 0.7, "08": 0.3}),
    ("混合 05+06·无协同", "MIXED", {"BASIC_003": "8", "BASIC_004": "8", "BASIC_005": "28", "BASIC_008": "300", "BASIC_009": "45"}, {"05": 0.7, "06": 0.3}),
    # ---- 5 个一票否决 ----
    ("一票否决·失信被执行人", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_013": "是"}, None),
    ("一票否决·重大税收违法", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_014": "是"}, None),
    ("一票否决·环保处罚未整改", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_015": "是"}, None),
    ("一票否决·征信连三累六", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_016": "是"}, None),
    ("一票否决·实控人刑事案件", "01", {"BASIC_003": "15", "BASIC_008": "400", "BASIC_017": "是"}, None),
]


def run():
    token = login()
    results = []
    for title, bt, indicators, mixed in SCENARIOS:
        payload = {"enterpriseName": f"测试·{title}", "businessType": bt, "productType": "综合", "indicators": indicators}
        if mixed:
            payload["mixedBusiness"] = mixed
        r = api("/risk/assess-dynamic", "POST", payload, token)
        d = r["data"]
        results.append((title, bt, d))

    # 输出汇总
    print(f"{'场景':<28} {'类型':<6} {'评分':>5} {'等级':<6} 关键信息")
    print("-" * 90)
    for title, bt, d in results:
        extra = []
        if d.get("veto"):
            extra.append(f"否决:{d['veto']}")
        for o in (d.get("overrides") or []):
            if o.startswith("synergy"):
                extra.append("协同")
            if o.startswith("data_layer"):
                extra.append("数据层")
        info = "; ".join(extra) if extra else "-"
        print(f"{title:<28} {bt:<6} {d['score']:>5} {d['level']:<6} {info}")

    # 统计
    levels = {}
    for _t, _bt, d in results:
        levels[d["level"]] = levels.get(d["level"], 0) + 1
    veto_cnt = sum(1 for _t, _bt, d in results if d.get("veto"))
    synergy_cnt = sum(1 for _t, _bt, d in results if any(o.startswith("synergy") for o in d.get("overrides", [])))
    data_cnt = sum(1 for _t, _bt, d in results if any(o.startswith("data_layer") for o in d.get("overrides", [])))
    print("-" * 90)
    print(f"等级分布: {levels} | 一票否决触发: {veto_cnt} | 协同触发: {synergy_cnt} | 数据层触发: {data_cnt}")
    ok = all(0 <= d["score"] <= 1000 and d["level"] in ("低风险", "中等风险", "高风险") for _t, _bt, d in results)
    print(f"契约校验（0-1000 分 + 合法等级）: {'✅ 全部通过' if ok else '❌ 有异常'}")
    return results


if __name__ == "__main__":
    run()
