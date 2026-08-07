# -*- coding: utf-8 -*-
"""检查第4级指标能否按「小类码」归位到所属小类后面。"""
import io
import openpyxl
from collections import OrderedDict, Counter

XLSX = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.xlsx"
MD = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.md"


def small_code(cat: str) -> str:
    """'0111_0111 稻谷种植' -> '0111' ;  '0111 谷物种植' -> '0111'"""
    return cat.split("_")[0].split(" ")[0].strip()


def analyze_rows(rows, label):
    """rows: list of tuples/rows. 返回统计"""
    originals = [r for r in rows if r[0] != "具体营业类型"]
    level4 = [r for r in rows if r[0] == "具体营业类型"]
    print(f"== {label}: 总 {len(rows)} 行, 原有 {len(originals)}, 第4级 {len(level4)}")

    # 小类最后出现位置
    last_pos = {}
    for i, r in enumerate(originals):
        if r[0] == "小类":
            last_pos[small_code(r[1])] = i

    # 分组第4级
    groups = OrderedDict()
    for r in level4:
        groups.setdefault(small_code(r[1]), []).append(r)

    orphan = {k: v for k, v in groups.items() if k not in last_pos}
    print(f"  第4级小类组数: {len(groups)}, 孤儿组(找不到所属小类): {len(orphan)}")
    for k, v in orphan.items():
        print(f"    孤儿小类码 {k}: {len(v)} 条, 例: {v[0][1]}")
    for k, v in groups.items():
        if k in last_pos and v:
            pass
    # 检查小类行是否连续（一个小类的行是否连在一起）
    seq = []
    for r in originals:
        if r[0] == "小类":
            seq.append(small_code(r[1]))
    # 统计每组行数
    groups_cnt = Counter(seq)
    print(f"  小类码种类: {len(groups_cnt)}, 示例: {list(groups_cnt.items())[:8]}")
    # 检查某小类行是否被非本小类行打断
    broken = []
    cur = None
    for r in originals:
        if r[0] == "小类":
            cur = small_code(r[1])
        elif r[0] != "小类":
            cur = None
        # 不需要此逻辑
    # 直接检查：对每个小类，其所有行是否连续
    contig = True
    for code in groups_cnt:
        idxs = [i for i, r in enumerate(originals) if r[0] == "小类" and small_code(r[1]) == code]
        if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
            contig = False
            print(f"  小类 {code} 行不连续: {idxs[:5]}...")
    print(f"  所有小类行连续: {contig}")
    return originals, level4, groups, last_pos


# ---- 读 xlsx ----
wb = openpyxl.load_workbook(XLSX, read_only=False)
ws = wb.active
xrows = [tuple(c.value for c in row) for row in ws.iter_rows(min_row=2)]
analyze_rows(xrows, "XLSX")

# ---- 读 md ----
with io.open(MD, encoding="utf-8") as f:
    lines = f.readlines()
md_rows = []
for ln in lines:
    s = ln.strip()
    if s.startswith("|") and not s.startswith("| 层级"):
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) >= 14:
            md_rows.append(tuple(parts[:14]))
analyze_rows(md_rows, "MD")
