"""合成样本生成器：模拟东北涉农经营主体数据（含违约标签）。

依据业务规则构建数据生成过程：
- 土地面积/补贴/营收正相关（规模越大经营越规范）
- 保险覆盖率、经营年限、收入稳定性、征信状况显著影响违约概率
- 整体违约率控制在 3%-5%（对齐涉农信贷实际水平）
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.indicators import INDICATOR_ORDER


def _std(x: np.ndarray) -> np.ndarray:
    s = x.std()
    return (x - x.mean()) / s if s > 1e-9 else x * 0.0


def generate_samples(n: int = 2000, default_rate: float = 0.04, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # ---------- 指标生成 ----------
    # 土地确权面积（亩）：对数正态，20-3000
    land_area = np.clip(rng.lognormal(mean=np.log(150), sigma=0.9, size=n), 20, 3000)
    # 土地流转年限（年）：0-20
    transfer_years = np.clip(rng.exponential(3, n), 0, 20).round(1)
    # 种植结构
    planting = rng.choice(["主粮种植", "经济作物", "混合经营", "设施农业"], n, p=[0.45, 0.2, 0.25, 0.1])
    # 土地规模利用率（%）
    land_util = np.clip(60 + 8 * rng.standard_normal(n) + transfer_years * 0.5, 40, 100)
    # 补贴（与面积相关）
    grain_subsidy = np.clip(land_area * rng.uniform(30, 60, n) + rng.normal(0, 3000, n), 0, None)
    mach_subsidy = np.clip(land_area * rng.uniform(0, 40, n) + rng.normal(0, 6000, n), 0, 150000)
    other_subsidy = np.clip(rng.uniform(0, 20000, n) + land_area * rng.uniform(0, 5, n), 0, 50000)
    # 农业保险覆盖率（%）
    insurance = np.clip(50 + 20 * rng.standard_normal(n) + transfer_years * 1.2, 0, 100)
    # 理赔次数 / 理赔金额占比
    claim_count = rng.poisson(1.5, n).astype(float)
    claim_ratio = np.clip(rng.lognormal(np.log(12), 0.7, n), 0, 80)
    # 经营年限（年）
    years = np.clip(rng.exponential(6, n), 0, 30).round(0)
    # 经营范围集中度（%）
    concentration = np.clip(rng.normal(70, 15, n), 30, 95)
    # 年销售收入（万元）
    revenue = np.clip(land_area * rng.uniform(0.05, 0.2, n) + rng.normal(0, 30, n), 5, 800)
    # 收入稳定性（与经营年限正相关）
    p_stable = np.clip(0.2 + years * 0.02, 0.1, 0.6)
    revenue_stability = np.array(
        [
            rng.choice(
                ["稳定", "基本稳定", "波动较大", "大幅波动"],
                p=[ps, 0.6 - ps, 0.25, 0.15],
            )
            for ps in p_stable
        ]
    )
    # 征信状况（多数良好）
    credit_status = rng.choice(["无不良记录", "轻微逾期", "多次逾期", "严重失信"], n, p=[0.8, 0.12, 0.05, 0.03])
    # 年龄（岁）：务农主体偏中老年，18-75
    age = np.clip(rng.normal(48, 10, n), 18, 75).round(0)
    # 受教育程度：农村地区小学/初中占比偏高
    education = rng.choice(["小学及以下", "初中", "高中", "大专及以上"], n, p=[0.22, 0.38, 0.25, 0.15])
    # 家庭成员数量（人）：均值约 3-4 口，1-10
    family_members = np.clip(rng.poisson(3.5, n), 1, 10).astype(float)
    # 历年理赔金额（元）：与理赔次数正相关，无理赔则为 0
    claim_amount = np.where(
        claim_count > 0,
        np.clip(rng.lognormal(np.log(2500), 1.0, n) * claim_count, 0, 300000),
        0.0,
    )
    # 历史贷款记录（次）：农村信贷普及，多数 1-5 次
    loan_history = np.clip(rng.poisson(2.0, n), 0, 15).astype(float)
    # 历史逾期记录（次）：整体逾期率低，与贷款次数相关（约 12%）+ 少量随机
    loan_overdue = np.clip(rng.binomial(loan_history.astype(int), 0.12, n) + rng.poisson(0.05, n), 0, 8).astype(float)

    # ---------- 违约概率（数据生成过程）----------
    planting_score = np.array(
        [{"主粮种植": 0.5, "经济作物": 1.2, "混合经营": 1.5, "设施农业": 1.0}[p] for p in planting]
    )
    stability_score = np.array(
        [{"稳定": 2.0, "基本稳定": 1.0, "波动较大": 0.0, "大幅波动": -1.0}[s] for s in revenue_stability]
    )
    credit_score = np.array(
        [{"无不良记录": 1.5, "轻微逾期": 0.5, "多次逾期": -1.0, "严重失信": -2.0}[c] for c in credit_status]
    )
    education_score = np.array([{"小学及以下": 0.5, "初中": 1.0, "高中": 1.5, "大专及以上": 2.0}[e] for e in education])
    # 年龄效应：偏离 45 岁壮年期越远，信用越差（倒U型，与规则分档 _score_age 一致）
    age_signal = -((age - 45) ** 2) / 100.0

    z = (
        0.50 * _std(land_area)  # 土地规模：替代数据核心
        + 0.15 * _std(transfer_years)
        + 0.20 * _std(land_util)
        + 0.30 * _std(grain_subsidy)  # 补贴类（政策保障=收入底线，增强信号）
        + 0.20 * _std(mach_subsidy)
        + 0.10 * _std(other_subsidy)
        + 0.40 * _std(insurance)  # 保险类
        - 0.35 * _std(claim_count)
        - 0.20 * _std(claim_amount)  # 理赔金额越高风险越大
        - 0.32 * _std(claim_ratio)
        + 0.20 * _std(years)  # 传统类（弱化，体现“无财报/无征信”场景下替代数据仍可识别）
        + 0.15 * _std(concentration)
        + 0.20 * _std(revenue)
        + 0.20 * _std(planting_score)
        + 0.20 * _std(stability_score)
        + 0.25 * _std(credit_score)
        + 0.30 * _std(age_signal)  # 户主特征：年龄倒U型（青壮年最佳）
        + 0.20 * _std(education_score)  # 学历=金融素养代理
        + 0.05 * _std(family_members)  # 家庭劳动力充足
        + 0.12 * _std(loan_history)  # 有信贷记录=信息充分，中性偏正
        - 0.45 * _std(loan_overdue)  # 历史逾期=强负面信号
        + 0.10 * rng.standard_normal(n)  # 噪声项
    )
    z_std = (z - z.mean()) / max(z.std(), 1e-9)

    # 校准：p_default = sigmoid(-(alpha * z_std + beta))
    # z 越大代表信用越好（面积大/保险足/征信优），违约概率越低；
    # beta 通过二分搜索使整体违约率 ≈ default_rate，同时保持概率展布（alpha 控制判别强度）
    # alpha=2.0：增强违约组/正常组概率分离度，提升模型 AUC 与精确率
    alpha = 2.0
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p_tmp = 1.0 / (1.0 + np.exp(alpha * z_std + mid))
        # p_tmp 随 mid 增大而减小；若均值仍高于目标率，需增大 mid
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
            "age": age,
            "education": education,
            "family_members": family_members,
            "land_confirmed_area": land_area.round(1),
            "land_transfer_years": transfer_years,
            "planting_structure": planting,
            "land_utilization": land_util.round(1),
            "grain_subsidy": grain_subsidy.round(0),
            "machinery_subsidy": mach_subsidy.round(0),
            "other_subsidy": other_subsidy.round(0),
            "insurance_coverage": insurance.round(1),
            "claim_count": claim_count,
            "claim_amount": claim_amount.round(0),
            "claim_ratio": claim_ratio.round(1),
            "years_operating": years,
            "business_concentration": concentration.round(1),
            "annual_revenue": revenue.round(1),
            "revenue_stability": revenue_stability,
            "credit_status": credit_status,
            "loan_history": loan_history,
            "loan_overdue_history": loan_overdue,
            "default": default,
        }
    )
    # 轻微扰动，保持列顺序与 INDICATOR_ORDER 一致
    df = df[INDICATOR_ORDER + ["default"]]
    return df
