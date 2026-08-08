#!/bin/bash
# ============================================================
# GitHub Actions 受限部署入口（通过 authorized_keys command= 调用）
# 功能：按分支对齐代码 -> 构建镜像 -> 重建服务
#   main -> /root/race-back-end       (race-backend,      端口 8000)
#   dev  -> /root/race-back-end-dev   (race-backend-dev,  端口 8081)
# 仅允许 main / dev 两个受信分支
# ============================================================
set -e

# 解析分支参数（GitHub Actions 走 $SSH_ORIGINAL_COMMAND；手动走 $1）
BRANCH="main"
if [[ -n "$SSH_ORIGINAL_COMMAND" ]] && [[ "$SSH_ORIGINAL_COMMAND" =~ deploy-backend\.sh[[:space:]]+([A-Za-z0-9_./-]+) ]]; then
  BRANCH="${BASH_REMATCH[1]}"
elif [[ -n "$1" ]] && [[ "$1" != *"deploy-backend.sh"* ]]; then
  BRANCH="$1"
fi
if [[ "$BRANCH" != "main" && "$BRANCH" != "dev" ]]; then
  echo "[deploy] 拒绝非受信分支: $BRANCH"
  exit 1
fi

if [[ "$BRANCH" == "dev" ]]; then
  DIR="/root/race-back-end-dev"
  COMPOSE_ARGS="-f docker-compose.dev.yml"
else
  DIR="/root/race-back-end"
  COMPOSE_ARGS=""
fi

echo "[deploy] $(date '+%F %T') 开始部署分支: $BRANCH -> $DIR"
cd "$DIR"
git fetch origin
git reset --hard "origin/$BRANCH"
echo "[deploy] 代码已对齐 origin/$BRANCH ($(git rev-parse --short HEAD))"

docker compose $COMPOSE_ARGS build backend
docker compose $COMPOSE_ARGS up -d --remove-orphans
echo "[deploy] 服务已按新配置更新"
docker compose $COMPOSE_ARGS ps --format 'table {{.Name}}\t{{.Status}}'

echo "[deploy] 完成 $(date '+%F %T')"
