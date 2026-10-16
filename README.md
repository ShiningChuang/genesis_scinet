# genesis_scinet

**SciNet 方向的系统研究**:为 AI 驱动的自主科学实验闭环,做支撑它的网络与数据传输基础设施——GPU-to-GPU 传输、science-aware 自适应路由、可靠性与韧性、跨机构 workflow 协调,先在合作方已有的网络 digital twin 上做原型与验证。不做具体领域的科学 AI 模型(蛋白质/材料等),那是上层的事。

隶属美国能源部 Genesis Mission 计划下的 SciNet 项目,当前是六个月 Phase 1 加速阶段,产出 proof of concept 与 demo,支撑 12 月的 Phase 2 proposal。**处于方向收敛期**:digital twin 的具体形态、本组负责的模块、第一个可测的系统问题均未确定(见 `docs/current_experiment_plan.md` 的待办与决策)。背景见 `resources/conversation_20260727.md`。

核心设计理念是把记录系统做成**可复现、可迁移、记忆持久化**的:实验结果都被结构化记录,换机器靠 `git clone` 恢复,项目结构靠 tag 前缀保持稳定而非随主题增删文件夹。

> 本文件是给人看的"地图 + 说明书",是总览与索引。具体规则只在这里简述并指向源文件(尤其 `CLAUDE.md`),不照抄,以免两处不同步。
> 本项目骨架来自通用实验框架模板;初始化步骤见 `TEMPLATE_SETUP.md`(填完即可删)。

## 目录结构

```
<project>/
├── CLAUDE.md                  # 项目铁律 + 记忆地图 + 接手阅读顺序(给 agent / 接手者的第一入口)  [git]
├── AGENTS.md                  # CLAUDE.md 的 Codex/GPT-agent 镜像(两份须同步)                    [git]
├── README.md                  # 本文件:全景说明与索引                                          [git]
├── EXPERIMENTS.md             # 实验索引表(一行一个实验,入口脚本自动追加)                      [git]
├── .gitignore                 # 区分"可迁移记忆"与"可重建大件"                                   [git]
├── docs/
│   ├── findings_{YYYYMMDD}.md # 结论性发现;按日期分卷,新卷由我创建、agent 可写已有卷       [git]
│   ├── knowledge_{YYYYMMDD}.md # 通用知识点(工具/系统/领域),不过期;按日期分卷,纯人工维护、agent 不写 [git]
│   ├── _index_findings.md     # findings 各卷的一至三级标题目录                              [git]
│   ├── _index_knowledge.md    # knowledge 各卷的一至三级标题目录                             [git]
│   ├── ideas.md               # 项目思考与点子(假设/待办/推测,允许过期);纯人工维护、agent 不写  [git]
│   ├── _plan_template.md      # 计划稿模板(新实验 cp 它起稿;用法/约定见其抬头)             [git]
│   ├── current_experiment_plan.md  # 当前实验计划稿(覆写式)+ 末尾「实验历史」               [git]
│   ├── current_log.md         # 当前实验运行流水账(append-only;我手写维护,agent 只创建/归档不写内容) [git]
│   └── archive/               # 历史 plan/log + ideas.md;findings/knowledge 靠分卷不设归档   [git]
├── configs/
│   ├── defaults.yaml          # 分层配置默认值(测量方法 B 类 + 实验条件 A 类默认 + 环境快照声明) [git]
│   └── <experiment>.yaml      # 具体实验 config,覆盖 defaults                                   [git]
├── scripts/
│   ├── run_experiment.py      # 唯一实验入口:合并配置 → 跑 → 落盘 → 登记 → commit+push          [git]
│   ├── fix_webview_links.py   # 把 IDE 粘贴出的 vscode-webview 链接还原成仓库相对路径             [git]
│   ├── extract_md_images.py   # md 内嵌 base64 图片 → resources/imgs/ 文件 + 相对路径引用         [git]
│   └── git-hooks/pre-commit   # 版本化 hook(env/setup.sh 里 core.hooksPath 激活)                [git]
├── src/
│   ├── experiments/{tag}/     # 每个实验一个文件夹(按 tag 分类,不裸露平铺),内部允许杂乱       [git]
│   │   └── run.py             #   该实验的 entry(config 的 entry 指向它);与 runs/ 靠 tag+hash 配对
│   └── lib/                   # 稳定复用代码,保持整洁                                            [git]
├── env/                       # 环境重建配方(venv/conda 两路线,每项目选一条)                   [git]
│   ├── README.md              #   路线声明 + 一键重建说明                                         [git]
│   ├── setup.sh               #   可跑的一键重建脚本                                              [git]
│   ├── external_deps.md       #   git 之外的依赖:仓库/来源 + 钉死 commit + 安装命令 + 本地改动     [git]
│   ├── pip/                   #   venv 路线:requirements.txt(直接依赖) + pip-freeze.lock(全量快照)
│   └── conda/                 #   conda 路线:environment.yml
├── resources/                 # 外部资料(论文/文档/笔记),人工维护、agent 只读不写
│   ├── README.md              #   纪律 + 大件出处清单                                            [git]
│   ├── *.md / *.txt / *.bib   #   小文本                                                         [git]
│   ├── imgs/                  #   md 引用的图片,{YYYYMMDD}_{tag}.{ext}(pre-commit 自动抽取)        [git]
│   └── *.pdf / office / 压缩包 #   大件                                              [本地,不进 git]
├── weekly_report/             # 组会周报(人机协作:AI 起草、我定稿)
│   ├── _report_template.md    #   周报模板(用法/协作方式见其抬头)                              [git]
│   └── {YYYYMMDD}.md          #   一次组会一份,文件名 = 组会日期                                [git]
├── external/                  # 第三方源码                                          [本地,不进 git]
├── data/                      # 大数据集                                            [本地,不进 git]
└── runs/                      # 所有 run 的产出(每个 run 一个目录,平铺)
    └── {ts}_{tag}_{hash}/       #   tag 以 exp_ / probe_ 起头:正式实验 / 中间表征(详见 CLAUDE.md Tag 约定)
        ├── description.txt    #   做了什么(config.description)+ 结果/结论(实验返回)——入口结构强制写入  [git]
        ├── config.yaml        #   合并后的完整配置(自包含)                                      [git]
        ├── metrics.json       #   指标                                                           [git]
        ├── env_snapshot.txt   #   环境快照(命令输出/库版本/seed/git hash)                       [git]
        └── *.log / *.csv / …  #   原始大件                                          [本地,不进 git]
```

