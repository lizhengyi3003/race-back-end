# 涉农信贷风险智能评估系统 · 后端管理平台

> 挑战杯创业计划竞赛（东北振兴产业升级专项赛）· 数智赋能产业组
> 基于多元统计模型的涉农小微企业信贷风险智能评估系统

本仓库为项目**后端 + 完整可视化后台管理平台**，包含：

- **信用评分卡引擎**：IV 特征筛选 → WOE 编码 → VIF 共线性诊断 → Logistic 回归 → 0-1000 分评分卡（参考 `toad`/`optbinning`/`scorecardpy` 方法自研实现，Python 开源生态）
- **后端 API 服务**：FastAPI + SQLAlchemy 2.0 + MySQL 8.0（可选 SQLite 轻量演示）
- **后台管理平台**（`admin-web/`，Vue3 + Element Plus）：登录、系统概览、数据管理、模型训练与评估、API 管理（列表/日志/测试控制台）、系统监控（服务器/数据库/健康检查）、数据导入导出
- **竞赛前端对接**：`fore-end/`（同级目录）已从模拟模型切换为调用本后端真实 API

---

## 目录结构

```
back-end/
├── app/                    # 后端主程序
│   ├── main.py             # FastAPI 入口（启动初始化 + 自动训练 + 挂载管理端）
│   ├── core/               # 配置 / JWT安全 / 异常 / 统一响应
│   ├── db/                 # SQLAlchemy 引擎与会话、初始化
│   ├── models/             # User / AssessmentRecord / ModelVersion / SystemConfig / ApiLog
│   ├── schemas/            # Pydantic 模型（对齐前端契约）
│   ├── api/v1/             # auth / risk / dashboard / model / data / admin / monitor
│   ├── services/           # 业务逻辑层
│   ├── ml/                 # ★ 评分卡核心：分箱WOE/IV、评分卡、评估、预测、种子数据
│   └── middleware/         # API 请求日志中间件
├── admin-web/              # 后台管理平台前端（Vue3 + Element Plus + ECharts）
├── scripts/                # init_db / seed_data / train_model / import_csv
├── data/                   # 数据库文件、模型文件、合成样本
├── tests/                  # pytest 测试（26 项）
├── Dockerfile              # 多阶段构建（前端 + 后端）
└── docker-compose.yml      # backend + MySQL 一键启动
```

---

## 快速开始（本地开发）

### 1. 环境准备

- Python 3.13+（Docker 镜像 `python:3.13-slim`）
- Node.js 20.19+（构建管理前端，Vite 8 要求，Docker 镜像 `node:22-alpine`）

### 2. 后端启动

```bash
cd back-end

# 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# 初始化数据库（建表 + 默认管理员 admin/admin123 + 默认配置）
python scripts/init_db.py

# （可选）生成合成样本 + 训练评分卡
python scripts/seed_data.py
python scripts/train_model.py

# 启动服务（启动时若无模型会自动训练）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：

| 地址 | 说明 |
|---|---|
| http://localhost:8000/admin | 后台管理平台（需先 `npm run build` 构建 admin-web） |
| http://localhost:8000/docs | Swagger 接口文档 |
| http://localhost:8000/ | 服务信息 |

### 3. 管理前端（开发模式）

```bash
cd back-end/admin-web
npm install
npm run dev          # http://localhost:5173（已代理 /api → localhost:8000）
```

生产构建（FastAPI 自动挂载到 `/admin`）：

```bash
cd back-end/admin-web
npm run build        # 产物在 admin-web/dist，重启后端即可访问 /admin
```

### 4. 竞赛前端（fore-end）

```bash
cd ../fore-end
npm install
npm run dev          # http://localhost:5174（已代理 /api → localhost:8000）
```

> 🔐 **邀约制登录**：本系统不开放注册，账号由后台管理平台（admin-web「用户管理」）统一开通。默认管理员 `admin/admin123` 登录管理端后，可在「数据管理 → 用户管理」创建分析师账号，再用于竞赛前端登录。登录态保存在浏览器 `localStorage`，刷新页面自动恢复。

---

## 数据库配置（MySQL / SQLite）

项目默认使用 **MySQL 8.0**（生产部署推荐），SQLite 可用于轻量演示：

1. 复制 `.env.example` 为 `.env`，修改 `DATABASE_URL` 中的账号密码：

```
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/race?charset=utf8mb4
```

2. 先创建数据库：`CREATE DATABASE race DEFAULT CHARACTER SET utf8mb4;`
3. 重新 `python scripts/init_db.py`

> 代码完全兼容两种数据库（SQLAlchemy 方言自动适配），切换仅需改一行配置。

---

## 信用评分卡技术方案

对齐商业计划书 3.3 节技术路线：

```
21项替代数据指标（六大类：户主特征/土地经营/农业补贴/农业保险/经营稳定性/贷款历史）
  → WOE 分箱（分位数初分箱 + 低频箱合并 + 坏账率单调性校正）
  → IV 值特征筛选（IV < 0.02 剔除）+ VIF 共线性诊断（>10 剔除）
  → Logistic 回归（class_weight 平衡违约样本）
  → 评分卡刻度：B = PDO/ln2，Score = 550 + Σ(-B·βᵢ·(WOEᵢ - meanᵢ))
  → 业务阈值分级：≥700 低风险 / 500-700 中等 / <500 高风险（可在管理平台调整）
