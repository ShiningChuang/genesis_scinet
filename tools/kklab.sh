#!/usr/bin/env bash
# 管理共享仓库 kklab_scinet_agents(本仓库中的 submodule:external/kklab_scinet_agents)。
# 规则与注意事项见 tools/manage_kklab_scinet_agents.md。
#
# 用法:
#   bash tools/kklab.sh setup                 一次性:加入 submodule、切到 main、提交 gitlink
#   bash tools/kklab.sh sync                  把 src/lib/network_agent 单向同步到共享仓库的 network_agent/
#   bash tools/kklab.sh begin                 修改共享文件前:submodule 切到 main 并拉到最新
#   bash tools/kklab.sh finish "<提交说明>"     修改共享文件后:提交并推送 submodule,再提交本仓库的 gitlink
#   bash tools/kklab.sh status                查看 submodule 分支、未推送提交、network_agent 是否已同步
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

REMOTE="${KKLAB_REMOTE:-git@github.com:ShiningChuang/kklab_scinet_agents.git}"
SUB=external/kklab_scinet_agents             # submodule 位置
PREFIX=src/lib/network_agent                 # 本仓库中 network agent 的源目录
TARGET=network_agent                         # 共享仓库中的目标目录(只由 sync 写入)
EXPORT_BRANCH=network-agent-export           # 承接 subtree 拆分历史的分支(本地 + 共享仓库各一个,勿删)
OLD_CLONE="$REPO_ROOT/../kklab_scinet_agents"  # 改用 submodule 之前的独立 clone

die() { echo "!! $*" >&2; exit 1; }

require_sub() {
    [ -e "$SUB/.git" ] || die "submodule 未初始化:首次运行 bash tools/kklab.sh setup;新 clone 后运行 git submodule update --init $SUB"
}

sub_on_main() {  # submodule 默认处于 detached HEAD,修改或合并前必须切回 main
    git -C "$SUB" fetch -q origin
    git -C "$SUB" checkout -q main
    git -C "$SUB" pull -q --ff-only origin main
}

commit_gitlink() {  # 在本仓库只提交 submodule 指针,不带上其他已暂存的改动
    if git diff --quiet HEAD -- "$SUB"; then
        echo "submodule 指针无变化,本仓库无需提交"
        return
    fi
    git add "$SUB"
    git commit -q -m "$1" -- "$SUB"
    echo "本仓库已提交指针:$(git log --oneline -1)(未 push)"
}

cmd_setup() {
    if [ -e "$SUB/.git" ]; then
        echo "submodule 已存在:$SUB"
    else
        git submodule add -q -f -b main "$REMOTE" "$SUB"   # external/* 被 .gitignore 忽略,需 -f
    fi
    sub_on_main
    git add .gitmodules "$SUB"
    if git diff --cached --quiet -- .gitmodules "$SUB"; then
        echo "gitlink 与 .gitmodules 无变化"
    else
        git commit -q -m "external/kklab_scinet_agents:共享仓库以 submodule 接入" -- .gitmodules "$SUB"
        echo "本仓库已提交:$(git log --oneline -1)(未 push)"
    fi
    if [ -d "$OLD_CLONE/.git" ]; then
        if [ -z "$(git -C "$OLD_CLONE" status --porcelain)" ] && \
           [ -z "$(git -C "$OLD_CLONE" log --oneline '@{u}..' 2>/dev/null)" ]; then
            echo "旧的独立 clone 没有未提交或未推送的内容,可以删除:rm -rf \"$OLD_CLONE\""
        else
            echo "!! 旧的独立 clone $OLD_CLONE 有未提交或未推送的内容,处理完再删除"
        fi
    fi
}

cmd_sync() {
    require_sub
    [ -z "$(git status --porcelain -- "$PREFIX")" ] || die "$PREFIX 有未提交的改动,未提交部分不会被同步。先 commit。"
    [ -z "$(git -C "$SUB" status --porcelain)" ] || die "$SUB 有未提交的改动(可能 begin 之后还没 finish),先处理。"

    echo "==> [1/4] 拆分 $PREFIX 的历史 → $EXPORT_BRANCH,推到共享仓库"
    git subtree split -q --prefix="$PREFIX" -b "$EXPORT_BRANCH" >/dev/null   # 分支已存在时增量更新
    git push -q "$REMOTE" "$EXPORT_BRANCH:$EXPORT_BRANCH"

    echo "==> [2/4] submodule 切到 main 并拉到最新"
    sub_on_main

    echo "==> [3/4] 并入 $TARGET/ 并推送共享仓库 main"
    local src_rev
    src_rev="$(git rev-parse --short HEAD)"
    (
        cd "$SUB"
        if [ -d "$TARGET" ]; then
            git subtree pull -q --prefix="$TARGET" origin "$EXPORT_BRANCH" -m "同步 network_agent(genesis_scinet $src_rev)"
        else
            git subtree add -q --prefix="$TARGET" origin "$EXPORT_BRANCH"
        fi
        git push -q origin main
    )

    echo "==> [4/4] 更新本仓库记录的 submodule 指针"
    commit_gitlink "external/kklab_scinet_agents:同步 network_agent(genesis_scinet $src_rev)"
}