**进 git 的(= 可迁移记忆):** 代码、所有配置、环境配方、每个 run 的环境快照与小结果文件、实验索引、发现日志、`resources/` 下的小文本资料。
**不进 git 的(= 可重建大件):** 第三方源码(`external/`)、数据集(`data/`)、原始大件(`runs/` 下的大文件)、`resources/` 下的 pdf 等大件。这些不靠迁移,靠 `env/` 里的配方(或 `resources/README.md` 里登记的出处)在新机器上重建——大件迁移成本高且可由配方精确还原。

## 核心设计理念

贯穿全项目的几条原则(完整铁律见 `CLAUDE.md`):

- **(a) 记忆属于 git 仓库,不属于任何一台 server。** 换机器 = `git clone`,而不是拷贝某台机器的状态。
- **(b) 可靠性靠结构强制,不靠执行者记忆。** 实验必须走统一入口,落盘、登记、push 都自动完成,不依赖人记得做。
- **(c) 主题靠 tag 前缀软聚合,不靠文件夹。** `runs/` 始终平铺,目录结构不随研究主题变化;相关实验用同一 tag 前缀聚合(详见 `CLAUDE.md` 的 Tag 命名约定)。
- **(d) 影响结果的变量进 config,测量方法变量全局统一。** A 类(数据、样本量、seed)逐实验可变、写进 config;B 类(warmup、重复次数)在 `configs/defaults.yaml` 全局固定,避免实验间不可比。
- **(e) 探索阶段保持精简,痛了再加。** 不预先搭重型框架;当某个痛点真正出现时再引入结构。

