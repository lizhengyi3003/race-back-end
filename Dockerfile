# ---------- 阶段 1：构建管理前端 admin-web ----------
FROM node:22-alpine AS admin-build
WORKDIR /admin
COPY admin-web/package*.json ./
# 国内服务器访问 npmjs 慢，用 npmmirror 加速
RUN npm config set registry https://registry.npmmirror.com && npm install --no-audit --no-fund
COPY admin-web/ ./
RUN npm run build

# ---------- 阶段 2：后端运行镜像 ----------
FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 依赖（国内服务器用清华 PyPI 镜像加速）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 后端代码
COPY app ./app
COPY scripts ./scripts

# 管理前端构建产物（FastAPI 自动挂载到 /admin）
COPY --from=admin-build /admin/dist ./admin-web/dist

# 数据目录
RUN mkdir -p data/models data/samples

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
