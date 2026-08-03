"""合成样本生成器：模拟黑龙江涉农经营主体数据（含违约标签）。

依据文档 3.3.2 四大维度 15 项指标构建数据生成过程（校赛通用方案）：
- 真实分布：确权面积/营收右偏、投保年限左偏、流转年限离散
- 违约率挂钩指标：信用好的样本各指标整体优于信用差的
- 固定种子 42，确保跨环境数据完全可复现；违约率 3%-5%
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.indicators import INDICATOR_ORDER


def _std(x: np.ndarray) -> np.ndarray:
    s = x.std()
    return (x - x.mean()) / s if s > 1e-9 else x * 0.0


def _transfer_probs() -> np.ndarray:
    """流转年限概率（离散 0-20）：未流转较少，3-10 年规范流转为主"""
    p = np.full(21, 0.03)
    p[0] = 0.08  # 未流转（口头/无）
    p[3:11] = 0.08  # 3-10 年规范流转主力
    return p / p.sum()


def generate_samples(n: int = 2000, default_rate: float = 0.04, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # ---------- 指标生成（黑龙江通用，按真实分布）----------
    # 确权耕地总面积（亩）：右偏（对数正态），黑土地规模化，20-3000
    land_area = np.clip(rng.lognormal(mean=np.log(200), sigma=0.8, size=n), 20, 3000)
    # 土地流转合同年限（年）：离散整数 0-20，3-10 年为主
    transfer_years = rng.choice(np.arange(0, 21), n, p=_transfer_probs()).astype(float)
    # 土地流转稳定性：稳定 / 小幅调整 / 频繁变更
    stability = rng.choice(["稳定", "小幅调整", "频繁变更"], n, p=[0.7, 0.2, 0.1])
    # 黑土地保护性耕作面积（亩）：与确权面积相关，黑龙江推广良好
    black_soil = np.clip(land_area * rng.uniform(0.5, 1.0, n), 0, None)
    # 耕地地力保护补贴（元）：与面积相关，稳定现金流（右偏）
    grain_subsidy = np.clip(land_area * rng.uniform(35, 70, n) + rng.normal(0, 3000, n), 0, None)
    # 大型农机购置补贴（元）：规模化经营才有（右偏）
    mach_subsidy = np.clip(land_area * rng.uniform(0, 30, n) + rng.normal(0, 6000, n), 0, 150000)
    # 粮食规模种植专项补贴（元）：千亩连片种植主体
    grain_scale = np.where(land_area > 100, np.clip(land_area * rng.uniform(5, 15, n), 0, 80000), 0.0)
    # 特色经济作物补贴（元）：黑龙江较少，约 20% 主体
    specialty = np.where(
        rng.random(n) < 0.2, np.clip(rng.lognormal(np.log(15000), 0.8, n), 0, 60000), 0.0
    )
    # 农业保险连续投保年限（年）：左偏（beta(2,1)，多数 3-10 年），0-10
    insurance_years = np.clip(rng.beta(2, 1, n) * 10, 0, 10).round(0)
    # 历史保险理赔频次（次）：泊松，多数 0-1 次
    claim_count = rng.poisson(1.2, n).astype(float)
    # 设施农业附加保险：完整投保 / 仅基础险 / 未投保
    facility_ins = rng.choice(["完整投保", "仅基础险", "未投保"], n, p=[0.3, 0.5, 0.2])
    # 主体持续经营年限（年）：右偏，0-30
    years = np.clip(rng.exponential(8, n), 0, 30).round(0)
    # 长期农产品收购订单：年度订单 / 零散收购 / 无稳定渠道
    purchase = rng.choice(["年度订单", "零散收购", "无稳定渠道"], n, p=[0.4, 0.4, 0.2])
    # 农产品年稳定营收（万元）：右偏，与面积相关，5-800
    revenue = np.clip(land_area * rng.uniform(0.05, 0.18, n) + rng.normal(0, 30, n), 5, 800)
    # 历年涉农信贷履约记录：多数无逾期
    credit = rng.choice(["无逾期", "有逾期"], n, p=[0.88, 0.12])

    # ---------- 违约概率（数据生成过程：信用好样本指标整体更优）----------
    stability_score = np.array([{"稳定": 2.0, "小幅调整": 1.0, "频繁变更": -1.0}[s] for s in stability])
    facility_score = np.array([{"完整投保": 1.0, "仅基础险": 0.3, "未投保": -1.0}[s] for s in facility_ins])
    purchase_score = np.array([{"年度订单": 1.5, "零散收购": 0.5, "无稳定渠道": -1.0}[s] for s in purchase])
    credit_score = np.array([{"无逾期": 2.0, "有逾期": -2.0}[c] for c in credit])

    z = (
        0.45 * _std(land_area)  # 确权面积：核心资产
        + 0.18 * _std(transfer_years)  # 流转年限：长期经营意愿
        + 0.22 * _std(stability_score)  # 流转稳定性
        + 0.15 * _std(black_soil)  # 黑土地保护
        + 0.32 * _std(grain_subsidy)  # 地力补贴：稳定现金流
        + 0.18 * _std(mach_subsidy)  # 农机补贴：投入意愿
        + 0.15 * _std(grain_scale)  # 规模种植补贴
        + 0.10 * _std(specialty)  # 特色补贴
        + 0.38 * _std(insurance_years)  # 投保年限：风险意识
        - 0.40 * _std(claim_count)  # 理赔频次：强负面
        + 0.15 * _std(facility_score)  # 设施险
        + 0.20 * _std(years)  # 经营年限
        + 0.22 * _std(purchase_score)  # 收购订单
        + 0.28 * _std(revenue)  # 营收
        + 0.40 * _std(credit_score)  # 信贷履约
        + 0.08 * rng.standard_normal(n)  # 噪声
    )
    z_std = (z - z.mean()) / max(z.std(), 1e-9)

    # 校准：p_default = sigmoid(-(alpha * z_std + beta))，违约率 ≈ default_rate
    alpha = 2.6
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p_tmp = 1.0 / (1.0 + np.exp(alpha * z_std + mid))
        if p_tmp.mean() > default_rate:
            lo = mid
        else:
            hi = mid
    beta = (lo + hi) / 2
    p_default = 1.0 / (1.0 + np.exp(alpha * z_std + beta))
    p_default = np.clip(p_default, 1e-6, 1 - 1e-6)
    default = (rng.random(n) < p_default).astype(int)

    df = pd.DataFrame(
        {
            "land_confirmed_area": land_area.round(1),
            "land_transfer_years": transfer_years,
            "land_transfer_stability": stability,
            "black_soil_protection": black_soil.round(1),
            "grain_subsidy": grain_subsidy.round(0),
            "machinery_subsidy": mach_subsidy.round(0),
            "grain_scale_subsidy": grain_scale.round(0),
            "specialty_crop_subsidy": specialty.round(0),
            "insurance_years": insurance_years,
            "claim_count": claim_count,
            "facility_insurance": facility_ins,
            "years_operating": years,
            "purchase_order": purchase,
            "annual_revenue": revenue.round(1),
            "credit_record": credit,
            "default": default,
        }
    )
    # 保持列顺序与 INDICATOR_ORDER 一致
    df = df[INDICATOR_ORDER + ["default"]]
    return df
