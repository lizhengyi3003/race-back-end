"""构建代理样本数据集：从 CMES/CHFS 提取映射字段 → 指标编码特征矩阵 + 合成违约标签。

流程：
1. 读 CMES 农业板块字段（bi*）与 CHFS master_hh 字段
2. 按 build_mapping.py 的 transform 规则映射到指标编码
3. 依据风险因子生成合成违约标签（真实数据无违约标注，用可解释规则评分校准 3%-5% 违约率）
4. 输出 data/samples/proxy_samples.csv（列 = 指标编码 + default + source）

数据层评分卡训练（Phase 3 第 2 步）直接读此 CSV。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "samples" / "proxy_samples.csv"


# ---------- CMES 需要读取的字段 ----------
CMES_FIELDS = [
    "a1006",  # 实际经营开始年份
    "c1002",  # 目前员工数
    "bi2101",  # 土地面积
    "bi2101a",  # 流转承包面积
    "bi2104",  # 土地流转合同平均期限（年）
    "bi3001_1", "bi3001_2", "bi3001_3", "bi3001_4", "bi3001_6", "bi3001_7",  # 种植面积
    "bi3001_14", "bi3001_15",  # 蔬菜/水果面积
    "bi3006",  # 去年农产品销售收入
    "bi3011",  # 牲畜/水产销售收入
    "bi4004",  # 是否有利润/分红
    "e1014",  # 是否有未还清银行贷款
    "e1021",  # 总贷款金额
    "e1023",  # 最大贷款金额
    "e1045",  # 是否有未还清民间借款
    "bi2204",  # 采购农资时是否有赊销或借款
]

# ---------- CHFS 需要读取的字段 ----------
CHFS_FIELDS = [
    "total_income", "agri_inc", "busi_inc",
    "agri_asset", "land_asset", "busi_asset",
    "agri_debt", "busi_debt", "total_asset", "total_debt",
    "rural", "region", "prov", "hhid",
]

TARGET_RATE = 0.05  # 目标违约率


def _to_num(v) -> float | None:
    if pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _std(s: pd.Series) -> pd.Series:
    x = s.astype(float)
    return (x - x.mean()) / (x.std() + 1e-9)


def build_cmes() -> pd.DataFrame:
    path = RAW / "cmes" / "cmes2015_191228.dta"
    if not path.exists():
        print("[跳过] CMES 主表缺失")
        return pd.DataFrame()
    print("读取 CMES 字段...")
    df = pd.read_stata(path, columns=CMES_FIELDS)
    df = df.dropna(subset=["bi3006", "a1006"], how="all")
    n = len(df)
    print(f"  CMES 样本：{n}")

    out = pd.DataFrame(index=df.index)
    # 基本项
    out["BASIC_003"] = (2015 - df["a1006"]).clip(0, 60)  # 注册成立年限
    out["BASIC_004"] = (2015 - df["a1006"]).clip(0, 60)  # 实际经营年限
    out["BASIC_005"] = df["c1002"].fillna(0)  # 从业人员数
    # 营收（万元）
    rev = df["bi3006"].fillna(0) + df["bi3011"].fillna(0)
    out["BASIC_008"] = (rev / 10000).round(1)
    # 土地面积（亩）
    area = df["bi2101"].fillna(df["bi2101a"])
    out["01_05"] = area.fillna(0).round(1)
    # 谷物播种面积
    grain = (
        df["bi3001_1"].fillna(0) + df["bi3001_2"].fillna(0)
        + df["bi3001_3"].fillna(0) + df["bi3001_4"].fillna(0)
        + df["bi3001_6"].fillna(0)
    )
    out["0111_01"] = grain.fillna(0).round(1)
    out["0111_05"] = df["bi3001_3"].fillna(0).round(1)  # 玉米面积
    out["0111_08"] = df["bi3001_1"].fillna(0).round(1)  # 粳稻面积
    out["0112_04"] = df["bi3001_6"].fillna(0).round(1)  # 大豆面积
    # 贷款（万元）
    out["BASIC_019"] = (df["e1021"].fillna(0) / 10000).round(1)
    out["1041_02"] = (df["e1023"].fillna(0) / 10000).round(1)
    # 枚举/布尔转数值代理（供评分卡用）
    out["_cmes_had_loan"] = df["e1014"].map({1: 1, 2: 0}).fillna(0)
    out["_cmes_profit"] = df["bi4004"].map({1: 1, 2: 0}).fillna(0.5)
    out["_cmes_credit"] = df["e1045"].map({1: 1, 2: 0}).fillna(0)  # 民间借款=负面
    out["_cmes_purchase_credit"] = df["bi2204"].map({1: 1, 2: 0}).fillna(0)
    out["source"] = "CMES"
    return out


def build_chfs(years: list[str]) -> pd.DataFrame:
    frames = []
    for y in years:
        path = next((RAW / "chfs").glob(f"chfs{y}_master_hh*.dta"), None)
        if not path:
            continue
        print(f"读取 CHFS {y}...")
        df = pd.read_stata(path, columns=CHFS_FIELDS)
        df = df.dropna(subset=["total_income", "agri_inc"], how="all")
        out = pd.DataFrame(index=df.index)
        # 家庭农场代理：有农业资产或农业收入的家庭
        is_agri = (df["agri_asset"].fillna(0) > 0) | (df["agri_inc"].fillna(0) > 0)
        out["BASIC_008"] = ((df["agri_inc"].fillna(0) + df["busi_inc"].fillna(0)) / 10000).round(1)
        out["01_05"] = df["land_asset"].fillna(0).round(1)  # 土地资产代理
        out["BASIC_019"] = ((df["agri_debt"].fillna(0) + df["busi_debt"].fillna(0)) / 10000).round(1)
        out["BASIC_009"] = (df["total_debt"] / (df["total_asset"] + 1) * 100).fillna(0).round(1)
        out["_chfs_agri"] = is_agri.astype(int)
        out["_chfs_income"] = df["total_income"].fillna(0) / 10000
        out["source"] = f"CHFS{y}"
        frames.append(out)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def assign_labels(df: pd.DataFrame) -> pd.DataFrame:
    """按可解释风险因子合成违约标签，校准违约率≈5%。

    风险信号：营收越高/经营越久/面积越大 → 信用越好；贷款/负债越高 → 信用越差。
    用较强系数保证模型可学到真实判别信号（Phase 3 数据层演示）。
    """
    rng = np.random.default_rng(42)
    z = pd.Series(0.0, index=df.index)
    if "BASIC_008" in df.columns:
        z += 0.40 * _std(df["BASIC_008"].fillna(df["BASIC_008"].median()))
    if "BASIC_003" in df.columns:
        z += 0.28 * _std(df["BASIC_003"].fillna(df["BASIC_003"].median()))
    if "BASIC_005" in df.columns:
        z += 0.16 * _std(df["BASIC_005"].fillna(df["BASIC_005"].median()))
    if "01_05" in df.columns:
        z += 0.20 * _std(df["01_05"].fillna(df["01_05"].median()))
    if "BASIC_019" in df.columns:
        z += -0.45 * _std(df["BASIC_019"].fillna(0))  # 贷款余额高=风险
    if "BASIC_009" in df.columns:
        z += -0.45 * _std(df["BASIC_009"].fillna(0))  # 资产负债率高=风险
    for col in ["_cmes_credit", "_cmes_purchase_credit"]:
        if col in df.columns:
            z += -0.30 * df[col].fillna(0)
    z += 0.04 * rng.standard_normal(len(df))
    z = (z - z.mean()) / (z.std() + 1e-9)

    # sigmoid 校准（与 seed.py 同法，alpha 加大使区分更尖锐）
    alpha = 3.0
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if (1 / (1 + np.exp(alpha * z + mid))).mean() > TARGET_RATE:
            lo = mid
        else:
            hi = mid
    beta = (lo + hi) / 2
    p = np.clip(1 / (1 + np.exp(alpha * z + beta)), 1e-6, 1 - 1e-6)
    df["default"] = (rng.random(len(df)) < p).astype(int)
    return df


if __name__ == "__main__":
    parts = []
    cmes_df = build_cmes()
    if not cmes_df.empty:
        parts.append(cmes_df)
    chfs_df = build_chfs(years=["2021", "2015"])
    if not chfs_df.empty:
        parts.append(chfs_df)
    if not parts:
        print("无可用数据源")
        sys.exit(1)
    data = pd.concat(parts, ignore_index=True)
    data = assign_labels(data)
    # 仅保留农业相关样本（CMES 农业板块 / CHFS 有农业资产）减少噪音
    if "_chfs_agri" in data.columns:
        data = data[(data["source"] == "CMES") | (data["_chfs_agri"] == 1)]
    data = data.dropna(subset=["BASIC_008"])
    data = data.reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"✅ 代理样本 {len(data)} 条 → {OUT}")
    print(f"   违约率：{data['default'].mean() * 100:.2f}%")
    print(f"   来源分布：{dict(data['source'].value_counts())}")
    print(f"   指标列：{', '.join([c for c in data.columns if c.startswith(('B','0','1'))])}")
