#!/usr/bin/env bash
# 管理项目共享仓库 SciNetGenesis(本仓库中的 submodule:external/SciNetGenesis),network agent 放在其中的 ucr/network_agent/。
# 规则与注意事项见 tools/manage_scinet_repo/manage_scinet_repo.md;公共逻辑在 tools/common/repo_sync.sh。
#
# 用法:
#   bash tools/manage_scinet_repo/scinet.sh setup                    一次性:submodule 跟踪 main、提交 gitlink
#   bash tools/manage_scinet_repo/scinet.sh check                    只审查(中文 / 个人信息 / 私人仓库信息),不碰任何仓库
#   bash tools/manage_scinet_repo/scinet.sh sync --dry-run           预览会推什么,然后还原,不提交不推送
#   bash tools/manage_scinet_repo/scinet.sh sync [--force] "<message>"  把 src/lib/network_agent 已提交的内容单向复制到 ucr/network_agent/;
#                                                                    提交说明 = "ucr/network_agent: <message>"(英文,写改了什么)
#   bash tools/manage_scinet_repo/scinet.sh begin                    修改 ucr/ 下其他文件前:submodule 切到 main 并拉到最新
#   bash tools/manage_scinet_repo/scinet.sh finish "<message>"       修改后:审查、提交并推送 submodule,再提交本仓库的 gitlink
#   bash tools/manage_scinet_repo/scinet.sh status                   查看 submodule 分支、未推送提交、ucr/network_agent 是否已同步
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

SCRIPT=tools/manage_scinet_repo/scinet.sh
NAME=SciNetGenesis
REMOTE="${SCINET_REMOTE:-git@github.com:SelfDrivingNetworkLab/SciNetGenesis.git}"
SUB=external/SciNetGenesis
PREFIX=src/lib/network_agent
TARGET=ucr/network_agent
SYNC_MSG=""
SYNC_MSG_PREFIX="ucr/network_agent: "            # 项目仓库:提交说明写改了什么,不写私人仓库名和本地 hash
EDIT_SCOPE="ucr/"                                # 只改我们自己的 ucr/;别人的目录一律不碰
EDIT_HINT="只可以修改 $SUB/ucr/ 下的文件(例如 ucr/README.md);"

source "$REPO_ROOT/tools/common/repo_sync.sh"
dispatch "$@"
