#!/usr/bin/env bash
# 把 src/lib/network_agent 单向同步到共享仓库 kklab_scinet_agents 的 network_agent/ 目录(git subtree,保留提交历史)。
# 用法:bash scripts/sync_shared.sh
#
# 只同步已 commit 的内容;共享仓库里的 network_agent/ 只由本脚本写入,同事不直接改(规则见共享仓库 README)。
# 可用环境变量覆盖:SHARED_REMOTE(共享仓库地址)、SHARED_DIR(共享仓库本地 clone 位置)。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PREFIX=src/lib/network_agent                 # 本仓库中的源目录
TARGET=network_agent                         # 共享仓库中的目标目录
EXPORT_BRANCH=network-agent-export           # 共享仓库里承接拆分历史的分支
SHARED_REMOTE="${SHARED_REMOTE:-git@github.com:ShiningChuang/kklab_scinet_agents.git}"
SHARED_DIR="${SHARED_DIR:-$REPO_ROOT/../kklab_scinet_agents}"

if [ -n "$(git status --porcelain -- "$PREFIX")" ]; then
    echo "!! $PREFIX 有未提交的改动,未提交部分不会被同步。先 commit 再运行。" >&2
    exit 1
fi

echo "==> [1/3] 拆分 $PREFIX 的历史 → 本地分支 $EXPORT_BRANCH"
git subtree split -q --prefix="$PREFIX" -b "$EXPORT_BRANCH" >/dev/null   # 分支已存在时增量更新
git push -q "$SHARED_REMOTE" "$EXPORT_BRANCH:$EXPORT_BRANCH"

echo "==> [2/3] 共享仓库本地 clone:$SHARED_DIR"
[ -d "$SHARED_DIR/.git" ] || git clone -q "$SHARED_REMOTE" "$SHARED_DIR"
cd "$SHARED_DIR"
git fetch -q origin
if ! git rev-parse -q --verify origin/main >/dev/null; then
    echo "!! 共享仓库还没有 main 分支(subtree add 需要已有提交),先推一个初始提交。" >&2
    exit 1
fi
git checkout -q main && git pull -q --ff-only origin main
if [ -n "$(git status --porcelain)" ]; then
    echo "!! $SHARED_DIR 有未提交的改动,先处理再同步。" >&2
    exit 1
fi

echo "==> [3/3] 并入 $TARGET/ 并推送 main"
if [ -d "$TARGET" ]; then
    git subtree pull -q --prefix="$TARGET" origin "$EXPORT_BRANCH" -m "同步 network_agent($(git -C "$REPO_ROOT" rev-parse --short HEAD))"
else
    git subtree add -q --prefix="$TARGET" origin "$EXPORT_BRANCH"
fi
git push -q origin HEAD:main
echo "完成:$(git log --oneline -1)"