```

模型验证：AUC / KS / 混淆矩阵 / 召回率 / 5 折交叉验证 / PSI，训练指标在管理平台可视化展示（ROC 曲线、KS 曲线、IV 条形图、混淆矩阵热力图）。

小样本与极端场景应对（对齐商业计划书 3.3.1）：
- **SMOTE 过采样**：对违约样本合成扩增（仅训练集，避免数据泄漏），缓解违约率 3%-5% 的样本不平衡
- **兜底规则**：连续两年绝收、土地大面积荒芜、重大自然灾害等极端客户，无论模型评分如何，强制标记高风险并提示人工复核
- **模型监控**：PSI 群体稳定性监控（训练分布 vs 实际客群），样本不足或显著偏移时触发再校准预警
- **业务仿真验证**：模拟干旱减产、粮价下跌、补贴退坡、突发灾情等极端场景，量化客群风险迁移
- **三组对比实验**：替代数据 vs 传统信用数据、原始变量/WOE/分组PCA 特征方案、涉农专属 vs 通用模型

合成样本由 `app/ml/seed.py` 按农业业务规则生成（土地面积/补贴/保险/经营年限分布 + 违约标签，违约率约 3%-5%），用于竞赛演示阶段模型训练与验证。

---

## 后台管理平台功能

| 模块 | 功能 |
|---|---|
| 系统概览 | 统计卡片（用户/记录/模型/API调用）、服务健康、评估趋势、评分分布、行业分布 |
| 数据管理 | 评估记录（搜索/筛选/详情/删除/导出）、用户管理（CRUD/重置密码/角色）、系统配置（阈值/利率） |
| 模型管理 | 训练评分卡（SMOTE 过采样 + 样本量可选）、指标看板（AUC/KS/混淆矩阵/ROC/KS曲线/IV图/5折CV）、**三组对比实验**（替代数据vs传统/WOE vs 分组PCA/涉农专属vs通用）、模型版本历史 |
| 模型监控 | PSI 群体稳定性、实际客群评分分布、客群迁移预警、模型再校准触发提示 |
| 业务仿真验证 | 极端场景模拟（干旱减产/粮价下跌/补贴退坡/突发灾情），观察评分与风险等级迁移 |
| API 管理 | 接口列表（OpenAPI 聚合）、接口日志（耗时/状态/请求响应）、接口测试控制台 |
| 系统监控 | 服务器状态（CPU/内存/磁盘实时曲线）、数据库状态（表/容量）、健康检查探针 |
| 数据管理工具 | CSV 模板下载、批量导入自动评估、评估记录导出 |

---

## API 一览（前缀 `/api/v1`）

| 模块 | 接口 | 说明 | 鉴权 |
|---|---|---|---|
| 认证 | `POST /auth/login` / `GET /auth/me` | 登录 / 当前用户 | 公开 / 需登录 |
| 风险评估 | `POST /risk/assess` | 提交评估（评分卡输出） | 公开 |
| 评估记录 | `GET /risk/records` `GET/DELETE /risk/records/{id}` | 记录管理 | 需登录 |
| 数据看板 | `GET /dashboard/stats` `/industry-distribution` `/score-distribution` `/trend` | 统计 | 公开 |
| 模型管理 | `GET /model/info` `POST /model/train` `GET /model/metrics` `GET/PUT /model/thresholds` `GET /model/monitor` `GET /model/simulate` | 训练/监控/仿真与配置 | 需登录 |
| 数据管理 | `GET /data/template` `POST /data/import` `GET /data/export` | 导入导出 | 需登录 |
| 管理平台 | `GET /admin/stats` `/users` `/api-logs` `/api-spec` `/configs` | 系统管理 | 需登录 |
| 系统监控 | `GET /monitor/server` `/database` `/health` | 服务器/数据库/健康 | 需登录 |

统一响应格式：`{ "code": 200, "message": "success", "data": ... }`（前端以 `code` 判断成败）。

---

## 测试

```bash
cd back-end
.venv\Scripts\python.exe -m pytest tests -v
```

覆盖：认证、风险评估契约（对齐前端契约，21 项指标）、模型训练指标、监控与管理接口（26 项用例）。

---

## 部署

### 1. 竞赛前端（fore-end）→ Cloudflare Pages

1. 在 `fore-end/.env.production` 中配置后端 API 地址：
   ```
   VITE_API_BASE_URL=https://<后端域名>/api/v1
   ```
2. 在 Cloudflare Pages 创建项目，构建命令 `npm run build`，输出目录 `dist`（项目使用 Hash 路由，无需配置 SPA rewrite 规则）。
3. 部署后访问 `https://<your-project>.pages.dev`。

