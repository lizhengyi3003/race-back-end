# -*- coding: utf-8 -*-
"""展示大类10明细 + 具体营业类型类别总数核对"""
import openpyxl
from collections import OrderedDict

XLSX = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.xlsx"
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active

bigs = OrderedDict()
mids = OrderedDict()
smalls = OrderedDict()
l4 = []
for r in ws.iter_rows(min_row=2, values_only=True):
    lv = r[0]; cat = r[1]
    if not lv or not cat:
        continue
    code = str(cat).split(" ")[0]
    if lv == "大类":
        bigs[code] = cat
    elif lv == "中类":
        mids[code] = (cat, code[:2])
    elif lv == "小类":
        smalls[code] = (cat, code[:3])
    elif lv == "具体营业类型":
        l4.append(code)

# 具体营业类型类别总数（去重）
l4_cats = list(OrderedDict.fromkeys(l4))
print(f"具体营业类型指标总行数: {len(l4)}")
print(f"具体营业类型类别数(去重): {len(l4_cats)}")

print()
print("=== 大类10 其他支持服务 明细 ===")
for mcode, (mname, bc) in mids.items():
    if bc == "10":
        sm_list = [(s, sn) for s, (sn, mc) in smalls.items() if mc == mcode]
        print(f"中类 {mcode} {mname}  -> 小类 {len(sm_list)} 个:")
        for s, sn in sm_list:
            cnt = len([c for c in l4_cats if c.startswith(s + "_")])
            print(f"    {s} {sn}: 具体营业类型 {cnt} 个")
        # 直接属于该中类但无小类前缀的？不需要

print()
print("=== 各 小类 -> 具体营业类型 数量分布 ===")
cnts = [len([c for c in l4_cats if c.startswith(s + "_")]) for s in smalls]
from collections import Counter
dist = Counter(cnts)
print("每个小类下具体营业类型类别数分布:", dict(sorted(dist.items())))
print(f"校验: 各类别数之和 = {sum(cnts)} (应=具体营业类型类别数 {len(l4_cats)})")