## 如何跑一个实验(快速上手)

所有实验必须通过唯一入口启动(禁止绕过,详见 `CLAUDE.md` 实验执行铁律):

```
python scripts/run_experiment.py <configs/your_experiment.yaml>
```

新参数先在 `configs/` 建一个 yaml 再启动。config 必填四件套:`tag` / `description` / `hypothesis` / `entry`;实验代码放 `src/experiments/{tag}/`,实现:

```python
def entry(config, run_dir) -> dict:
    ...
    return {"metrics": {...}, "conclusion": "一句话结果", "verdict": "✅|❌|🔍"}
```

入口会自动:

1. **分层加载配置** —— 读 `configs/defaults.yaml`,再用你的实验 config **深度合并覆盖**(嵌套字段递归合并,不是整块替换)。
2. **固定随机源** —— 用合并后配置里的 `seed` 统一设置 python / numpy / torch(并行/GPU 非确定性下不保证逐位相同,只控制可控随机源)。
3. **建立 run 目录并落盘** —— `runs/{timestamp}_{tag}_{git_hash}/`,保存合并后的完整 `config.yaml`(自包含,不依赖 defaults 后续改动)、`metrics.json`、`env_snapshot.txt`、`description.txt`。
4. **登记并同步** —— 往 `EXPERIMENTS.md` 追加一行,自动 `commit` + `push`。即使实验失败也会登记(Verdict 标 ❌)并 push——失败也是数据。

**结构强制**:缺 `description` / `entry` / `tag`、或 entry 不在 `src/experiments/{tag}/` 下、或仓库不是 git repo,入口直接拒跑。

## 如何复现一个历史实验

1. 在 `EXPERIMENTS.md` 找到目标实验那一行,记下它的 run 目录(目录名含 git hash)。
2. `git checkout <hash>` 回到当时的代码状态。
3. 用该 run 目录里保存的 `config.yaml`(已是合并后的完整配置)作为实验输入。
4. `diff` 该 run 的 `env_snapshot.txt` 与当前环境,确认环境一致;不一致则参照 `env/` 下的配方重建环境和第三方依赖。
5. 通过 `python scripts/run_experiment.py <该config>` 重跑。
6. 复现完成后回到最新状态:`git checkout <hash>` 会进入 detached HEAD(游离状态),用 `git switch -`(回到上一个分支)或 `git checkout main && git pull` 回到最新代码。

> 复现重跑时(checkout 到旧 hash)入口脚本会自动检测到 detached HEAD / 非主分支并**跳过 commit/push**,复现结果仅在本地 `runs/` 落盘,不进入项目 git 历史。如需保留复现得到的结论,手动在最新一卷 `docs/findings_{YYYYMMDD}.md` 补记即可。

## 如何在新机器上恢复项目

项目记忆都在 git 仓库里,不在任何一台 server 上:

```
git clone <repo-url>
cd <project>
# 1. 一键重建环境与第三方依赖(详见 env/README.md,它声明本项目走哪条路线):
bash env/setup.sh
# 2. data/ 不在 git 中,按 env/external_deps.md 另行拉取;external/ 由 setup.sh 重建。
claude   # 启动 agent,它会先读 CLAUDE.md 恢复项目上下文
```

## 记忆系统导航

几层记录各司其职,从原始到结论逐层收敛:

- **`runs/`** —— 原始产出。每个 run 一个自包含目录(配置 + 指标 + 环境快照 + 原始数据)。**正式实验与中间表征都进这里**,靠 tag 前缀区分:`exp_`(产出可登记结论的正式实验)/ `probe_`(为定参数/探路的表征测量)。中间结果不留 `/tmp`、不堆进计划稿——distill 后的指标进对应 run 的 `metrics.json`,大件留本地不进 git。
- **`EXPERIMENTS.md`** —— 索引。一行一个实验:日期 / tag / 假设 / 关键结果 / Verdict / 目录,用于快速检索与按 tag 前缀聚合。
- **`docs/findings_{YYYYMMDD}.md`** —— **结论性发现**。每条沉淀一个结论,带 `runs/` 证据链接。按日期分卷,文件名日期是该卷起始日期;新卷何时创建由我决定,agent 只写已有卷。最新卷 = 日期最大的那个,旧卷原地即归档,不进 `docs/archive/`。
- **`docs/knowledge_{YYYYMMDD}.md`** —— **通用知识点**(脱离具体 run 的工具行为/系统特性/领域事实),不随实验过期,**由我手工维护,agent 只读不写、也不新建**。**按日期分卷**避免单文件过大:文件名日期是该卷起始日期,写满了我手动开下一卷,**最新卷 = 日期最大的那个**(`ls docs/knowledge_*.md` 看全部)。旧卷原地保留即归档,因此不进 `docs/archive/`。
- **`docs/_index_findings.md` / `docs/_index_knowledge.md`** —— 两类分卷的目录索引,只收录一级至三级标题;新增卷或标题变化后同步更新。
- **`docs/ideas.md`** —— **项目思考与点子**(假设、待办、推测),**允许过期**,**由我手工维护,agent 只读不写**;过期的我手动剪切进 `docs/archive/ideas.md`。
- **`docs/current_experiment_plan.md`** —— 当前实验的计划稿,**单份滚动**:它存在即表示当前实验进行中。**末尾 `## 实验历史`** 记历次实验简介,换实验时由 AI **carry-forward** 到新 plan(live plan 末尾永远是截至当前的最全历史,归档副本是各时间点快照)。换实验时把计划稿移入 `docs/archive/`,命名 `{YYYYMMDD}_{tag}.md`,再从 `docs/_plan_template.md`(`cp` 覆写)为新实验起稿。
- **`docs/current_log.md`** —— 当前实验**运行流水账**(**append-only**)。**由我(人)手写维护,agent 不写入、不修改其内容**(agent 只在换实验起稿时创建空文件、换实验时归档)。我把每次跑完想留的记录手写进来,慢慢读、据此再**手动**把该留的 distill 进最新一卷 `findings_{YYYYMMDD}.md` / `knowledge_{YYYYMMDD}.md`——它是 raw run 与 distill 之间的缓冲。换实验时连同 plan 一起归档(`{YYYYMMDD}_{tag}_log.md`)后清空。

上面几层都是**本项目产出的记忆**,另有两个方向的补充:

- **`resources/`** —— 外部输入的原材料(论文、外部文档、摘来的笔记),由我人工维护、agent 只读不写(纪律与大件出处清单见 `resources/README.md`)。
- **`weekly_report/`** —— 对外汇报的快照,一次组会一份 `{YYYYMMDD}.md`。**人机协作**:AI 依据 `EXPERIMENTS.md` / `runs/` / 最新 findings 卷起草客观结果(每条带证据链接),我补判断与下周打算后定稿。它是记忆的**出口**而非记忆本身——结论仍以最新 `docs/findings_{YYYYMMDD}.md` 为准,周报只引用不复制。模板见 `weekly_report/_report_template.md`。

**谁能写哪一层**(完整版见 `CLAUDE.md` §3 的人工独占清单):`docs/knowledge_*.md`、`docs/ideas.md`(含 `archive/ideas.md`)、`docs/current_log.md`、`resources/` 是**我的思考缓冲区,agent 只读不写**——它可以读、可以引用、可以在对话里指出问题并提议改法,但不动手写、不新建、不整理。agent 可写的是 `EXPERIMENTS.md`(入口自动)、已有的 `docs/findings_*.md`、两个 `_index_*.md`、`docs/current_experiment_plan.md`、`docs/archive/` 的计划稿与流水账归档、以及周报初稿;findings 新卷只由我创建。

**新接手阅读顺序**(完整版见 `CLAUDE.md`):先读 `CLAUDE.md` → 再读 `docs/current_experiment_plan.md`(末尾「实验历史」看脉络、顶部看当前实验)→ 再从 `docs/_index_findings.md` 定位相关 findings 卷 → 再扫 `EXPERIMENTS.md` 最近若干行。
