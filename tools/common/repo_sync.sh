# 把本仓库的一个目录单向同步到某个 submodule 仓库的公共逻辑,由 tools/manage_*/ 下的脚本 source。
# 不要直接运行。调用方在 source 之前设置:
#   REPO_ROOT   本仓库根目录
#   SCRIPT      调用方脚本的相对路径(用于提示信息)
#   NAME        目标仓库的显示名
#   REMOTE      目标仓库地址
#   SUB         submodule 位置(相对 REPO_ROOT)
#   PREFIX      本仓库中的源目录
#   TARGET      目标仓库中的目录(只由 sync 写入)
#   SYNC_MSG    sync 在目标仓库的提交说明(printf 模板,%s 处填本仓库源 commit 的短 hash)
#   EDIT_SCOPE  finish 允许修改的路径前缀(空 = 除 TARGET 外都可以)
#   EDIT_HINT   begin 时提示可以改哪些文件
#
# 推到目标仓库的内容要过两项审查(sync 查 HEAD 中 $PREFIX 下的代码文件,finish 查提交说明和新增的代码行):
#   [中文]     提交说明、代码注释/字符串里不能有中文字符或中文标点
#   [私人信息] 不能出现个人信息与私人仓库信息,规则见 tools/common/private_patterns.txt
# md 文档的正文不算注释,不审查。

PATTERNS="$REPO_ROOT/tools/common/private_patterns.txt"

die() { echo "!! $*" >&2; exit 1; }

