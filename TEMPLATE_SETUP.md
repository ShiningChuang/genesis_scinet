# 用本模板起一个新研究项目

本目录是从一个已跑了 100+ 个实验的探索型项目里抽出来的**通用骨架**:agent 协作规则 + 实验入口 + 三层记忆系统 + 环境复现配方。它与研究主题无关,填完下面 7 步即可开跑。

```bash
cp -r research_template <你的项目名> && cd <你的项目名>
```

## 初始化清单

- [ ] **1. 填抬头(决定 agent 的第一印象)**
  `CLAUDE.md`、`AGENTS.md`、`README.md` 顶部各有一段 `<PROJECT_NAME>` / `<一句话研究方向>` 占位;三处要一致。
  这段是 agent 每次进项目读到的第一句话,写清楚"研究什么、处在什么阶段"比写漂亮更重要。
  > `CLAUDE.md` 与 `AGENTS.md` 是同一套规则的两份镜像(Claude Code 读前者,Codex/GPT 类 agent 读后者),**改一处必须同步另一处**。若只用一种 agent,删掉另一份也可以。

- [ ] **2. `git init`**
  入口脚本要求项目是 git 仓库(run 目录名带 git hash、跑完自动 commit),不是就直接拒跑。
  ```bash
  git init -b main && git add -A && git commit -m "init from research_template"
  git remote add origin <repo-url> && git push -u origin main   # 有远端就配上,没有也能先本地跑
  ```
  > 分支名默认 `main`(`scripts/run_experiment.py` 的 `MAIN_BRANCH`);用别的名字就改那一行。

- [ ] **3. 建环境**
  ```bash
  bash env/setup.sh          # 建 .venv + 装 pyyaml + 激活版本化 git hooks
  ```
  再按项目实际情况补 `env/pip/requirements.txt`、`env/setup.sh` 的 [3/4][4/4] 两段,并在 `env/README.md` 写死走 venv 还是 conda 路线。

- [ ] **4. 跑一次自检**
  ```bash
  .venv/bin/python scripts/run_experiment.py configs/probe_example.yaml
  ```
  应当看到:`runs/{ts}_probe_example_{hash}/` 生成、`EXPERIMENTS.md` 多一行、自动 commit 成功。
  验证通过后删掉示例:`rm -r configs/probe_example.yaml src/experiments/probe_example`。

- [ ] **5. 配置分层的两类参数**
  打开 `configs/defaults.yaml`:B 类(测量方法:warmup/重复次数/超时…)全局固定,A 类(被测对象默认值)按项目补。
  同时改 `env_snapshot` 段 —— 声明每个 run 要记录哪些命令输出与库版本(默认只记 python/git;用 GPU 就放开 `nvidia-smi` / `nvcc` 那两行)。

- [ ] **6. 按项目产出补 `.gitignore`**
  规则是:**小结果文件进 git(可迁移记忆),大件不进(可重建)**。`runs/**` 与 `resources/**` 已按常见扩展名挡了一批,项目特有的大件格式自己补。
  > `resources/` 是给你手动放外部资料(论文 pdf、外部文档、摘来的 md)的地方:小文本进 git、pdf 等大件留本地并在 `resources/README.md` 登记出处;agent 只读不写。

- [ ] **7. 起第一份实验计划**
  `docs/current_experiment_plan.md` 现在是占位稿。让 agent 陪你把 TBD 清掉、把第一个假设定下来,再开跑第一个实验(`CLAUDE.md` §7:没有清晰假设的实验不要做)。

- [ ] **8. 删掉本文件** —— 初始化完成后 `rm TEMPLATE_SETUP.md`,它对项目本身没有信息量。

## 这套框架在强制什么(为什么值得照做)

| 机制 | 强制了什么 | 实现位置 |
|---|---|---|
| 唯一入口 | 实验不可能"跑了但没记录" | `scripts/run_experiment.py`,`CLAUDE.md` §1 |
| config 必填四件套 | 每个 run 都能回答"做了什么、验证什么假设" | 入口的拒跑校验 |
| entry 必须在 `src/experiments/{tag}/` | 代码与 run 靠 tag 配对,不裸露平铺 | 入口的拒跑校验 |
| 合并后 config 存进 run 目录 | 历史 run 自包含,不被 defaults 后续改动污染 | `save_config` |
| 环境快照每 run 一份 | 事后能 diff"环境是否悄悄变了" | `capture_env_snapshot` |
| 失败也登记 + push | 负结果不被静默丢弃 | 入口的 `finally` 块 |
| detached HEAD 跳过 commit | 复现旧实验不污染 git 历史 | `git_commit_and_push` |
| 计划稿覆写式 + 同步铁律 | 任何时刻能回答"在做什么、下一步是什么" | `CLAUDE.md` §8 |
| knowledge/ideas/current_log 人工独占 | agent 不能污染人的思考缓冲区 | `CLAUDE.md` §3 |
| findings / knowledge 按日期分卷 | 单文件不会无限膨胀,旧卷原地即归档 | `docs/{findings,knowledge}_{YYYYMMDD}.md` |
| 两类分卷各有三级标题索引 | 跨卷定位不依赖逐文件搜索 | `docs/_index_{findings,knowledge}.md` |

## 日常节奏(照抄原项目的用法)

1. 想清楚假设 → 让 agent 用一两句话陈述"验证什么、预期看到什么、为什么值得做" → 你认可。
2. agent 先把这个实验补进 `docs/current_experiment_plan.md` 的「步骤与进度」,再建 config、写 `src/experiments/{tag}/run.py`。
3. `python scripts/run_experiment.py configs/xxx.yaml` → 自动落盘、登记、commit+push。
4. agent 只汇报三点:客观结果 / 对照假设 / 一个建议的下一步,然后**停下**。
5. 你把想留的记录手写进 `docs/current_log.md`(agent 不碰),隔一阵手动 distill 进最新一卷 `docs/findings_{YYYYMMDD}.md`(结论)或 `docs/knowledge_{YYYYMMDD}.md`(通用知识;agent 不碰);两类新卷都由你决定何时创建。
6. 关键结论标 ✅ 之前,至少重复跑一次确认。
7. 换实验时:current plan / current_log 归档进 `docs/archive/{YYYYMMDD}_{tag}.md` 与 `_log.md`,从 `docs/_plan_template.md` 起新稿并 carry-forward「实验历史」。
