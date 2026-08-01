"""多元统计信用评分卡：IV筛选 → WOE编码 → VIF共线性诊断 → Logistic回归 → 0-1000 分刻度。

对齐商业计划书 3.3.1 技术路线。评分卡刻度公式：
    B = PDO / ln(2)（PDO=50 → B≈72.13）
    Score = base_score + Σ(-B · coef_i · (WOE_i - WOE_mean_i))
其中 base_score 默认 550（评分中心），每指标贡献分 = -B·coef_i·(WOE_i - WOE_mean_i)。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from app.ml.binning import WOEBinner
from app.ml.indicators import CATEGORICAL_FIELDS, INDICATOR_ORDER


class Scorecard:
    def __init__(
        self,
        version: str = "v1.0.0",
        max_bins: int = 5,
        min_bin_pct: float = 0.05,
        min_iv: float = 0.02,
        vif_threshold: float = 10.0,
        pdo: float = 50.0,
        base_score: float = 550.0,
        random_state: int = 42,
        use_smote: bool = True,
    ):
        self.version = version
        self.max_bins = max_bins
        self.min_bin_pct = min_bin_pct
        self.min_iv = min_iv
        self.vif_threshold = vif_threshold
        self.pdo = pdo
        self.base_score = base_score
        self.random_state = random_state
        self.use_smote = use_smote

        self.B = pdo / np.log(2)
        self.A: float = base_score

        self.binners: dict[str, WOEBinner] = {}
        self.feature_names: list[str] = []
        self.woe_means: dict[str, float] = {}
        self.coef: np.ndarray | None = None
        self.intercept: float = 0.0
        self.iv_table: list[dict] = []
        self.vif_table: list[dict] = []
        self.metrics: dict = {}
        self.n_samples: int = 0

    # ---------------------------------------------------------------
    def fit(self, df: pd.DataFrame, target_col: str = "default") -> Scorecard:
        df = df.copy()
        n = len(df)
        self.n_samples = n
        total_bad = int(df[target_col].sum())

        # 1) 全量分箱
        for field in INDICATOR_ORDER:
            binner = WOEBinner(
                field,
                is_categorical=field in CATEGORICAL_FIELDS,
                max_bins=self.max_bins,
                min_bin_pct=self.min_bin_pct,
            )
            binner.fit(df[field], df[target_col])
            self.binners[field] = binner

        # 2) IV 值特征筛选（IV < min_iv 剔除）
        iv_scores = {f: b.iv_ for f, b in self.binners.items()}
        self.iv_table = [
            {"factor": f, "iv": round(iv_scores[f], 6), "nBins": len(self.binners[f].bins_)} for f in INDICATOR_ORDER
        ]
        keep = [f for f in INDICATOR_ORDER if iv_scores[f] >= self.min_iv]
        if not keep:
            # 极端兜底：全部 IV 过低时保留 IV 最高的 3 个
            keep = sorted(INDICATOR_ORDER, key=lambda f: iv_scores[f], reverse=True)[:3]

        # 3) WOE 转换
        woe_df = pd.DataFrame(index=df.index)
        for f in keep:
            woe_df[f] = df[f].apply(self.binners[f].transform)

        # 4) VIF 共线性诊断（逐步剔除 VIF > 阈值）
        selected = self._vif_selection(woe_df, keep)
        self.feature_names = selected

        # 5) 训练 / 测试划分
        X = woe_df[selected].values
        y = df[target_col].values.astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state, stratify=y
        )
        # 保留 SMOTE 前原始训练集（用于 PSI 群体稳定性对比，避免失衡失真）
        X_train_orig = X_train.copy()

        # 5.1) SMOTE 过采样（仅训练集，避免数据泄漏；违约样本合成扩增）
        smote_applied = False
        n_bad_train = int((y_train == 1).sum())
        n_good_train = int((y_train == 0).sum())
        if self.use_smote and 0 < n_bad_train < n_good_train:
            try:
                from imblearn.over_sampling import SMOTE

                smote = SMOTE(random_state=self.random_state)
                X_train, y_train = smote.fit_resample(X_train, y_train)
                smote_applied = True
            except Exception:
                smote_applied = False

        # 6) Logistic 回归（类别平衡 + 正则化）
        lr = LogisticRegression(
            class_weight="balanced",
            C=1.0,
            max_iter=2000,
            random_state=self.random_state,
        )
        lr.fit(X_train, y_train)
        self.coef = lr.coef_[0]
        self.intercept = float(lr.intercept_[0])

        # 7) 评分刻度
        for i, f in enumerate(selected):
            self.woe_means[f] = float(X_train[:, i].mean())
        self.A = self.base_score + self.B * sum(float(self.coef[i]) * self.woe_means[f] for i, f in enumerate(selected))

        # 8) 评估指标（测试集）
        from app.core.config import settings
        from app.ml.evaluate import evaluate_binary

        y_prob = lr.predict_proba(X_test)[:, 1]
        # 业务判定阈值：评分 < 高风险阈值（默认500）视为预测违约，映射回违约概率阈值。
        # 信用评分场景用业务阈值而非 bestThreshold，避免类不平衡下精确率失真。
        high_risk_th = int(settings.HIGH_RISK_THRESHOLD)
        # score = A - B*logit <= high_risk_th  ⟺  logit >= (A-high_risk_th)/B
        # prob = sigmoid(logit)，故业务阈值概率 = sigmoid((A-high_risk_th)/B)
        business_th = float(1.0 / (1.0 + np.exp(-(self.A - high_risk_th) / self.B)))
        self.metrics = evaluate_binary(y_test, y_prob, threshold=business_th)
        self.metrics["businessThreshold"] = round(business_th, 6)
        self.metrics["businessRiskScore"] = high_risk_th
        self.metrics["nSamples"] = n
        self.metrics["nFeatures"] = len(selected)
        self.metrics["defaultRate"] = round(total_bad / n, 4)
        self.metrics["smoteApplied"] = smote_applied
        self.metrics["trainBadBefore"] = n_bad_train
        self.metrics["trainBadAfter"] = int((y_train == 1).sum()) if smote_applied else n_bad_train
        self.metrics["ivTable"] = self.iv_table
        self.metrics["featureImportance"] = [
            {"factor": f, "weight": round(abs(float(self.coef[i])), 4)} for i, f in enumerate(selected)
        ]
        self.metrics["featureNames"] = selected

        # 9) 5 折交叉验证
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        cv_scores = cross_val_score(lr, X, y, cv=cv, scoring="roc_auc")
        self.metrics["cvScores"] = [round(float(s), 4) for s in cv_scores]

        # 10) PSI（SMOTE 前原始训练集 vs 测试集评分分布）
        try:
            from app.ml.evaluate import compute_psi

            orig_train_logit = self.intercept + X_train_orig @ self.coef
            train_score = self.score_from_logit(orig_train_logit)
            test_score = self.score_from_logit(self.intercept + X_test @ self.coef)
            self.metrics["psi"] = round(compute_psi(train_score, test_score), 6)
        except Exception:
            self.metrics["psi"] = None

        return self

    # ---------------------------------------------------------------
    def _vif_selection(self, woe_df: pd.DataFrame, keep: list[str]) -> list[str]:
        from statsmodels.stats.outliers_influence import variance_inflation_factor

        selected = list(keep)
        for _round in range(20):
            if len(selected) <= 2:
                break
            X = woe_df[selected].values
            vifs = []
            for i in range(X.shape[1]):
                try:
                    vifs.append(float(variance_inflation_factor(X, i)))
                except Exception:
                    vifs.append(1.0)
            if max(vifs) <= self.vif_threshold:
                self.vif_table = [{"factor": selected[i], "vif": round(vifs[i], 2)} for i in range(len(selected))]
                break
            # 剔除 VIF 最高的变量
            drop_idx = int(np.argmax(vifs))
            self.vif_table.append({"factor": selected[drop_idx], "vif": round(vifs[drop_idx], 2), "dropped": True})
            del selected[drop_idx]
        return selected

    # ---------------------------------------------------------------
    def woe_vector(self, inputs: dict) -> np.ndarray:
        """输入 dict -> WOE 向量（按 feature_names 顺序）"""
        return np.array([self.binners[f].transform(inputs.get(f)) for f in self.feature_names])

    def logit(self, woe_vec: np.ndarray) -> float:
        return float(self.intercept + np.dot(self.coef, woe_vec))

    def predict_proba(self, inputs: dict) -> float:
        woe = self.woe_vector(inputs)
        return float(1.0 / (1.0 + np.exp(-self.logit(woe))))

    def score_from_logit(self, logit_array: np.ndarray) -> np.ndarray:
        return self.A - self.B * logit_array

    def predict_score(self, inputs: dict) -> float:
        woe = self.woe_vector(inputs)
        return float(np.clip(self.A - self.B * self.logit(woe), 0, 1000))

    def contribution_points(self, inputs: dict) -> dict[str, float]:
        """每指标评分贡献分（可正可负），总和 + base_score = 总分"""
        pts: dict[str, float] = {}
        for i, f in enumerate(self.feature_names):
            woe = self.binners[f].transform(inputs.get(f))
            pts[f] = -self.B * float(self.coef[i]) * (woe - self.woe_means[f])
        return pts