scan_text() {  # 从 stdin 读文本,打印命中审查的行(前缀为 $1);有命中返回 0
    perl -CSD -e 'use utf8;
        my ($pf, $label) = @ARGV;
        open my $fh, "<:encoding(UTF-8)", $pf or die "cannot read $pf\n";
        my @p;
        while (<$fh>) { chomp; next if /^\s*(#|$)/; push @p, [$_, qr/$_/i] }
        my $hit = 0;
        while (my $l = <STDIN>) {
            chomp $l;
            if ($l =~ /[\x{3000}-\x{303F}\x{3400}-\x{9FFF}\x{FF00}-\x{FFEF}]/) {
                print "  [中文] $label:$.: $l\n"; $hit = 1; next;
            }
            for my $r (@p) {
                if ($l =~ $r->[1]) { print "  [私人信息 /$r->[0]/] $label:$.: $l\n"; $hit = 1; last }
            }
        }
        exit($hit ? 0 : 1)' "$PATTERNS" "$1"
}

review_head() {  # 审查 HEAD 中 $PREFIX 下的代码文件(md 除外);打印命中,有命中返回 0
    local f hit=1
    while read -r f; do
        git show "HEAD:$f" | scan_text "$f" && hit=0
    done < <(git ls-tree -r --name-only HEAD -- "$PREFIX" | grep -v '\.md$')
    return $hit
}

target_from_source() {  # 目标仓库当前的 $TARGET 是否等于本仓库某次提交的 $PREFIX(否则说明有人在那边直接改过)
    local tree c
    tree="$(git -C "$SUB" rev-parse "HEAD:$TARGET" 2>/dev/null)" || return 0   # 还没有 $TARGET
    for c in $(git log --format=%H -- "$PREFIX"); do
        [ "$(git rev-parse "$c:$PREFIX" 2>/dev/null)" = "$tree" ] && return 0
    done
    return 1
}

require_sub() {
    [ -e "$SUB/.git" ] || die "submodule 未初始化:首次运行 bash $SCRIPT setup;新 clone 后运行 git submodule update --init $SUB"
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

copy_committed() {  # 用本仓库 HEAD 中 $PREFIX 的内容覆盖 $SUB/$TARGET(不带未跟踪文件和 __pycache__)
    local tmp
    tmp="$(mktemp -d)"
    git archive HEAD "$PREFIX" | tar -x -C "$tmp"
    mkdir -p "$SUB/$TARGET"
    rsync -a --delete "$tmp/$PREFIX/" "$SUB/$TARGET/"
    rm -rf "$tmp"
}

cmd_setup() {
    if [ -e "$SUB/.git" ]; then
        echo "submodule 已存在:$SUB"
    else
        git submodule add -q -f -b main "$REMOTE" "$SUB"   # external/* 被 .gitignore 忽略,需 -f
    fi
    git config -f .gitmodules "submodule.$SUB.branch" main
    sub_on_main
    git add .gitmodules "$SUB"
    if git diff --cached --quiet -- .gitmodules "$SUB"; then
        echo "gitlink 与 .gitmodules 无变化"
    else
        git commit -q -m "$SUB:以 submodule 接入并跟踪 main" -- .gitmodules "$SUB"
        echo "本仓库已提交:$(git log --oneline -1)(未 push)"
    fi
}

cmd_check() {  # 只做审查,不碰任何仓库
    echo "审查 HEAD 中 $PREFIX 下的代码文件(规则:tools/common/private_patterns.txt + 中文)"
    if review_head; then
        die "以上内容不能推到 $NAME;改掉并 commit 后再 sync"
    fi
    echo "通过"
}

cmd_sync() {
    require_sub
    local opt="${1:-}"
    [ -z "$opt" ] || [ "$opt" = --force ] || [ "$opt" = --dry-run ] || die "未知参数 $opt(可用 --force / --dry-run)"
    [ -z "$(git status --porcelain -- "$PREFIX")" ] || die "$PREFIX 有未提交的改动,未提交部分不会被同步。先 commit。"
    [ -z "$(git -C "$SUB" status --porcelain)" ] || die "$SUB 有未提交的改动(可能 begin 之后还没 finish),先处理。"
    if review_head; then
        die "以上内容不能推到 $NAME;改掉并 commit 后再 sync"
    fi

    echo "==> [1/4] submodule 切到 main 并拉到最新"
    sub_on_main
    [ "$opt" = --force ] || target_from_source || die "$NAME 的 $TARGET/ 与本仓库任何一次提交都不一致,有人在那边直接改过。同步会覆盖这些改动,先按说明文档处理(处理完用 sync --force)。"

    echo "==> [2/4] 用 $PREFIX 已提交的内容覆盖 $SUB/$TARGET/"
    local src_rev
    src_rev="$(git rev-parse --short HEAD)"
    copy_committed

    if [ "$opt" = --dry-run ]; then
        echo "==> [dry-run] 将要提交到 $NAME 的改动:"
        git -C "$SUB" add -A "$TARGET"
        git -C "$SUB" diff --cached --stat | tail -20
        echo "提交说明:$(printf "$SYNC_MSG" "$src_rev")"
        git -C "$SUB" reset -q -- "$TARGET"
        git -C "$SUB" checkout -q -- . 2>/dev/null || true
        git -C "$SUB" clean -fdq -- "$TARGET"
        echo "==> [dry-run] 已还原 submodule,没有提交也没有推送"
        return
    fi

    echo "==> [3/4] 提交并推送 $NAME"
    if [ -z "$(git -C "$SUB" status --porcelain -- "$TARGET")" ]; then
        echo "$TARGET/ 无变化"
    else
        git -C "$SUB" add -A "$TARGET"
        git -C "$SUB" commit -q -m "$(printf "$SYNC_MSG" "$src_rev")"
        git -C "$SUB" pull -q --rebase origin main
        git -C "$SUB" push -q origin main
        echo "$NAME 已推送:$(git -C "$SUB" log --oneline -1)"
    fi

    echo "==> [4/4] 更新本仓库记录的 submodule 指针"
    commit_gitlink "$SUB:同步 $PREFIX($src_rev)"
}

cmd_begin() {
    require_sub
    [ -z "$(git -C "$SUB" status --porcelain)" ] || die "$SUB 已有未提交的改动;改完了就运行 finish"
    sub_on_main
    echo "submodule 已在 main:$(git -C "$SUB" log --oneline -1)"
    echo "$EDIT_HINT 不要改 $TARGET/。改完运行:bash $SCRIPT finish \"<English message>\""
}

cmd_finish() {
    require_sub
    local msg="${1:-}"
    [ -n "$msg" ] || die "用法:bash $SCRIPT finish \"<English message>\""
    [ "$(git -C "$SUB" rev-parse --abbrev-ref HEAD)" = main ] || \
        die "submodule 不在 main(detached HEAD),先运行 begin。若已在 detached HEAD 上提交过,见说明文档「找回 detached HEAD 上的提交」"
    git -C "$SUB" fetch -q origin
    if [ -n "$(git -C "$SUB" status --porcelain -- "$TARGET")" ] || \
       ! git -C "$SUB" diff --quiet origin/main HEAD -- "$TARGET"; then
        die "$TARGET/ 不能在 $NAME 里改(只由 sync 写入)。撤销:git -C $SUB checkout origin/main -- $TARGET;要改请在 $PREFIX 里改再 sync"
    fi
    if [ -z "$(git -C "$SUB" status --porcelain)" ] && [ -z "$(git -C "$SUB" log --oneline origin/main..HEAD)" ]; then
        die "submodule 里没有要提交的改动"
    fi
    if { printf '%s\n' "$msg"; git -C "$SUB" log --format=%B origin/main..HEAD; } | scan_text "commit message"; then
        die "提交说明(含尚未推送的提交)不能有中文、个人信息或私人仓库信息"
    fi
    git -C "$SUB" add -A
    if [ -n "$EDIT_SCOPE" ]; then
        local outside
        outside="$( { git -C "$SUB" diff --cached --name-only; git -C "$SUB" diff --name-only origin/main HEAD; } | grep -v "^$EDIT_SCOPE" || true)"
        if [ -n "$outside" ]; then
            git -C "$SUB" reset -q
            die "只能改 $EDIT_SCOPE 下的文件,以下文件不在范围内(已取消暂存,文件内容未动):
$outside"
        fi
    fi
    if git -C "$SUB" diff --cached -U0 -- . ':(exclude)*.md' | grep '^+' | grep -v '^+++' | scan_text "new line"; then
        git -C "$SUB" reset -q
        die "以上新增的代码行不能推到 $NAME(已取消暂存,文件内容未动);改掉后重新运行 finish(md 文档不审查)"
    fi
    git -C "$SUB" diff --cached --quiet || git -C "$SUB" commit -q -m "$msg"
    git -C "$SUB" pull -q --rebase origin main    # 别人可能刚推过
    git -C "$SUB" push -q origin main
    echo "$NAME 已推送:$(git -C "$SUB" log --oneline -1)"
    commit_gitlink "$SUB:$msg"
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
    if [ "$(git rev-parse "HEAD:$PREFIX")" = "$(git -C "$SUB" rev-parse "origin/main:$TARGET" 2>/dev/null)" ]; then
        echo "$TARGET:已同步(与本仓库 HEAD 的 $PREFIX 一致)"
    else
        echo "$TARGET:未同步(本仓库 HEAD 的 $PREFIX 与 $NAME 不同),运行 sync"
    fi
    local dirty
    dirty="$(git -C "$SUB" status --short)"
    [ -z "$dirty" ] || { echo "submodule 未提交的改动:"; echo "$dirty"; }
}

dispatch() {
    case "${1:-}" in
        setup)  cmd_setup ;;
        check)  cmd_check ;;
        sync)   shift; cmd_sync "${1:-}" ;;
        begin)  cmd_begin ;;
        finish) shift; cmd_finish "${1:-}" ;;
        status) cmd_status ;;
        *)      sed -n '/^# 用法:/,/^set -euo/p' "$SCRIPT" | sed '$d'; exit 1 ;;
    esac
}
