#!/bin/bash
# ============================================================
# GitHub Actions 鍙楅檺閮ㄧ讲鍏ュ彛锛堥€氳繃 authorized_keys command= 璋冪敤锛?# 鍔熻兘锛氭寜鍒嗘敮瀵归綈浠ｇ爜 -> 鏋勫缓闀滃儚 -> 閲嶅缓鏈嶅姟
#   main -> /root/race-back-end       (race-backend,      绔彛 8000)
#   dev  -> /root/race-back-end-dev   (race-backend-dev,  绔彛 8081)
# 浠呭厑璁?main / dev 涓や釜鍙椾俊鍒嗘敮
# ============================================================
set -e

# 瑙ｆ瀽鍒嗘敮鍙傛暟锛圙itHub Actions 璧?$SSH_ORIGINAL_COMMAND锛涙墜鍔ㄨ蛋 $1锛?BRANCH="main"
if [[ -n "$SSH_ORIGINAL_COMMAND" ]] && [[ "$SSH_ORIGINAL_COMMAND" =~ deploy-backend\.sh[[:space:]]+([A-Za-z0-9_./-]+) ]]; then
  BRANCH="${BASH_REMATCH[1]}"
elif [[ -n "$1" ]] && [[ "$1" != *"deploy-backend.sh"* ]]; then
  BRANCH="$1"
fi
if [[ "$BRANCH" != "main" && "$BRANCH" != "dev" ]]; then
  echo "[deploy] 鎷掔粷闈炲彈淇″垎鏀? $BRANCH"
  exit 1
fi

if [[ "$BRANCH" == "dev" ]]; then
  DIR="/root/race-back-end-dev"
  COMPOSE_ARGS="-f docker-compose.dev.yml"
else
  DIR="/root/race-back-end"
  COMPOSE_ARGS=""
fi

echo "[deploy] $(date '+%F %T') 寮€濮嬮儴缃插垎鏀? $BRANCH -> $DIR"
cd "$DIR"
git fetch origin
git reset --hard "origin/$BRANCH"
echo "[deploy] 浠ｇ爜宸插榻?origin/$BRANCH ($(git rev-parse --short HEAD))"

docker compose $COMPOSE_ARGS build backend
docker compose $COMPOSE_ARGS up -d --remove-orphans
echo "[deploy] 鏈嶅姟宸叉寜鏂伴厤缃洿鏂?
docker compose $COMPOSE_ARGS ps --format 'table {{.Name}}\t{{.Status}}'

echo "[deploy] 瀹屾垚 $(date '+%F %T')"
