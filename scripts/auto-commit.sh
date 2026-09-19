#!/usr/bin/env bash
# 文件变化自动提交并推送
# 用法: ./scripts/auto-commit.sh [提交信息前缀]
#   有 inotifywait(Linux) / fswatch(macOS) 就用事件监听, 否则每 10 秒轮询
set -u
cd "$(dirname "$0")/.." || exit 1

BRANCH=$(git branch --show-current)
MSG_PREFIX="${1:-auto: 更新代码}"

auto_push() {
  [ -z "$(git status --porcelain)" ] && return 0
  git add -A
  git diff --cached --quiet && return 0
  STAMP=$(date '+%Y-%m-%d %H:%M:%S')
  git commit -m "${MSG_PREFIX} (${STAMP})" && git push origin "${BRANCH}"
}

echo "自动提交监听中, 分支: ${BRANCH}, Ctrl+C 退出"

if command -v inotifywait >/dev/null 2>&1; then
  while true; do
    inotifywait -r -e modify,create,delete,move --exclude '(^|/)\.git/' . >/dev/null 2>&1
    sleep 2 # 简单防抖
    auto_push || echo "[$(date '+%H:%M:%S')] 提交/推送失败, 等待下次变化重试"
  done
elif command -v fswatch >/dev/null 2>&1; then
  fswatch -r --exclude '\.git/' . | while read -r _; do
    sleep 2
    auto_push || echo "[$(date '+%H:%M:%S')] 提交/推送失败, 等待下次变化重试"
  done
else
  echo "未找到 inotifywait / fswatch, 使用轮询模式(每 10 秒)"
  while true; do
    sleep 10
    auto_push || true
  done
fi
