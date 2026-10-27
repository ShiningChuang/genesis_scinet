# 管理项目共享仓库 SciNetGenesis

SciNet 项目的共享仓库：<https://github.com/SelfDrivingNetworkLab/SciNetGenesis>（Mariam 管理，多方共用）。
在本仓库里以 submodule 接入，位置是 `external/SciNetGenesis`。network agent 放在其中的 **`ucr/network_agent/`**，
直接推 `main`。固定操作写成了 [scinet.sh](scinet.sh)，和 [kklab.sh](../manage_kklab_scinet_agents/kklab.sh) 共用同一套逻辑（[tools/common/repo_sync.sh](../common/repo_sync.sh)），命令也一样：

```bash
bash tools/manage_scinet_repo/scinet.sh setup                    # 一次性：submodule 跟踪 main
bash tools/manage_scinet_repo/scinet.sh check                    # 只审查，不碰任何仓库
bash tools/manage_scinet_repo/scinet.sh sync --dry-run           # 预览会推什么，然后还原，不提交不推送
bash tools/manage_scinet_repo/scinet.sh sync [--force] "<English message>"   # 同步 src/lib/network_agent → ucr/network_agent/
bash tools/manage_scinet_repo/scinet.sh begin                    # 改 ucr/ 下其他文件前
bash tools/manage_scinet_repo/scinet.sh finish "<English message>"   # 改完后
bash tools/manage_scinet_repo/scinet.sh status                   # 随时查看状态
```

> **这是多人共用的组织仓库，推送前先 `sync --dry-run` 看一眼。** agent（Claude）不会自动推到这个仓库，每次由你自己运行 `sync` / `finish`。

## 1. 和 kklab 的区别

|  | kklab_scinet_agents | SciNetGenesis |
|---|---|---|
| 性质 | 你和 Sourabha 的私有仓库 | 项目共享仓库，多方共用 |
| network agent 位置 | `network_agent/` | `ucr/network_agent/` |
| `finish` 能改的范围 | `network_agent/` 以外都可以 | **只能改 `ucr/` 下的文件**（`network_agent/` 除外），别人的目录（`harness/`、`scinetagentframework/`、`workflows/` …）一律不碰 |
| sync 的提交说明 | 自动生成：`Sync network_agent from genesis_scinet@<hash>`，`sync` 不接受手写说明 | **必须手写**：`sync "<message>"` → `ucr/network_agent: <message>`；不写私人仓库名，也不写本地 hash |
| 与本地 commit 的对应 | 写在提交说明里 | 只记在本仓库：每次 sync 在本仓库生成的指针提交 `external/SciNetGenesis:同步 src/lib/network_agent(<本地 hash>):<message>`，既写着本地 hash，又指向 SciNetGenesis 的新 commit。查对应关系：`git log -p -- external/SciNetGenesis` |

其余规则完全相同，详见 [manage_kklab_scinet_agents.md](../manage_kklab_scinet_agents/manage_kklab_scinet_agents.md) §4 的注意事项：detached HEAD、每次修改要提交两次、本地两份 `network_agent`、测试要用包内相对导入、只同步已提交的内容。

## 2. 推送前的审查

`sync` 会审查 HEAD 中 `src/lib/network_agent` 下的代码文件；`finish` 会审查提交说明（包括还没推送的提交）和新增的代码行。命中任何一条就拒绝推送，并打印出是哪个文件、哪一行。`check` 只做审查，可以随时跑。

| 审查项 | 规则 |
|---|---|
| **[中文]** | 不能有中文字符或中文标点（`，。（）：` 等全角字符） |
| **[私人信息]** | 不能有个人信息和私人仓库信息，规则见 [tools/common/private_patterns.txt](../common/private_patterns.txt)：私人仓库的路径（`resources/`、`runs/`、`docs/`、`CLAUDE.md`、`PLAN.md`、`src.lib.` …）、私人仓库名（`genesis_scinet`、`kklab_scinet_agents`）、本机路径、账号、邮箱、人名（Linxuan、KK、Sourabha、Mariam）、会议（`meeting`、`10/15 design` 这类写法）、内部实验编号（`Exp2`、`runs` 目录名） |

