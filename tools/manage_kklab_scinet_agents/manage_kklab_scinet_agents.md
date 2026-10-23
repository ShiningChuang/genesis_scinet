# 管理共享仓库 kklab_scinet_agents

与 telemetry agent 同事共享代码和图表的仓库：<https://github.com/ShiningChuang/kklab_scinet_agents>（私有，同事为 collaborator）。
在本仓库里以 submodule 接入，位置是 `external/kklab_scinet_agents`。固定操作都写成了 [kklab.sh](kklab.sh)，日常只用下面五条命令。

```bash
bash tools/manage_kklab_scinet_agents/kklab.sh setup                 # 一次性：加入 submodule
bash tools/manage_kklab_scinet_agents/kklab.sh sync                  # network agent 有新提交后：同步到共享仓库
bash tools/manage_kklab_scinet_agents/kklab.sh begin                 # 改共享文件前
bash tools/manage_kklab_scinet_agents/kklab.sh finish "<提交说明>"     # 改共享文件后
bash tools/manage_kklab_scinet_agents/kklab.sh status                # 随时查看状态
```

## 1. 三处代码的关系

```
genesis_scinet（本仓库，私有，不分享）
├── src/lib/network_agent/          ← network agent 唯一的源头，日常开发都在这里
│         │
│         │  kklab.sh sync（git subtree，单向，保留提交历史）
│         ▼
└── external/kklab_scinet_agents/   ← submodule = 共享仓库
    ├── network_agent/              ← 同步过来的副本，只由 sync 写入
    ├── telemetry_agent/            ← 同事负责
    ├── resources/                  ← 两人共享的图表、笔记
    └── README.md                   ← 归属规则、接口说明
```

## 2. 哪些文件能在 submodule 里改

| 位置 | 能否在 submodule 里改 | 说明 |
|---|---|---|
| `resources/`、顶层 `README.md`、`requirements.txt` | ✅ 用 `begin` / `finish` | 两人共用 |
| `telemetry_agent/` | 按与同事的约定 | 归同事；小修改先打招呼 |
| **`network_agent/`** | ❌ | 源头在 `src/lib/network_agent`。在这里改，改动回不到源头，下次 `sync` 还会冲突。要改就在 `src/lib/network_agent` 改、commit、再 `sync`。`finish` 会检查这一条，发现改动就拒绝提交 |

## 3. 日常操作

### 同步 network agent

```bash
git commit ...                    # 先在 src/lib/network_agent 里提交
bash tools/manage_kklab_scinet_agents/kklab.sh sync
git push                          # 推本仓库（sync 只在本地提交了 gitlink）
```

`sync` 依次做四件事：
1. 用 `git subtree split` 把 `src/lib/network_agent` 的历史拆到分支 `network-agent-export`，推到共享仓库；
2. 把 submodule 切到 `main` 并拉到最新；
3. 在 submodule 里 `git subtree pull` 并入 `network_agent/`，推送共享仓库的 `main`；
4. 在本仓库**只**提交 submodule 指针（gitlink），不带上其他改动。

### 修改共享文件（resources/、README 等）

```bash
bash tools/manage_kklab_scinet_agents/kklab.sh begin
# 编辑 external/kklab_scinet_agents/resources/... 等文件
bash tools/manage_kklab_scinet_agents/kklab.sh finish "resources: 加入拓扑示意图"
git push                          # 推本仓库
```

`finish` 依次：检查 submodule 在 `main` 上、`network_agent/` 没被改 → 提交 → `pull --rebase`（同事可能刚推过）→ 推送共享仓库 → 在本仓库提交 gitlink。

### 新机器 / 新 clone

```bash
git submodule update --init external/kklab_scinet_agents
bash tools/manage_kklab_scinet_agents/kklab.sh begin         # 切到 main（submodule 初始化后处于 detached HEAD）
```

## 4. 注意事项

1. **submodule 默认处于 detached HEAD。** `git submodule update` 之后，submodule 停在某个 commit 上，不在任何分支。这时直接 commit，提交不属于任何分支，很容易丢。所以改之前一律先运行 `begin`（`sync` 内部也会自动切到 `main`）。

2. **每次修改都要提交两次。** 一次在 submodule 里（提交并推送共享仓库），一次在本仓库（提交新的 gitlink）。脚本两步都会做，但**本仓库的 push 需要你自己执行**。`scripts/run_experiment.py` 的自动提交只会 `git add EXPERIMENTS.md configs runs`，**不会**带上 gitlink。