### 2. 后端 + 管理端 → 服务器 Docker

```bash
cd back-end
docker compose up -d --build
```

- `mysql` 服务：MySQL 8.0，数据卷持久化
- `backend` 服务：多阶段构建（前端构建 + 后端），自动挂载管理端到 `/admin`，启动自动初始化并训练模型
- 访问 http://<服务器IP>:8000/admin

服务器部署步骤：
1. 修改 `.env`：`DATABASE_URL` 指向服务器 MySQL、`JWT_SECRET_KEY` 换随机串、`CORS_ORIGINS` 填入 Cloudflare Pages 域名
2. `docker compose up -d --build`
3. （可选）配置 Nginx/Caddy 反代 HTTPS，并将域名解析到服务器

---

## 代码风格与质量检查

全项目统一代码风格，提交前请执行：

**后端（Python，ruff 0.16+）**

```bash
cd back-end
.venv\Scripts\python.exe -m ruff check app scripts tests
.venv\Scripts\python.exe -m ruff format app scripts tests
.venv\Scripts\python.exe -m pytest tests -q
```

**前端（admin-web / fore-end，ESLint + Prettier）**

```bash
cd admin-web        # 或 fore-end
npm run lint        # eslint . --max-warnings=0
npm run format      # prettier --write
npm run build       # vue-tsc + vite 构建验证
```

约定：行宽 120、Python 缩进 4 空格 / 前端 2 空格、UTF-8 + LF、文件末尾换行（见 `.editorconfig`）；两端统一「农业绿」主题（`#2c6e49`）。

---

## 默认账号

| 角色 | 账号 | 密码 |
|---|---|---|
| 管理员 | `admin` | `admin123` |
| 分析师 | `analyst1` | `analyst123`（示例，由管理员在管理端创建） |

> ⚠️ 生产部署前请修改 `.env` 中 `JWT_SECRET_KEY` 与默认管理员密码。

---

## 版权与致谢

- 评分卡方法参考：`Toad-Dev-Group/toad`、`carlo58/optbinning`、`ShichenXie/scorecardpy`
- 后端结构参考：`tiangolo/full-stack-fastapi-template`
- 管理端结构参考：`PureAdmin`、`SoybeanAdmin` 等开源后台模板思路
