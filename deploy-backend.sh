#!/bin/bash
# ============================================================
# GitHub Actions 受限部署入口（通过 authorized_keys command= 调用）
# 功能：对齐远端代码 → 构建镜像 → 按新配置重建/更新全部服务
# 支持分支：通过 $SSH_ORIGINAL_COMMAND 传入，例如 "deploy-backend.sh dev"
#          （未传则默认 main；仅允许 main / dev 两个受信分支）
# 服务器端构建依赖国内镜像源（/etc/docker/daemon.json registry-mirrors）
# 及已缓存的基础镜像（python:3.13-slim / node:22-alpine），否则构建很慢。
# ============================================================
set -e
cd /root/race-back-end

# 解析分支参数：
# 1) 受限密钥路径（GitHub Actions）：原始命令放入 $SSH_ORIGINAL_COMMAND，
#    形如 "deploy-backend.sh dev"；
# 2) 手动测试路径：命令行参数 $2（ssh root@server deploy-backend.sh dev）
BRANCH="main"
if [[ -n "$SSH_ORIGINAL_COMMAND" ]] && [[ "$SSH_ORIGINAL_COMMAND" =~ deploy-backend\.sh[[:space:]]+([A-Za-z0-9_./-]+) ]]; then
  BRANCH="${BASH_REMATCH[1]}"
elif [[ -n "$2" ]]; then
  BRANCH="$2"
fi
if [[ "$BRANCH" != "main" && "$BRANCH" != "dev" ]]; then
  echo "[deploy] 拒绝非受信分支: $BRANCH"
  exit 1
fi

echo "[deploy] $(date '+%F %T') 开始部署分支: $BRANCH"
git fetch origin
git reset --hard "origin/$BRANCH"
echo "[deploy] 代码已对齐 origin/$BRANCH ($(git rev-parse --short HEAD))"

docker compose build backend
docker compose up -d --remove-orphans
echo "[deploy] 服务已按新配置更新"
docker compose ps --format 'table {{.Name}}\t{{.Status}}'

echo "[deploy] 完成 $(date '+%F %T')"