3. **本地有两份 `network_agent`。** 一份在 `src/lib/network_agent`（源头），一份在 `external/kklab_scinet_agents/network_agent`（副本）。
   - 不要把 `external/kklab_scinet_agents` 加进 `PYTHONPATH` / `sys.path`，否则可能 import 到副本。
   - 在本仓库根目录直接运行 `pytest`，可能把副本的测试也收集进来，两份模块名相同，会报 `import file mismatch`。根目录的 `pytest.ini` 已经限定 `testpaths = src`、`norecursedirs = external ...`；显式写路径（`pytest src/lib/network_agent/tests`）也没问题，**不要写成 `pytest external/...` 或 `pytest .`**。

4. **`sync` 只同步已 commit 的内容。** `src/lib/network_agent` 下有未提交的改动时，脚本会直接停下。

5. **不要删除 `network-agent-export` 分支。** 本仓库的本地分支和共享仓库的远端分支都要保留：subtree 靠它们做增量同步，删掉后下次同步会重新拆分整段历史，并可能冲突。

6. **测试必须保持包内相对导入。** `src/lib/network_agent/tests/` 里用的是 `from ..schemas import ...`、`from .helpers import ...`，所以同一份代码在两个仓库里都能运行（这边是 `src.lib.network_agent`，那边是顶层 `network_agent`）。新写的测试不要再用 `from src.lib.network_agent...`，否则同步过去后会 import 失败。

7. **共享仓库里的稳定接口。** 共享仓库 README 写明 telemetry agent 可以依赖四个接口：`schemas.LinkSample`、`telemetry.TelemetrySource`、`topology.Topology` / `TopologySpec`、`sim.MockNetwork`。**改这几个之前先通知同事**；其余模块（ledger、placement、graphs …）属于内部实现，可以随时改。

8. **同步的是整个 `src/lib/network_agent` 目录**，包括 `PLAN.md`（进度表、待决项，其中提到 slides、会议记录路径和人名）。不想分享的内容不要放进这个目录。

9. **大文件不进共享仓库。** 共享仓库的 `.gitignore` 已经忽略 `*.pptx`、`*.pdf`；其他大文件（数据集等）也不要提交，在共享仓库的 `resources/README.md` 里登记来源。

10. **登记外部依赖。** 按 CLAUDE.md §3 的规定，这个 submodule 已登记在 `env/external_deps.md`。它是协作仓库，指针变化频繁，所以那里不写固定 hash，以 gitlink 为准。

## 5. 出问题时

### 找回 detached HEAD 上的提交

在 detached HEAD 上 commit 了，之后又切走：

```bash
git -C external/kklab_scinet_agents reflog -10          # 找到那次提交的 hash
git -C external/kklab_scinet_agents checkout main
git -C external/kklab_scinet_agents cherry-pick <hash>
bash tools/manage_kklab_scinet_agents/kklab.sh finish "<提交说明>"
```

### 有人直接改了共享仓库里的 `network_agent/`

`sync` 的 subtree pull 会出现合并冲突。处理原则是**以 `src/lib/network_agent` 为准**：

1. 先看对方改了什么：`git -C external/kklab_scinet_agents log origin/main -- network_agent`；
2. 有价值的改动，手工搬进 `src/lib/network_agent` 并 commit；
3. 在 submodule 里解决冲突时，一律取同步过来的版本，提交合并后推送，再运行一次 `sync`；
4. 提醒对方：`network_agent/` 只由 sync 写入。

### 想换回独立 clone，或者不用 submodule 了

```bash
git submodule deinit -f external/kklab_scinet_agents
git rm -f external/kklab_scinet_agents
rm -rf .git/modules/external/kklab_scinet_agents
```

同时删掉 `env/external_deps.md` 里对应的一节。

## 6. 相关文件

| 文件 | 作用 |
|---|---|
| [tools/manage_kklab_scinet_agents/kklab.sh](kklab.sh) | 全部固定操作 |
| [pytest.ini](../../pytest.ini) | 防止收集到副本的测试 |
| [env/external_deps.md](../../env/external_deps.md) | submodule 登记 |
| `external/kklab_scinet_agents/README.md` | 共享仓库的归属规则与接口说明（给同事看） |
