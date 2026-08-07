# -*- coding: utf-8 -*-
"""按检查报告修正补贴标准取值说明（仅改值，不增删行，保留样式）。
输出到 _v3 临时文件。"""
import io
import openpyxl

XLSX = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.xlsx"
MD = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系.md"
XLSX_OUT = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系_v3.xlsx"
MD_OUT = r"e:\Project\Web\race\fore-end\docs\农业及相关产业动态指标搜集体系_v3.md"

REPL = {
    # 1. 耕地地力保护补贴（黑龙江 76 -> 75.73）
    "年度实际到账金额（东北近年参考：黑约76、吉约128、辽约132元/亩，以当年官方公示为准）":
        "年度实际到账金额（东北近年参考：黑75.73、吉约128、辽约132元/亩，以当年官方公示为准）",
    # 2. 黑土地保护性耕作补助（补充金额）
    "免耕/少耕/秸秆覆盖还田实施面积":
        "免耕/少耕/秸秆覆盖还田实施面积（黑龙江补助约35-60元/亩、吉林最高约80元/亩，以当年官方公示为准）",
    # 3. 深松整地补贴（补充金额）
    "深松作业面积":
        "深松作业面积（黑龙江作业补助约20元/亩，以当年官方公示为准）",
    # 4. 玉米生产者补贴（黑龙江改为范围值）
    "当年补贴标准×种植面积（东北近年参考：黑约17、吉约49、辽约67元/亩，以当年官方公示为准）":
        "当年补贴标准×种植面积（东北近年参考：黑约30-150、吉约49、辽约67元/亩，黑龙江当年标准以省级公示为准）",
    # 5. 轮作休耕补贴（扩大范围）
    "轮作试点补贴到账（东北近年参考：约80-150元/亩，以当年官方公示为准）":
        "轮作/休耕试点补贴到账（东北近年参考：轮作约150-200元/亩、休耕约500-800元/亩·季，以当年官方公示为准）",
    # 6. 大豆生产者补贴（增加高油高蛋白说明）
    "当年补贴标准×面积（东北近年参考：黑约350、吉约550、辽约410-460元/亩，以当年官方公示为准）":
        "当年补贴标准×面积（东北近年参考：黑约350、吉约550、辽约410-460元/亩；高油/高蛋白品种另有额外补贴，以当年官方公示为准）",
}

# ==================== XLSX（只改值，样式保留） ====================
print("== XLSX ==")
wb = openpyxl.load_workbook(XLSX)
ws = wb.active
changed = 0
for row in ws.iter_rows(min_row=2):
    cell = row[5]  # 取值说明列
    if cell.value in REPL:
        print(f"  改: {row[2].value} | {row[1].value}")
        print(f"    旧: {cell.value[:60]}...")
        cell.value = REPL[cell.value]
        changed += 1
wb.save(XLSX_OUT)
print(f"XLSX 修改 {changed} 处 -> {XLSX_OUT}")

# ==================== MD ====================
print("== MD ==")
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
    if p and p[5] in REPL:
        print(f"  MD 改: {p[2]} | {p[1]}")
        p[5] = REPL[p[5]]
        ln = "| " + " | ".join(p) + " |\n"
        md_changed += 1
    out.append(ln)
with io.open(MD_OUT, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(out)
print(f"MD 修改 {md_changed} 处 -> {MD_OUT}")
print("完成")
