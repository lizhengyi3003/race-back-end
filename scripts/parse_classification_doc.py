# -*- coding: utf-8 -*-
"""解析《农业及相关产业统计分类（2020）》.md → 生成 4 级类别结构（大类/中类/小类/具体营业类型）。
输出:
  - docs/parsed_categories.json   完整 4 级类别树（供审核）
  - 控制台统计：各级别数量、与现有 DB(10/61/215) 对比、行业代码冲突情况
"""
import json
import re
import sys
from pathlib import Path

DOC = Path(r"e:\Project\Web\race\fore-end\docs") / "《农业及相关产业统计分类（2020）》.md"
OUT = Path(__file__).resolve().parent / "parsed_categories.json"

def parse_md(text: str):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and "|" in line[1:]):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9:
            continue
        big, big_name, mid, mid_name, small, small_name, ind_code, ind_name = cells[0:8]
        if not (re.fullmatch(r"\d{2}", big) and mid and small and ind_code):
            continue
        rows.append({
            "big": big, "big_name": big_name,
            "mid": mid, "mid_name": mid_name,
            "small": small, "small_name": small_name,
            "industry_code": ind_code, "industry_name": ind_name,
        })
    return rows

def main():
    text = DOC.read_text(encoding="utf-8")
    rows = parse_md(text)
    print(f"解析数据行（第4级行业）: {len(rows)}")

    # 各级别去重
    bigs = {(r["big"], r["big_name"]) for r in rows}
    mids = {(r["mid"], r["mid_name"]) for r in rows}
    smalls = {(r["small"], r["small_name"]) for r in rows}
    inds = {(r["industry_code"], r["industry_name"]) for r in rows}
    print(f"大类: {len(bigs)}  中类: {len(mids)}  小类: {len(smalls)}  具体营业类型: {len(inds)}")
    print(f"(现有 DB 应为 大类10/中类61/小类215)")

    # 检查现有 DB 对比：中类/小类是否与文档一致
    # 代码冲突：小类 code 与行业 code 是否有相同数值
    small_codes = {r["small"] for r in rows}
    ind_codes = {r["industry_code"] for r in rows}
    collide = sorted(small_codes & ind_codes)
    print(f"小类code与行业code数值冲突数量: {len(collide)} (如 {collide[:8]})")

    # 构建树
    tree = []
    for big in sorted(bigs):
        bnode = {"code": big[0], "name": big[1], "children": []}
        for mid in sorted({(r["mid"], r["mid_name"]) for r in rows if r["big"] == big[0]}):
            mnode = {"code": mid[0], "name": mid[1], "children": []}
            for small in sorted({(r["small"], r["small_name"]) for r in rows if r["mid"] == mid[0]}):
                snode = {"code": small[0], "name": small[1], "children": []}
                for r in rows:
                    if r["small"] == small[0]:
                        # 第4级唯一编码：小类code_行业code（避免数值冲突）
                        snode["children"].append({
                            "code": f"{small[0]}_{r['industry_code']}",
                            "name": r["industry_name"],
                            "industry_code": r["industry_code"],
                        })
                snode["children"].sort(key=lambda c: c["industry_code"])
                mnode["children"].append(snode)
            mnode["children"].sort(key=lambda c: c["code"])
            bnode["children"].append(mnode)
        bnode["children"].sort(key=lambda c: c["code"])
        tree.append(bnode)

    OUT.write_text(json.dumps(tree, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写入: {OUT}")

    # 展示前 2 个大类的树形预览
    for b in tree[:2]:
        print(f"\n[{b['code']} {b['name']}]")
        for m in b["children"][:3]:
            print(f"  [{m['code']} {m['name']}]")
            for s in m["children"][:3]:
                print(f"    [{s['code']} {s['name']}]")
                for c in s["children"][:4]:
                    print(f"      [{c['code']} {c['name']}]")

if __name__ == "__main__":
    main()