cmd_begin() {
    require_sub
    [ -z "$(git -C "$SUB" status --porcelain)" ] || die "$SUB 已有未提交的改动;改完了就运行 finish"
    sub_on_main
    echo "submodule 已在 main:$(git -C "$SUB" log --oneline -1)"
    echo "可以修改 $SUB 下的 resources/、README 等;不要改 $TARGET/。改完运行:bash tools/kklab.sh finish \"<提交说明>\""
}

cmd_finish() {
    require_sub
    local msg="${1:-}"
    [ -n "$msg" ] || die '用法:bash tools/kklab.sh finish "<提交说明>"'
    [ "$(git -C "$SUB" rev-parse --abbrev-ref HEAD)" = main ] || \
        die "submodule 不在 main(detached HEAD),先运行 begin。若已在 detached HEAD 上提交过,见文档「找回 detached HEAD 上的提交」"
    git -C "$SUB" fetch -q origin
    if [ -n "$(git -C "$SUB" status --porcelain -- "$TARGET")" ] || \
       ! git -C "$SUB" diff --quiet origin/main HEAD -- "$TARGET"; then
        die "$TARGET/ 不能在共享仓库里改(只由 sync 写入)。撤销:git -C $SUB checkout origin/main -- $TARGET;要改请在 $PREFIX 里改再 sync"
    fi
    if [ -z "$(git -C "$SUB" status --porcelain)" ] && [ -z "$(git -C "$SUB" log --oneline origin/main..HEAD)" ]; then
        die "submodule 里没有要提交的改动"
    fi
    git -C "$SUB" add -A
    git -C "$SUB" diff --cached --quiet || git -C "$SUB" commit -q -m "$msg"
    git -C "$SUB" pull -q --rebase origin main    # 同事可能刚推过
    git -C "$SUB" push -q origin main
    echo "共享仓库已推送:$(git -C "$SUB" log --oneline -1)"
    commit_gitlink "external/kklab_scinet_agents:$msg"
}

cmd_status() {
    require_sub
    git -C "$SUB" fetch -q origin
    local branch ahead behind recorded
    branch="$(git -C "$SUB" rev-parse --abbrev-ref HEAD)"
    ahead="$(git -C "$SUB" rev-list --count origin/main..HEAD)"
    behind="$(git -C "$SUB" rev-list --count HEAD..origin/main)"
    recorded="$(git ls-tree HEAD "$SUB" | awk '{print $3}')"
    echo "submodule 分支:$branch$([ "$branch" = HEAD ] && echo '(detached,修改前先运行 begin)')"
    echo "submodule 当前:$(git -C "$SUB" log --oneline -1)"
    echo "相对 origin/main:领先 $ahead,落后 $behind"
    echo "本仓库记录的指针:${recorded:0:7}$([ "$recorded" = "$(git -C "$SUB" rev-parse HEAD)" ] || echo '(与 submodule 当前不一致,需要 commit gitlink)')"
    if [ "$(git rev-parse "HEAD:$PREFIX")" = "$(git -C "$SUB" rev-parse "origin/main:$TARGET")" ]; then
        echo "network_agent:已同步(与本仓库 HEAD 的 $PREFIX 一致)"
    else
        echo "network_agent:未同步(本仓库 HEAD 的 $PREFIX 与共享仓库不同),运行 sync"
    fi
    local dirty
    dirty="$(git -C "$SUB" status --short)"
    [ -z "$dirty" ] || { echo "submodule 未提交的改动:"; echo "$dirty"; }
}

case "${1:-}" in
    setup)  cmd_setup ;;
    sync)   cmd_sync ;;
    begin)  cmd_begin ;;
    finish) shift; cmd_finish "${1:-}" ;;
    status) cmd_status ;;
    *)      sed -n '5,10p' "$0"; exit 1 ;;
esac
