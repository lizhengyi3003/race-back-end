# -*- coding: utf-8 -*-
"""全面核对指标体系树形结构：
1. 各 大类 -> 中类 -> 小类 -> 具体营业类型 覆盖
2. 找缺少小类的中类、缺少具体营业类型的小类
3. 具体营业类型总数核对"""
import openpyxl
from collections import OrderedDict

XLSX = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.xlsx"
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active

# 收集各层级
bigs = OrderedDict()   # code -> name
mids = OrderedDict()   # mcode -> (name, bcode)
smalls = OrderedDict() # scode -> (name, mcode)
l4 = []                # (code, name)
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
        l4.append((code, cat))

print(f"大类 {len(bigs)}, 中类 {len(mids)}, 小类 {len(smalls)}, 具体营业类型 {len(l4)}")
print()

# 1. 每个大类: 中类数/小类数/具体营业类型数
print("=== 各大类结构 ===")
for bcode, bname in bigs.items():
    mid_list = [m for m, (mn, bc) in mids.items() if bc == bcode]
    sm_list = [s for s, (sn, mc) in smalls.items() if mc[:2] == bcode]
    l4_list = [c for c, cn in l4 if c[:2] == bcode]
    # 具体营业类型属于哪小类? l4 码是小类码_行业码, 小类码前缀
    l4_by_big = [c for c, cn in l4 if c[:2] == bcode]
    print(f"{bcode} {bname}: 中类{len(mid_list)} 小类{len(sm_list)} 具体营业类型{len(l4_by_big)}")

print()
print("=== 缺少小类的中类 ===")
missing_small_mid = []
for mcode, (mname, bcode) in mids.items():
    has = [s for s, (sn, mc) in smalls.items() if mc == mcode]
    if not has:
        missing_small_mid.append((mcode, mname))
        print(f"  {mcode} {mname} (大类{bcode}) 无小类")

print()
print("=== 缺少具体营业类型的小类 ===")
missing_l4_small = []
for scode, (sname, mcode) in smalls.items():
    has = [c for c, cn in l4 if c.startswith(scode + "_")]
    if not has:
        missing_l4_small.append((scode, sname, mcode))
        print(f"  {scode} {sname} (中类{mcode}) 无具体营业类型")

print()
print(f"统计: 无小类的中类 {len(missing_small_mid)} 个; 无具体营业类型的小类 {len(missing_l4_small)} 个")
