#!/usr/bin/env bash
# 管理共享仓库 kklab_scinet_agents(本仓库中的 submodule:external/kklab_scinet_agents)。
# 规则与注意事项见 tools/manage_kklab_scinet_agents/manage_kklab_scinet_agents.md;公共逻辑在 tools/common/repo_sync.sh。
#
# 用法:
#   bash tools/manage_kklab_scinet_agents/kklab.sh setup                    一次性:加入 submodule、跟踪 main、提交 gitlink
#   bash tools/manage_kklab_scinet_agents/kklab.sh check                    只审查(中文 / 个人信息 / 私人仓库信息),不碰任何仓库
#   bash tools/manage_kklab_scinet_agents/kklab.sh sync [--force|--dry-run] 把 src/lib/network_agent 已提交的内容单向复制到 network_agent/
#   bash tools/manage_kklab_scinet_agents/kklab.sh begin                    修改共享文件前:submodule 切到 main 并拉到最新
#   bash tools/manage_kklab_scinet_agents/kklab.sh finish "<message>"       修改共享文件后:审查、提交并推送 submodule,再提交本仓库的 gitlink
#   bash tools/manage_kklab_scinet_agents/kklab.sh status                   查看 submodule 分支、未推送提交、network_agent 是否已同步
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SCRIPT=tools/manage_kklab_scinet_agents/kklab.sh
NAME=kklab_scinet_agents
REMOTE="${KKLAB_REMOTE:-git@github.com:ShiningChuang/kklab_scinet_agents.git}"
SUB=external/kklab_scinet_agents
PREFIX=src/lib/network_agent
TARGET=network_agent
SYNC_MSG="Sync network_agent from genesis_scinet@%s"   # kklab 是与同事的私有仓库,写明来源便于追溯
EDIT_SCOPE=""                                          # 除 network_agent/ 外都可以改
EDIT_HINT="可以修改 $SUB 下的 resources/、README 等;"

source "$REPO_ROOT/tools/common/repo_sync.sh"
dispatch "$@"
