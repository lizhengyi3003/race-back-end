# 多源数据融合管道（新，替代旧 Phase 3 管道）

> 目标：用真实调查数据（CHFS / CMES / CFPS）训练数据层评分卡，替代旧合成样本。
> 用户决策：完全推倒重建；CHFS + CMES + CFPS **全部接入**；违约标签 A+B 混合；清洗版本 = 文件 + versions.json。
> CFPS 2018/2020/2022 已用 Instructions 密码解密接入（2026-08）。

## 管道流程

```mermaid
flowchart LR
    A[CHFS 2015 dta] --> C[clean_sources.py<br/>按 wave 清洗+版本化]
    B[CMES 2015 dta] --> C
    D[CFPS 2016/2018/2020/2022<br/>famecon] --> C
    C --> E[data/cleaned/{源}_{年份}_{版本}.csv<br/>+ 清洗报告 + versions.json]
    E --> F[fuse_sources.py<br/>纵向堆叠 + 缺失报告]
    F --> G[fused_samples.csv]
    G --> H[train_fused_model.py<br/>A+B 标签 + Scorecard]
    H --> I[data_layer 模型]
```

## 执行顺序（幂等，可重复）

```bash
# Phase 0: 解压 CFPS（2010-2016 无密码；2018/2020/2022 用 Instructions 密码）
python scripts/phase0_extract_cfps.py
python scripts/phase0_build_field_catalog.py     # -> data/samples/field_catalog.csv (9282 条)

# Phase 1: 指标清单 + 自动预匹配（辅助人工，候选仅供参考）
python scripts/phase1_prepare_indicator_catalog.py  # -> indicator_catalog.csv (775 条)
python scripts/phase1_auto_map.py                   # -> mapping_candidates.csv

# Phase 2: 每源/每波清洗 + 版本化（核心映射在 scripts/fusion/mappings.py）
python scripts/fusion/clean_sources.py --sources CMES,CHFS,CFPS --version v1

# Phase 3: 多源融合 + 缺失报告
python scripts/fusion/fuse_sources.py --version v1

# Phase 5: A+B 标签 + 训练（--register 注册 data_layer 模型版本）
python scripts/fusion/train_fused_model.py --version v1 --subset all [--register]
```

## 核心模块（scripts/fusion/）

| 文件 | 职责 |
|---|---|
| `mappings.py` | 核心映射字典（CMES 21 + CHFS 8 + CFPS 5+9 条，9 字段含 wave；clean_rule DSL）、数据源可信度、按 wave 读取字段、入模特征（27 项） |
| `clean_engine.py` | 清洗规则表达式引擎（AST 白名单：clip/sum/div/map/coalesce/fill/mask，防注入） |
| `clean_sources.py` | 每源/每波独立清洗 → data/cleaned/{源}_{年份}_{版本}.csv + 报告 + versions.json（不可变版本） |
| `fuse_sources.py` | 纵向堆叠多源多波样本 + 特征缺失率报告（>50% 建议剔除） |
| `train_fused_model.py` | A+B 标签 + Scorecard 训练 + 评估 + 可选注册 |

## 数据源与波次

| 数据源 | 文件 | 样本量(v1) | 映射 |
|---|---|---|---|
| CMES 2015 | cmes2015_191228.dta | 5,497 | 21 条 |
| CHFS 2015 | chfs2015_master_hh_pub_v1_20260707.dta | 37,289 | 8 条 |
| CFPS 2016 | cfps2016famecon_201807.dta | 14,019 | 5 条 |
| CFPS 2018 | cfps2018famecon_202512.dta | 14,215 | 9 条 |
| CFPS 2020 | cfps2020famecon_202306.dta | 11,620 | 9 条 |
| CFPS 2022 | cfps2022famecon_202410.dta | 10,726 | 9 条 |
| **融合** | fused_samples_v1.csv | **93,366** | 25 指标列 |

## 清洗规则 DSL（clean_rule 示例）
- `clip(2015-{a1006},0,60)` 经营年限（年份相减+截断）
- `div(sum({bi3006},{bi3011}),10000)` 收入加总转万元
- `map({e1014},{1:1,2:0})` 枚举→0/1
- `coalesce({fs101},{fs201})` 多字段取首非空
- `mask({agri_asset},sum({agri_asset},{agri_inc})>0)` 条件掩码

## 违约标签（A+B）
- **A 主标签**：营收/年限/从业/土地（+）与贷款/负债率/民间借款（−）加权，sigmoid 校准违约率 5%
- **B 验证**：真实负面信号（未还贷款/民间借款）与预测分排序一致性（Spearman）

## 当前结果（v1, 全样本 93,366 行）
- 入模特征（缺失率<0.9 自动筛选）12 项：BASIC_008/009/019、01_05、_chfs_agri/_chfs_income、_cfps_agri/_cfps_hus_input/_cfps_private_debt/_cfps_income/_cfps_assets/_cfps_total_asset
- 5 折 CV **AUC 0.7950±0.0025**、KS 0.53、PSI 0.0007；A 标签违约率 5.05%
- **B 验证（防泄漏）Spearman=0.105（p=1.6e-56, n=22,745）**：
  - 真实 `predict_proba` 违约概率（非特征均值占位）
  - 独立真实负面信号 `_cfps_rejected`（CFPS ft8 借款被拒经历，1=被拒/5=未拒，**不入模**，2018plus 三波）
  - 排除与入模特征重叠的信号变量（`_cfps_private_debt` 曾是特征+信号→自相关虚高 0.524，已剔除）
  - 方向正确：被拒过的家庭模型违约概率更高；与早期 CMES 子集（0.103）交叉印证
- 关键特征缺失率已改善：BASIC_019 贷款 5.5%、BASIC_008 营收 15.5%、_cfps_private_debt 45.8%
- 模型产物：data/models/scorecard_v*.pkl（已注册生产 id=6, metrics_json 含 model_type/scoreQuantiles）

## 已知限制与后续迭代
1. **AUC 偏乐观**：合成标签来自同批指标（自我验证），B 验证（0.105）才是与真实信号的参考强度
2. **跨源缺失仍高**：CMES 专属特征（BASIC_003/004/005/0111_*、1041_02）缺失 >90% 被自动剔除；建议单一融合模型（评分卡缺失单独成箱天然处理）或按数据源分客群建模
3. **B 验证信号有限**：当前仅 CFPS ft8（被拒经历）为独立信号；CHFS 信号字段（逾期/违约）待扩展，CMES 信号因全局缺失>90% 被过滤
4. **映射字典待扩展**：当前 35 条核心映射；field_catalog 9,282 字段可人工扩展（mapping_candidates.csv 是候选）
5. **清洗规则 DSL** 需更多算子（if/聚合窗口），可按需扩展 clean_engine
6. 合成样本旧管道（seed.py/indicators.py）仍在生产供主评分卡兜底，清理需确认不影响 AUTO_TRAIN_ON_STARTUP
7. **脚本提交会触发生产部署**（GitHub Actions paths 含 scripts/**），提交前确认不破坏生产评分卡
