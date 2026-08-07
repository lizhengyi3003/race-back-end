# -*- coding: utf-8 -*-
"""修复『经营者个人经营性贷款余额』评分方向（数值越高得分越高 -> 数值越高风险越高）
同步 xlsx + md，输出 _v5 临时文件。"""
import io
import openpyxl

XLSX = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.xlsx"
MD = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.md"
XLSX_OUT = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系_v5.xlsx"
MD_OUT = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系_v5.md"

TARGET_NAME = "经营者个人经营性贷款余额"
OLD_RULE = "数值越高得分越高（分段计分）"
NEW_RULE = "数值越高风险越高（分段扣分）"

# ===== XLSX（只改值，保留样式）=====
wb = openpyxl.load_workbook(XLSX)
ws = wb.active
changed = 0
for row in ws.iter_rows(min_row=2):
    if row[2].value == TARGET_NAME and row[13].value == OLD_RULE:
        row[13].value = NEW_RULE
        changed += 1
        print(f"XLSX 改: {row[2].value} 规则 -> {NEW_RULE}")
wb.save(XLSX_OUT)
print(f"XLSX 修改 {changed} 处")

# ===== MD =====
with io.open(MD, encoding="utf-8") as f:
    lines = f.readlines()

def parse_table(ln):
    s = ln.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    if s.startswith("|---"):
        return None
    p = [x.strip() for x in s.strip("|").split("|")]
    if len(p) < 14 or p[0] in ("层级", ""):
        return None
    return p[:14]

md_changed = 0
out = []
for ln in lines:
    p = parse_table(ln)
    if p and p[2] == TARGET_NAME and p[13] == OLD_RULE:
        p[13] = NEW_RULE
        ln = "| " + " | ".join(p) + " |\n"
        md_changed += 1
    out.append(ln)
with io.open(MD_OUT, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(out)
print(f"MD 修改 {md_changed} 处 -> 完成")
