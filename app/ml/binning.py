"""WOE 分箱与 IV 计算。

技术路线（对齐商业计划书）：
1. 连续变量：分位数初分箱 → 合并低频箱 → 坏账率单调性校正
2. 分类变量：按类别计算 WOE → 合并稀有类别为“其他”
3. WOE = ln(good_dist / bad_dist)，IV = (good_dist - bad_dist) * WOE
4. 缺失单独成箱处理
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd


def _safe_woe(bad: float, good: float, total_bad: float, total_good: float) -> float:
    bad_dist = bad / max(total_bad, 1.0)
    good_dist = good / max(total_good, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return float(np.log(max(good_dist, 1e-6) / max(bad_dist, 1e-6)))


def _safe_iv(bad: float, good: float, total_bad: float, total_good: float) -> float:
    bad_dist = bad / max(total_bad, 1.0)
    good_dist = good / max(total_good, 1.0)
    woe = _safe_woe(bad, good, total_bad, total_good)
    return float((good_dist - bad_dist) * woe)


class WOEBinner:
    """单个特征的 WOE 分箱器"""

    def __init__(self, field: str, is_categorical: bool = False, max_bins: int = 5, min_bin_pct: float = 0.05):
        self.field = field
        self.is_categorical = is_categorical
        self.max_bins = max_bins
        self.min_bin_pct = min_bin_pct

        self.bins_: list[dict] = []  # 分箱明细 [{label, woe, count, bad_rate, iv}]
        self.edges_: list[float] | None = None  # 连续变量：分箱右边界（不含 -inf）
        self.woe_per_bin_: list[float] = []  # 连续变量：每箱 WOE（与 edges 对齐）
        self.cat_map_: dict[str, float] = {}  # 分类变量：类别 -> WOE
        self.iv_ = 0.0
        self.missing_woe_ = 0.0

    # ---------------------------------------------------------------
    def fit(self, series: pd.Series, target: pd.Series) -> WOEBinner:
        data = pd.DataFrame({"x": series, "y": target.astype(int)})
        total = len(data)
        total_bad = int(data["y"].sum())
        total_good = total - total_bad

        non_null = data[data["x"].notna()].copy()

        # ---- 缺失单独处理 ----
        missing = data[data["x"].isna()]
        if len(missing) > 0:
            miss_bad = int(missing["y"].sum())
            miss_good = len(missing) - miss_bad
            self.missing_woe_ = _safe_woe(miss_bad, miss_good, total_bad, total_good)
            self.iv_ += _safe_iv(miss_bad, miss_good, total_bad, total_good)

        if self.is_categorical:
            self._fit_categorical(non_null, total, total_bad, total_good)
        else:
            self._fit_continuous(non_null, total, total_bad, total_good)

        self.iv_ = round(self.iv_, 6)
        return self

    # ---------------------------------------------------------------
    def _fit_categorical(self, non_null: pd.DataFrame, total: int, total_bad: int, total_good: int) -> None:
        grouped = non_null.groupby("x")["y"].agg(["count", "sum"]).reset_index()
        grouped.columns = ["x", "count", "bad"]
        grouped["good"] = grouped["count"] - grouped["bad"]

        min_count = max(2, int(self.min_bin_pct * total))
        rare = grouped[grouped["count"] < min_count]
        common = grouped[grouped["count"] >= min_count]

        rows = []
        if len(rare) > 0:
            rows.append(
                {
                    "x": "__other__",
                    "count": int(rare["count"].sum()),
                    "bad": int(rare["bad"].sum()),
                }
            )
        if len(common) > 0:
            rows.extend(common.to_dict("records"))

        for row in rows:
            good = int(row["count"]) - int(row["bad"])
            woe = _safe_woe(row["bad"], good, total_bad, total_good)
            iv = _safe_iv(row["bad"], good, total_bad, total_good)
            label = str(row["x"])
            self.bins_.append(
                {
                    "label": label,
                    "woe": woe,
                    "count": int(row["count"]),
                    "bad_rate": round(int(row["bad"]) / max(int(row["count"]), 1), 4),
                    "iv": round(iv, 6),
                }
            )
            self.cat_map_[label] = woe
            self.iv_ += iv

    # ---------------------------------------------------------------
    def _fit_continuous(self, non_null: pd.DataFrame, total: int, total_bad: int, total_good: int) -> None:
        values = non_null["x"].values.astype(float)
        ys = non_null["y"].values.astype(int)

        # 1) 初分箱
        n_unique = len(np.unique(values))
        n_bins = min(self.max_bins, n_unique)
        if n_bins < 2:
            edges = [float(values.min()), float(values.max())]
            counts = [len(values)]
            bads = [int(ys.sum())]
        else:
            quantiles = np.linspace(0, 1, n_bins + 1)
            raw_edges = np.quantile(values, quantiles)
            edges = np.unique(raw_edges).tolist()
            if len(edges) < 3:
                edges = [float(values.min()), float(values.max())]
            boundaries = np.array(edges[1:-1])
            bin_idx = np.searchsorted(boundaries, values, side="right")
            counts = np.bincount(bin_idx, minlength=len(boundaries) + 1).astype(int).tolist()
            bads = np.bincount(bin_idx, weights=ys, minlength=len(boundaries) + 1).astype(int).tolist()

        # 2) 合并低频箱
        bins = [[edges[i], edges[i + 1], int(counts[i]), int(bads[i])] for i in range(len(counts))]
        min_count = max(2, int(self.min_bin_pct * total))

        def _merge(i: int) -> None:
            bins[i] = [bins[i][0], bins[i + 1][1], bins[i][2] + bins[i + 1][2], bins[i][3] + bins[i + 1][3]]
            del bins[i + 1]

        merged = True
        while merged:
            merged = False
            for i in range(len(bins)):
                if bins[i][2] < min_count:
                    if i == 0:
                        _merge(0)
                    elif i == len(bins) - 1:
                        _merge(i - 1)
                    else:
                        # 合并到样本更少的相邻箱
                        if bins[i - 1][2] <= bins[i + 1][2]:
                            _merge(i - 1)
                        else:
                            _merge(i)
                    merged = True
                    break

        # 3) 坏账率单调性校正（贪心合并）
        def _rates() -> list[float]:
            return [b[3] / max(b[2], 1) for b in bins]

        def _is_monotonic(rates: list[float]) -> bool:
            if len(rates) < 2:
                return True
            signs = []
            for i in range(len(rates) - 1):
                d = rates[i + 1] - rates[i]
                if d > 1e-9:
                    signs.append(1)
                elif d < -1e-9:
                    signs.append(-1)
            return len(set(signs)) <= 1

        guard = 0
        while len(bins) > 2 and not _is_monotonic(_rates()) and guard < 10:
            guard += 1
            rates = _rates()
            # 找到破坏单调性的相邻对，合并其中样本较少的
            target = None
            for i in range(len(rates) - 1):
                d1 = rates[i + 1] - rates[i] if i > 0 else 0
                d2 = rates[i + 2] - rates[i + 1] if i + 2 < len(rates) else 0
                if i > 0 and i + 2 < len(rates) and (d1 * d2 < 0):
                    target = i if bins[i][2] <= bins[i + 2][2] else i + 1
                    break
            if target is None:
                # 退化为合并最小样本相邻对
                sizes = [bins[i][2] + bins[i + 1][2] for i in range(len(bins) - 1)]
                target = int(np.argmin(sizes))
            _merge(target)

        # 4) 计算 WOE / IV
        # edges_ 保存“内部边界”（不含 min/max），transform 用 bisect 定位分箱
        self.edges_ = [b[0] for b in bins[1:]]
        self.woe_per_bin_ = []
        for b in bins:
            bad, good = b[3], b[2] - b[3]
            woe = _safe_woe(bad, good, total_bad, total_good)
            iv = _safe_iv(bad, good, total_bad, total_good)
            self.woe_per_bin_.append(woe)
            self.iv_ += iv
            self.bins_.append(
                {
                    "label": f"[{b[0]:.2g}, {b[1]:.2g})",
                    "woe": woe,
                    "count": b[2],
                    "bad_rate": round(bad / max(b[2], 1), 4),
                    "iv": round(iv, 6),
                }
            )

    # ---------------------------------------------------------------
    def transform(self, value) -> float:
        """值 -> WOE（缺失返回缺失箱 WOE）"""
        if value is None:
            return self.missing_woe_
        if isinstance(value, float) and np.isnan(value):
            return self.missing_woe_
        if value == "":
            return self.missing_woe_

        if self.is_categorical:
            key = str(value)
            if key in self.cat_map_:
                return self.cat_map_[key]
            return self.cat_map_.get("__other__", 0.0)

        if self.edges_ is None or not self.woe_per_bin_:
            return 0.0
        idx = bisect.bisect_right(self.edges_, float(value))
        idx = max(0, min(idx, len(self.woe_per_bin_) - 1))
        return self.woe_per_bin_[idx]

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "is_categorical": self.is_categorical,
            "iv": self.iv_,
            "bins": self.bins_,
            "edges": self.edges_,
            "woe_per_bin": self.woe_per_bin_,
            "cat_map": self.cat_map_,
            "missing_woe": self.missing_woe_,
        }
