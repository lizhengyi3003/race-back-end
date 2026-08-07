# -*- coding: utf-8 -*-
"""打印 parsed_categories.json 的完整结构概览：每个小类下的具体营业类型清单。"""
import json
from pathlib import Path

tree = json.load(open(Path(__file__).parent / "parsed_categories.json", encoding="utf-8"))
for b in tree:
    n4 = sum(len(s["children"]) for m in b["children"] for s in m["children"])
    print(f"\n### [{b['code']} {b['name']}] 第4级共{n4}个")
    for m in b["children"]:
        print(f"  · {m['code']} {m['name']}")
        for s in m["children"]:
            names = "、".join(c["name"] for c in s["children"])
            print(f"      {s['code']} {s['name']} → {names}")
