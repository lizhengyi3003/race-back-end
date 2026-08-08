"""Phase 1: 数据源字段 → 模型指标 自动预匹配。

输入：
- data/samples/field_catalog.csv（7,444 条数据源字段，含中文标签）
- data/samples/indicator_catalog.csv（775 条模型指标）
输出：
- data/samples/mapping_candidates.csv（候选映射，供人工审核）
- 控制台输出统计（按数据源/匹配方式）

匹配策略（保守优先，避免噪音）：
1. 精确包含：指标名是字段标签的子串，或字段标签是指标名的子串（高置信）
2. 相似度：difflib.SequenceMatcher ratio >= 0.62（中置信）
结果标注 match_type: exact_contain / fuzzy，score 0-1。
"""

import difflib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIELD_CSV = ROOT / "data" / "samples" / "field_catalog.csv"
IND_CSV = ROOT / "data" / "samples" / "indicator_catalog.csv"
OUT = ROOT / "data" / "samples" / "mapping_candidates.csv"

# 指标名中常见的通用后缀词（匹配时剥离，避免误匹配）
_SUFFIX = ["（亩）", "（万元）", "（%）", "（人）", "（年）", "（元）", "面积", "总额", "数量", "收入", "支出"]


def _norm(s: str) -> str:
    s = (s or "").strip()
    for suf in _SUFFIX:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def main() -> None:
    fields = pd.read_csv(FIELD_CSV)
    inds = pd.read_csv(IND_CSV)
    print(f"数据源字段: {len(fields)}, 指标: {len(inds)}")

    # 预构建指标名集合（含去后缀版）
    ind_names = list(inds["name"].astype(str))
    ind_by_name = {n: inds[inds["name"] == n] for n in set(ind_names)}

    rows = []
    seen: set[tuple] = set()
    for _, f in fields.iterrows():
        label = str(f["label"] or "").strip()
        if not label:
            continue
        label_norm = _norm(label)
        best = None
        # 1) 精确包含匹配
        for n in ind_names:
            if n and len(n) >= 3 and (n in label or label in n):
                score = 0.95 if n in label else 0.9
                if best is None or score > best[0]:
                    best = (score, n, "exact_contain")
        # 2) 去后缀后包含
        if best is None and label_norm:
            for n in ind_names:
                nn = _norm(n)
                if nn and len(nn) >= 3 and (nn in label or nn in label_norm or label_norm in nn):
                    if best is None or 0.88 > best[0]:
                        best = (0.88, n, "norm_contain")
        # 3) 模糊相似度
        if best is None and label:
            for n in ind_names:
                if not n:
                    continue
                r = difflib.SequenceMatcher(None, label, n).ratio()
                if r >= 0.62 and (best is None or r > best[0]):
                    best = (round(r, 3), n, "fuzzy")
        if best:
            score, ind_name, mtype = best
            # 取该指标名对应的 code（若同名多 code 取第一个）
            match = ind_by_name[ind_name]
            code = str(match.iloc[0]["code"])
            key = (f["source"], str(f["field"]), code)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "source": f["source"],
                    "wave": f.get("wave", ""),
                    "field": f["field"],
                    "label": label,
                    "indicator_code": code,
                    "indicator_name": ind_name,
                    "score": score,
                    "match_type": mtype,
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["source", "score"], ascending=[True, False])
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\n候选映射: {len(df)} 条 -> {OUT}")
    print(df.groupby("match_type").size().to_string())
    print("\n按数据源:")
    print(df.groupby("source").size().to_string())
    print("\n高置信（exact_contain/norm_contain）示例:")
    high = df[df["match_type"] != "fuzzy"]
    print(high.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