- **审查范围是代码文件**（`.md` 以外的所有文件）里的注释、docstring 和字符串，以及提交说明。`.md` 文档正文不审查。
- 规则文件可以随时补充：有新的人名、账号要拦，就往里加一行正则；误报了就把对应规则改窄。kklab 和 SciNetGenesis 共用这一份。
- 审查只拦得住通过脚本推送的内容。直接在 submodule 里 `git push` 会绕过它，所以不要这样做。
- **审查不管 git 作者信息。** 每个提交都带有你本机 `git config user.name / user.email` 设置的名字和邮箱，SciNetGenesis 上的所有人都能看到。如果不想公开当前的邮箱，可以在 submodule 里单独设置：`git -C external/SciNetGenesis config user.email <GitHub noreply 邮箱>`。

## 3. 日常操作

### 同步 network agent

```bash
git commit ...                                                         # 先在 src/lib/network_agent 里提交
bash tools/manage_scinet_repo/scinet.sh sync --dry-run                 # 预览：会改哪些文件
bash tools/manage_scinet_repo/scinet.sh sync "add reserve/commit branch"   # 确认后真正同步
git push                                                               # 推本仓库（不急，见下）
```

**提交说明怎么写：** 英文，动词开头，写这次改了什么，脚本会自动加上 `ucr/network_agent: ` 前缀（自己写了前缀也不会重复）。例如：
- 第一次：`sync "add SciNet network agent (protocol graph quote branch, capacity ledger, SENSE and telemetry interfaces)"`
- 以后：`sync "add reserve/commit branch"`、`sync "fix slot rounding in ledger.apply"`

说明同样要过审查：不能有中文、人名、私人仓库名等。不写说明直接 `sync` 会被拒绝（`--dry-run` 可以不写）。

**最后的 `git push` 推的是本仓库，不是 SciNetGenesis。** `sync` 结束时 SciNetGenesis 已经推送完毕；本仓库只是在本地多了一个记录新指针的提交。不推也不影响 SciNetGenesis，只是 GitHub 上的 genesis_scinet 还记着旧指针，下次有别的改动时一起推即可。

### 修改 `ucr/` 下的其他文件（比如 `ucr/README.md`）

```bash
bash tools/manage_scinet_repo/scinet.sh begin
# 编辑 external/SciNetGenesis/ucr/README.md
bash tools/manage_scinet_repo/scinet.sh finish "ucr: add README"
git push
```

### 别人的更新

`begin`、`sync`、`finish` 都会先把 submodule 拉到 SciNetGenesis 最新的 `main`。只想看看别人更新了什么，运行 `status` 就够了：它会 fetch，然后报告落后多少个提交。

## 4. 出问题时

- **有人直接改了 `ucr/network_agent/`：** `sync` 会停下并提示"与本仓库任何一次提交都不一致"。先看对方改了什么（`git -C external/SciNetGenesis log -p origin/main -- ucr/network_agent`），把有用的改动搬进 `src/lib/network_agent` 并提交，再用 `sync --force`。
- **找回 detached HEAD 上的提交、撤掉 submodule：** 做法和 kklab 一样，见 kklab 说明文档 §5，把路径换成 `external/SciNetGenesis` 即可。

## 5. 相关文件

| 文件 | 作用 |
|---|---|
| [scinet.sh](scinet.sh) | SciNetGenesis 的参数（仓库地址、目标目录、提交说明、可改范围） |
| [tools/common/repo_sync.sh](../common/repo_sync.sh) | 两个仓库共用的同步、审查、提交逻辑 |
| [tools/common/private_patterns.txt](../common/private_patterns.txt) | 私人信息审查规则 |
| [env/external_deps.md](../../env/external_deps.md) | SciNetGenesis submodule 登记 |
