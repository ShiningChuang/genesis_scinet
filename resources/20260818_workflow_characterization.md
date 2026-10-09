# Workflow 刻画调研 —— "一个 workflow 是怎么被刻画的"

> **任务来源**：`resources/meetings/20260818.md` 第十五节，KK 会后布置。
> **交付**：一组 slides，本周内邮件发 KK；2026-08-25(二) 全员讨论。
> **真正用途**：给第一层 **workflow 侧 API**（同纪要第十三节）找字段依据。
>
> **KK 的五个刻画维度**（原话见纪要第十五节表格）：
> ① 端点 ② 负载特征 ③ 负载分布 ④ SLA（带宽 / 延迟 / 完成时间）⑤ 论文/系统作者自己用来刻画 workflow 的量
>
> **两条会议约束**（贯穿全部分析）：
> - **要 workflow 对网络的需求，不要网络环境**（第五节 KK 纠正 Mariam）。拓扑、站点地址是静态给定的，不属于这份 API。
> - **必须撑得住多 workflow**（第七节）。一个 workflow = 一个虚拟用户 = 一组 endpoint 间的交互图，不是一条直线。
>
> **本文件维护**：AI 写入（经明确授权，属 CLAUDE.md §3「resources/ 人工独占」的例外）。逐份材料追加一节，最后做跨材料归并。

---

## 材料清单

| # | 材料 | 类型 | 状态 |
|---|---|---|---|
| 1 | [Pegasus WMS Reference Guide — Mapping](https://pegasus.isi.edu/documentation/reference-guide/mapping.html) | 系统文档 | 已分析（下） |
| | [同上 — Configuration/Profiles](https://pegasus.isi.edu/documentation/reference-guide/configuration.html) | 系统文档 | 已分析（作为 #1 的字段依据） |
| 2 | [PegasusHub — Workflows](https://pegasushub.io/pages/workflows.html)（+ [workflow-registry](https://github.com/pegasushub/workflow-registry)） | workflow 案例库 | 已分析（下） |
| 3 | [pegasus-isi/1000genome-workflow](https://github.com/pegasus-isi/1000genome-workflow) | 单个真实 workflow（代码 + 实测数据） | 已分析（下） |
| 4 | [WfCommons](https://wfcommons.org/) — WfFormat schema + WfInstances 318 实例 | 标准化刻画格式 + 实测数据集 | 已分析（下） |

---

## 材料 1：Pegasus WMS — Mapping / Site Selection

### 这是什么

Pegasus 是 USC/ISI 出的 **workflow management system（WMS）**，DOE / NSF 科学计算里长期在用（LIGO、CyberShake 等）。
这一页是它 Reference Guide 里的 **Mapping 章**，讲的是 Pegasus 的**规划器（planner）**如何把用户写的
**abstract workflow（抽象 DAG，DAX 格式）** 编译成 **executable workflow（可在具体资源上跑的 DAG）**。

Mapping 由 6 个 refinement step 串成：

1. **Data Reuse** —— 输出文件已在 Replica Catalog 里存在的节点，直接剪掉；
2. **Site Selection** —— 把抽象 job 映射到具体 compute site（用户点名的锚点在这里）；
3. **Job Clustering** —— 同站点的短作业合并，摊薄调度开销；
4. **Addition of Data Transfer and Registration Nodes** —— **往 DAG 里插入 stage-in / stage-out / 注册节点**；
5. **Addition of Create Dir and Cleanup Jobs** —— 建工作目录、清中间数据；
6. **Code Generation** —— 输出成 Condor DAG / shell / PMC。

**Site Selection 的可选算法**：`Random`、`RoundRobin`（按各站点已分配作业数排序轮转）、
`Group`（同 group 的作业绑到同一站点，靠 `PEGASUS profile key group` 关联）、
`Heft`（HEFT 调度，输入是**运行时估计 + 处理器数**）、`NonJavaCallout`（外部回调）。

### 对我们有用吗——有，但主要是**反面证据**

一句话：**Pegasus 完整回答了"一个 workflow 怎么被刻画"，但它的刻画里几乎没有网络。**
这恰恰是纪要第十三节 KK 那句"这样的 API 现在根本不存在"的**具体实证**。

按 KK 的五个维度逐条对：

| 维度 | Pegasus 里有什么 | 判断 |
|---|---|---|
| **① 端点** | 有一等公民概念：**site**（Site Catalog 里配置），区分 compute site / staging site / output site；数据位置由 **Replica Catalog** 给出（LFN → PFN，URL 带 scheme） | **有，但是"网络环境"侧的静态配置** —— 正是 KK 第五节要区分开的那半边。站点是管理域标识，不带地址/带宽/时延属性 |
| **② 负载特征** | 文件级：LFN、**file size**、transfer flag、registration flag；作业级：transformation 标识、DAG level/depth | **部分有**。每条 DAG 边上的数据量原则上可算出 → 这是最接近**流量矩阵**的东西 |
| **③ 负载分布** | 只能从 **DAG 结构 + `pegasus.runtime` 估计**间接推出；`clusters.size` / `clusters.num` / `clusters.maxruntime` 控制打包粒度 | **隐式，未声明**。没有任何"时间剖面 / 突发性"字段 |
| **④ SLA** | **无**。跨 mapping 页与 configuration 页均未出现 bandwidth / latency / deadline / SLA 任何一项 | **完全缺失** ← 本次调研最重要的一格 |
| **⑤ 系统自用的刻画量** | 见下方字段表 | **全是算力侧，零网络侧** |

### ⑤ Pegasus 实际用来刻画一个 job 的字段（`pegasus` namespace profile keys）

这是**现成的 API 字段依据**，KK 特别要的就是这一条：

| Key | 含义（文档原文/转述） |
|---|---|
| `pegasus.cores` | "The total number of cores, required for a job" |
| `pegasus.gpus` | "The total number of gpus, required for a job" |
| `pegasus.nodes` | "Indicates the number of nodes a job requires" |
| `pegasus.ppn` | "Indicates the number of processors per node" |
| `pegasus.memory` | "Indicates the maximum memory a job requires in MB" |
| `pegasus.diskspace` | "Indicates the maximum diskspace a job requires in MB" |
| `pegasus.runtime` | 作业预期运行时长（秒），在 Transformation Catalog 里给 |
| `pegasus.maxwalltime` | "the maximum walltime in minutes for a single execution of a job" |
| `pegasus.checkpoint.time` | 期望多久后给作业发 TERM 信号（分钟） |

聚合/传输相关：`pegasus.clusters.size`、`pegasus.clusters.num`、`pegasus.clusters.maxruntime`、
`pegasus.stagein.clusters`、`pegasus.stageout.clusters`（每个 compute site 的 stage-in/out 作业数上限）。
Globus/GRAM 侧另有 `globus.queue`、`globus.project`、`globus.maxtime`、`globus.maxcputime`、`globus.maxmemory/minmemory`。

**九个资源字段，全部是 CPU / GPU / 内存 / 磁盘 / 时间。没有一个描述网络。**

### 网络在 Pegasus 里的位置

网络**不是被声明的需求，而是被生成的副作用**：

- 传输在 mapping 第 4 步被**自动插进 DAG**，成为 stage-in / stage-out 节点；
- 实际搬运交给 **`pegasus-transfer`**，它按 URL scheme 选工具：`globus-url-copy`、`s3cmd`、`irods-transfer`、`scp`、`wget`、`cp`、`ln`；
- 也就是说：**能选协议，不能提需求**。没有"我要 X Gbps"、"我要在 T 之前完成"这样的表达。

顺带一个对我们很关键的推论：**Site Selection 的五个算法没有一个看网络状态**。
HEFT 用的是运行时估计和处理器数，Random/RoundRobin 连这个都不看。
→ **作业放置决策是 network-blind 的。** 这是 SciNet 可以直接指认的一处空白。

### 给 slides 的可用论点

1. **成熟 WMS 的 workflow 刻画 = 一张 DAG + 九个算力字段 + 静态站点表**。这是"现状基线"，可以直接当 slide 一页。
2. **传输被当成副产品自动生成，不是被声明的需求**。workflow 从来没有机会说"我需要多少带宽 / 我几点前要完"。
3. **调度对网络盲**。site selection 不看链路状态，所以再好的网络能力也无法被 workflow 层利用。
4. → **第一层 API 的最小增量**：在 Pegasus 这类已有刻画之上，补的正是 KK 第十三节说的那两类字段——
   **QoS（带宽 / 延迟 / 完成时间）** 与 **客户类别（硬 deadline vs 弹性）**。
   这给了一个很干净的叙事：不是发明新语言，而是给已有 workflow 描述**补上缺的那一维**。

### 局限与待补

- 这是**系统文档，不是论文**，拿不到"论文作者怎么刻画 workflow"的那一层（KK 第五维的另一半），也没有真实负载的量化分布。
- **"无 SLA/带宽/deadline 字段"这一负面结论**，来自对 mapping 与 configuration 两页的抓取，两处独立一致，**置信度高但未对全站文档穷尽核对**。若要写进 slides 当强论断，建议再对 Pegasus 全文档做一次关键词核对。
- Pegasus 与 **WfCommons / WfBench**（纪要推测的 Raphael = Rafael Ferreira da Silva）同源，他曾在 ISI Pegasus 组。
  **WfInstances / WfFormat schema** 会比本页更接近我们要的东西——它按 task 记录 bytes read/written、runtime、机器信息，是量化的负载刻画。**建议作为下一份材料。**

---

## 材料 2：PegasusHub — Workflows Gallery

### 这是什么

**PegasusHub 是 Pegasus 的社区案例库 / 应用商店**，不是研究产物，也不是 benchmark suite。
官网自述：

> "The centralized ecosystem for discovering, learning, and deploying high-throughput computing workflows using Pegasus-WMS."

> "a centralized repository of production-ready workflows contributed by researchers around the world"

站点由三块组成：**Academy**（Jupyter 教程 / 案例）、**Workflows Gallery**（本页）、**Build & Deploy**（Cookiecutter/Copier 脚手架，
把 workflow 部署到本地容器 / HPC 集群 / Open Science Grid）。由 NSF 资助，ISI 维护。

**它解决的问题是"新用户不会写 workflow"**：官方说法是让人
"search for a blueprint that matches your domain … and adapt it to fit your own computational needs"。
所以这些 workflow 的定位是 **可改的模板（blueprint）**，不是标准化的测试负载。

### 后台是怎么组织的

Workflows 页是**前端从一个 JSON 动态渲染**的（直接抓 HTML 拿不到列表），真正的数据源在
[`pegasushub/workflow-registry`](https://github.com/pegasushub/workflow-registry)：

- `data/workflows.json` —— 注册表索引，**PegasusHub 运行时读的唯一真相源**；
- 每个 workflow 一个 `<name>.md`，YAML frontmatter + 描述 + 文件说明 + 怎么跑；
- 投稿走 GitHub Issue 模板或 PR；要求 Pegasus >= 5.0.0、仓库公开。

**每条注册表记录的全部字段**：
`github_owner` / `github_repo` / `pegasus_version` / `Topic` / `license` / `last_verified` / `image` / `name` / `description`。

### 目前收录的 15 个 workflow

| id | 领域 | 是什么 |
|---|---|---|
| `1000genomes` | bioinformatics | 用 1000 Genomes Phase3 数据按染色体做突变重叠分析，产出零假设分布 |
| `variant-calling` | bioinformatics / genomics | 变异检测 |
| `sra-search` | bioinformatics / genomics | SRA 序列检索 |
| `montage-v3` | astronomy | Montage 天文图像拼接（经典 workflow benchmark） |
| `freesurfer` | brain imaging | FreeSurfer 脑影像处理，跑在 OSG 上 |
| `rosetta` | protein folding | Rosetta 蛋白折叠 |
| `orcasound` | machine learning | 虎鲸声音识别 |
| `lung-seg` | machine learning | 肺部实例分割 |
| `mask-detection` | ML / optuna / pytorch | 口罩检测 + 超参搜索 |
| `fb-nlp` | ML / NLP | NLP 流水线 |
| `compare-llm` | machine learning | 比较多个 LLM |
| `diamond-workflow` | training | **结构原型：菱形**（1→2→1） |
| `split-workflow` | training | **结构原型：扇出** |
| `merge-workflow` | training | **结构原型：扇入** |
| `process-wf` | training | **结构原型：单节点** |

### 对我们有用吗

**作为"刻画量"的来源：几乎没用。** 注册表的字段里
**没有任务数、没有数据量、没有运行时、没有端点、没有 SLA**——一个量化字段都没有
（`description` 在 `workflows.json` 里甚至 15 条全是空串，描述只存在于各自的 `.md`）。
它是**编目**，不是**刻画**。这一点本身可以进 slides：社区级的 workflow 共享设施，元数据里完全没有性能/资源维度。

**但有三处真实价值**：

1. **领域普查**——真实科学 workflow 的分布长这样：生信 3、天文 1、脑影像 1、蛋白 1、ML 5、教学玩具 4。
   可以用来说明"workflow"不是一个同质的东西。
2. **结构原型**——`diamond` / `split` / `merge` / `process` 这四个教学 workflow 就是 DAG workflow 的**基本图元**
   （单节点 / 扇出 / 扇入 / 菱形）。真实 workflow 基本是这几种 motif 的组合与嵌套。
   这是"workflow 长什么样子"最简洁的回答，**适合做 slides 的一页**。
3. **每条记录都带 GitHub 仓库 + DAG 结构图**——真正的形状和规模在仓库里，特别是**生成器脚本**
   （如 1000genomes 的 `daxgen.py`）。读生成器可以得到"任务数 = f(输入规模)"的精确关系，这是注册表本身给不了的。

### 两条对项目直接相关的观察

- **收录里没有 HEP。** 15 个里一个高能物理 workflow 都没有。
  这印证了纪要第十四节 Mariam 要向 Raphael 单独去要 HEP workflow 的必要性——公开案例库里拿不到。
- **全部是单站点 / HTC 型 workflow。** 部署目标是"本地容器 / HPC 集群 / OSG"，
  注册表里**根本没有"端点"这个概念**。它们的刻画天然是"多少个任务、多少 CPU 小时"，而不是"站点之间搬多少数据"。
  → 与材料 1 的结论同向并加强：**WMS 生态从数据模型到社区元数据，整条链路都不把网络当成一等公民。**
  我们要的那种多端点、跨机构、带 SLA 的 workflow 刻画，在这里是缺位的。

### 待补

- 若要拿到量化刻画，得**下钻到单个仓库**读生成器与 DAG 图。**`1000genomes` 是首选**：数据密集、有明确输入规模参数、
  且是 WfCommons 的 benchmark workflow 之一，能同时接上下一份材料。

---

## 材料 3：1000genome-workflow —— 第一个能量化到底的 workflow

仓库：<https://github.com/pegasus-isi/1000genome-workflow>
**这是本次调研第一份能同时给出「结构」「规模」「实测」三样东西的材料**，也是 KK 第五维（作者自己用什么量刻画）唯一有实证的一份。

### 科学内容

用 1000 Genomes Project Phase3 数据（2,504 个个体、26 个人群）做**突变重叠分析**，
为"某个突变是否与疾病相关"的统计检验提供零假设分布。五类任务：

| 任务 | 做什么 |
|---|---|
| `individuals` | 按染色体解析 Phase3 数据，提取每个个体带哪些 SNP 变异 |
| `individuals_merge` | 把同一染色体被切开的多个 chunk 合并 |
| `sifting` | 计算 SNP 的 SIFT 分数（该氨基酸替换是否有表型影响） |
| `mutation_overlap` | 按人群、按染色体，度量个体两两之间的突变重叠 |
| `frequency` | 随机抽个体，度量突变重叠的频率（不看 SIFT 分数） |

### DAG 结构（从 `daxgen.py` 读出，非猜测）

设 **C** = 染色体数（`data.csv` 行数，仓库自带 10 行），
**I** = 每条染色体切几个 `individuals` 任务（`-i/--individuals-jobs`，默认 1），
**P** = 人群数（`data/populations/` 下 7 个：AFR / ALL / AMR / EAS / EUR / GBR / SAS）。

```
每条染色体 c:
  I × individuals(ALL.chr{c}.vcf, columns.txt) ──→ chunk 输出
      └─ 1 × individuals_merge(全部 chunk)      ──→ merged chr{c}
  1 × sifting(annotation vcf)                    ──→ sifted.SIFT.chr{c}.txt

对每个 (染色体 c, 人群 p):
  1 × mutation_overlap(merged, sifted, pop, columns) ──→ chr{c}-{p}.tar.gz      [stage_out=True]
  1 × frequency        (merged, sifted, pop, columns) ──→ chr{c}-{p}-freq.tar.gz [stage_out=True]
```

**任务总数 = C·(I + 2) + 2·C·P**

**已用实测数据交叉验证**：`analysis/breakdown-1000genome.csv` 的那次运行是 C=1, I=10 →
10 + 1 + 1 + 2×7 = **26**，作业 ID 恰好是 `ID0000001`–`ID0000026`。公式成立。

形态上就是材料 2 那四个图元的组合：**扇出（individuals）→ 扇入（merge）→ 再扇出（population × 2 种分析）**。

### 实测：执行时间（NERSC Cori 单节点 Haswell，C=1, I=10）

| 任务类 | 时长(s) | 占比 |
|---|---:|---:|
| Individuals | 11431 | **81.85%** |
| Frequency | 1492 | 10.68% |
| Individuals_Merge | 500 | 3.58% |
| Mutation_Overlap | 468 | 3.35% |
| **Stage_Out** | **34** | **0.24%** |
| **Stage_In** | **21** | **0.15%** |
| Auxiliary | 16 | 0.11% |
| Sifting | 6 | 0.05% |
| **总计** | **13967 (3.9h)** | 100% |

> **数据传输占总时长 0.39%。**

### 实测：负载随「切分粒度」变化（`analysis/pegasus-io-1000genome.csv`，3 trial 取均值/最大）

| I（每染色体 individuals 任务数） | 任务数 | 总输出(MB) | 单任务输出(MB) | 峰值内存 maxRSS(GB) |
|---:|---:|---:|---:|---:|
| 2 | 2 | 184.2 | 92.1 | 6.41 |
| 5 | 5 | 184.0 | 36.8 | 4.14 |
| 10 | 10 | 156.8 | 15.7 | 3.41 |
| 16 | 16 | 119.3 | 7.5 | 3.08 |

（内存与 README 自报的 6.10 / 3.93 / 3.17 / 2.93 GB 同量级、同趋势；README 报的是 per-job 要求，此处取 maxRSS 峰值。）

### 输入数据规模

- 仓库自带 10 条染色体的 `ALL.chr{N}.250000.vcf.gz`，每个 **约 42–46 MB**（压缩态，各 250,000 行）；
- `sifting` 的输入（annotation VCF）不在仓库，由 `prepare_input.sh` 另取；
- **只有 `mutation_overlap` 和 `frequency` 的输出 `stage_out=True`**，其余中间产物全部 `stage_out=False`——
  即**出口数据 = 2·C·P 个 tar.gz**，中间态不出站点。

### 按 KK 五维归档

| 维度 | 这个 workflow 给了什么 | 够不够 |
|---|---|---|
| **① 端点** | **几乎没有**。只有 Pegasus 的 `local` / `cori` 两个执行站点选项（`--execution-site`），数据靠 Bosco/SSH 从提交端搬到 Cori | ✗ 单站点模型，没有多端点概念 |
| **② 负载特征** | **有且精确**：输入 42–46 MB/染色体、单任务输出 7.5–92 MB、峰值内存 2.9–6.4 GB、单任务时长 ~11,300 s | ✓ 最好的一份 |
| **③ 负载分布** | **有**：DAG 拓扑给出并发结构（I 路并行 → 汇聚 → 2P 路并行），实测给出各任务类时长占比 | ✓ 部分（时间剖面可从 DAG+时长推，未直接给） |
| **④ SLA** | **无**。没有 deadline、没有带宽需求、没有延迟约束 | ✗ 与材料 1 一致 |
| **⑤ 作者自用的刻画量** | `任务数` / `单任务输入行数` / `单任务输出字节数` / `峰值内存 maxRSS` / `单任务时长` / `各任务类时长占比` / `切分参数 I` | ✓ **这七个量是最直接的 API 字段候选** |

### 三条给 slides 的核心论点

**1. 负载不是 workflow 的属性，是 (workflow, 切分参数) 的属性。**
同一份输入、同一个科学问题，仅仅把 `I` 从 2 调到 16，任务数 ×8、单任务内存 ÷2、单任务输出 ÷12、总输出还掉了 35%。
→ **API 若只描述"这个 workflow 需要什么"，是不可能定义清楚的**；必须要么把切分旋钮暴露给网络侧，要么在**规划之后**才做刻画。
这是本次调研对 API 设计影响最大的一条。

**2. 作者自己用来刻画 workflow 的七个量，全是"任务级 + 算力/存储级"，没有一个是网络级。**
连 `analysis/` 目录里专门做 I/O 分析的脚本（`analyze-io.py`），量的也是**任务写了多少字节**，不是**跨站点搬了多少字节**。
→ 再次印证材料 1、2：整个 WMS 生态的刻画词汇表里没有网络。

**3. ⚠️ 传输只占 0.39%——这条对项目是把双刃剑，必须正视。**
在这个被公认为"数据密集"的经典科学 workflow 里，stage-in + stage-out 合计 55 秒 / 3.9 小时。
**这正解释了为什么 WMS 从不为网络建模：对这类 workflow，网络本来就不是瓶颈。**

必须同时说明的**边界条件**（否则这个数字会被误用）：
- 该次运行是 **NERSC Cori 单节点**，输入数据已提前放在 Cori 本地（README 明确建议用 `--src-path` 指向本地目录以"避免 staging 大量数据的开销"）——**这几乎是最有利于传输的配置**；
- 输入总量仅 ~450 MB（10 条染色体压缩态），出口是 2·C·P 个小 tar.gz；
- 是**单站点 HTC**，不是跨机构。

→ **给项目的推论**：SciNet 要打的不是这一类 workflow。
"传输占比 0.39%" 恰恰是**筛选目标 workflow 的判据**——我们需要的是传输占比高、跨机构、多端点的那一类，
也就是 HEP。**这给纪要第十四节"必须拿到 HEP workflow"提供了一个量化理由，而不只是偏好。**
建议把这一条作为 slides 里向 KK 提的问题：**我们的第一版 API 是为哪一类 workflow 设计的？**

### 待补

- 仓库有 `analysis/log.tar.gz`（24 MB 原始运行日志）与 `plot.ipynb`，若需要更细的 per-task 时间序列可以下钻。
- `breakdown-1000genome.csv` 中 `frequency_ID0000016/20/26` 各出现两次（疑为重试或两次测量合并），未深究，引用单条时长时需注意。

---

## 材料 4：WfCommons —— workflow 刻画的事实标准

官网 <https://wfcommons.org/>　仓库 <https://github.com/wfcommons>
**这是本次调研最重要的一份材料。** 它就是"一个 workflow 是怎么被刻画的"这个问题在学术界的标准答案。

### 这是什么

自述："an open-source ecosystem of workflow execution instances, synthetic workflow generators, and benchmark specifications"。
六个组件：

| 组件 | 作用 |
|---|---|
| **WfFormat** | JSON Schema，"a common representation for workflow instances and generators" |
| **WfInstances** | 真实运行实例库，**318 个实例 / 31+ 个科学应用 / 6 种 WMS** |
| **WfChef** | 从真实实例里挖掘"recurring dependency patterns and statistical distributions"，产出 recipe |
| **WfGen** | 由 recipe 生成合成实例，"preserving structure, runtime, and I/O distributions at any scale" |
| **WfBench** | 生成 benchmark，**CPU / 内存 / I/O 压力可配置** |
| **WfSim** | 对接仿真框架，不占真实算力评估调度器 |

**维护方**：University of Hawaiʻi at Mānoa + **Oak Ridge National Laboratory** + San Diego Supercomputer Center；NSF + **DOE** 资助。
框架论文作者：Coleman, Casanova, Pottier, Kaushik, Deelman, **Ferreira da Silva**。

> ⚠️ **与项目的直接关联**：纪要里待核对的 "Raphael"（`[推测]` Rafael Ferreira da Silva，ORNL）正是这条线的作者之一。
> KK 说"benchmark 太宽泛了，我想看的是具体的 workflow 例子"——**WfCommons 恰好就是"benchmark"与"具体实例"两样都做的那个项目**。
> 若推测成立，Mariam 要来的 workflow 极可能就是 WfFormat 格式的。**本节应作为下周讨论的主要依据。**

### WfFormat v1.6 完整字段（KK 第五维的标准答案）

顶层：`name*` / `description` / `createdAt` / `schemaVersion*` / `runtimeSystem{name*,version*,url}` / `author{name*,email*,institution,country}` / `workflow*`
（`*` = schema 必填）

**结构与执行是分开的两半**，这个划分本身对我们很重要：

**`workflow.specification`（机器无关，描述"这个 workflow 是什么"）**

| 字段 | 含义 |
|---|---|
| `tasks[].name*` / `id*` | 任务名与唯一 ID |
| `tasks[].parents*` / `children*` | DAG 依赖边 |
| `tasks[].inputFiles` / `outputFiles` | 任务的输入/输出文件 |
| `files[].id*` / `sizeInBytes*` | **文件大小（字节）** |
| `metrics.numberOfTasks` | 任务数 |
| `metrics.numberOfFiles` | 文件数 |
| `metrics.sumOfFileSizesInBytes` | **全部文件总字节数** |
| `metrics.numberOfLevels` | **DAG 层数（深度）** |
| `metrics.minimumWidth` / `maximumWidth` | **各层并行度的最小/最大值（宽度）** |

**`workflow.execution`（一次真实运行的测量）**

| 字段 | 含义 |
|---|---|
| `makespanInSeconds*` | 整个 workflow 的墙钟时长 |
| `executedAt*` | 起始时间戳 |
| `tasks[].runtimeInSeconds*` | 任务时长 |
| `tasks[].command{program, arguments}` | 实际执行的命令 |
| `tasks[].coreCount` | 用了几核 |
| `tasks[].avgCPU` | 平均 CPU 利用率（%） |
| `tasks[].readBytes` / `writtenBytes` | **读/写总字节** |
| `tasks[].memoryInBytes` | 常驻内存 |
| `tasks[].energyInKWh` / `avgPowerInW` | 能耗 / 平均功率 |
| `tasks[].priority` | 任务优先级 |
| `tasks[].machines` | 该任务用了哪些机器 |
| `machines[].nodeName*` / `system` / `architecture` / `release` / `memoryInBytes` / `cpu{coreCount, speedInMHz, vendor}` | 机器描述 |
| `metrics.sumTaskRuntimesInSeconds` | 总工作量 |
| `metrics.totalNumBytesRead` / `totalNumBytesWritten` | 总读/写字节 |

### 🔴 最关键的一条：整个 schema 里没有任何网络字段

逐条核过 v1.6 全部字段——**没有 bandwidth、没有 latency、没有 deadline、没有 SLA、没有站点/地理位置、没有传输时间、没有端点、没有 IP/地址**。

- `machines[]` 有 `nodeName`、CPU、内存，**但没有位置、没有网卡、没有链路属性**；
- `readBytes` / `writtenBytes` 是**任务对文件系统的读写**，不是**跨站点搬运的字节**；
- **150 / 318 个实例用了不止一台机器**（分布见下），但 schema **没有任何地方记录"哪些字节在机器之间流动过"**。

> **这就是我们要填的洞。** 材料 1（Pegasus 字段）、材料 2（PegasusHub 元数据）、材料 3（1000genome 自评量）三处独立观察，
> 在 WfCommons 这个**社区级事实标准**上得到最终确认：**workflow 刻画的标准词汇表里，网络不存在。**

### 实证：318 个实例里，哪些字段真的被填了

schema 允许的和大家真的会填的，是两回事。全量统计（`schemaVersion` 318/318 全是 1.6）：

| `execution.tasks` 字段 | 被填的实例数 | 占比 |
|---|---:|---:|
| `runtimeInSeconds` | 318 | **100%** |
| `command` | 318 | **100%** |
| `machines` | 287 | 90% |
| `avgCPU` | 182 | 57% |
| `coreCount` | 166 | 52% |
| `priority` | 137 | 43% |
| `executedAt` | 136 | 43% |
| `memoryInBytes` | 81 | 25% |
| **`readBytes` / `writtenBytes`** | **45** | **14%** |
| `energyInKWh` / `avgPowerInW` | 0 | **0%** |

**结论：社区实际测量的是「时间」和「CPU」。** 最接近数据量的 `readBytes`/`writtenBytes` 只有 14% 的实例填了，能耗一个都没填。
→ 这比 schema 本身更能说明问题：**不是没地方写网络，是连本地 I/O 都没人认真记。**

每实例使用的机器数分布：`1台:168, 2台:36, 3台:21, 4台:54, 5台:25, 6台:8, 7台:5, 0台:1`
→ **近一半实例是多机的**，但正如上面所说，机器之间的数据流动完全没有被记录。

### 规模普查：318 个实例长什么样

| 应用 | 实例数 | 任务数(min–max) | 层数(中位) | 最大宽度(中位) | makespan(s)中位 | 总文件大小(GB)中位 |
|---|---:|---:|---:|---:|---:|---:|
| pegasus/montage | 17 | 58–**9805** | 8 | 516 | 2172 | 4.51 |
| pegasus/cycles | 24 | 67–6543 | 4 | 322 | 1524 | 4.64 |
| nextflow/ro-crate | 101 | 101–2324 | 14 | 171 | 10634 | 20.68 |
| snakemake/varlociraptor | 8 | 91–1783 | **37** | 28 | 15959 | 78.28 |
| pegasus/epigenomics | 26 | 41–1695 | 9 | 125 | 1064 | 5.59 |
| pegasus/seismology | 11 | 101–1101 | 2 | 600 | 1063 | 0.01 |
| makeflow/bwa | 15 | 104–1004 | 3 | **1000** | 4978 | 0.006 |
| pegasus/1000genome | 22 | 52–902 | 3 | 216 | 2869 | 30.24 |
| pegasus/soykb | 10 | 96–676 | 11 | 200 | 23044 | 2.85 |
| snakemake/RASflow | 7 | 11–501 | 4 | 25 | 694 | 0.35 |
| makeflow/blast | 15 | 43–303 | 3 | 100 | 3720 | 0.0005 |
| nextflow/legacy | 15 | 11–265 | 10 | 20 | 3731 | 0.33 |
| snakemake/rna-seq-star-deseq2 | 19 | 45–251 | 7 | 65 | 6028 | **144.08** |
| pegasus/srasearch | 25 | 22–104 | 4 | 31 | 7576 | 43.11 |
| streamflow/1000genome | 1 | 26 | 4 | 14 | 256 | 4.12 |
| helloworld | 2 | 5–10 | 4 | 4.5 | 549 | 0.10 |

**"workflow"的量级跨度**：任务数 5 → 9,805（3 个数量级）；层数 2 → 37；宽度 4 → 1,000；数据量 0.5 MB → 144 GB（5 个数量级）。
→ 任何"一个 workflow 需要 X"的说法都必须带规模参数，这与材料 3 的结论一致。

### 数据密集度排序（用于挑目标 workflow）

用 `sumOfFileSizesInBytes / sumTaskRuntimesInSeconds` 作**每核心秒搬运字节数**的粗略代理，中位值：

| 应用 | MB / core-second |
|---|---:|
| snakemake/rna-seq-star-deseq2 | **8.31** |
| snakemake/varlociraptor | 4.76 |
| streamflow/1000genome | 2.99 |
| pegasus/1000genome | 1.23 |
| pegasus/srasearch | 0.99 |
| pegasus/montage | 0.52 |
| pegasus/epigenomics | 0.48 |
| pegasus/cycles | 0.36 |
| nextflow/legacy | 0.19 |
| pegasus/soykb | 0.06 |
| nextflow/ro-crate | 0.05 |
| pegasus/seismology | 0.03 |
| makeflow/bwa | 0.002 |

⚠️ **这个指标很粗**，只能当排序用不能当结论：文件大小按去重后总量算、分母是总核心工作量而非 makespan、
且**它衡量的是本地 I/O 强度而不是网络强度**（这些实例几乎都是单站点的）。
真正要判断"网络相关性"，需要的是**跨站点字节数 / makespan**，而这个量 **WfFormat 记不了**。

### 按 KK 五维归档

| 维度 | WfCommons 给了什么 | 判断 |
|---|---|---|
| **① 端点** | `machines[]` 有 nodeName / CPU / 内存，近一半实例是多机 | **✗ 有"机器"无"端点"**：没有位置、没有网络属性、没有机器间流量 |
| **② 负载特征** | `files[].sizeInBytes`、`readBytes`/`writtenBytes`、`memoryInBytes`、`coreCount`、`avgCPU` | **✓ 最完整的一份**，但 I/O 字段实际填充率仅 14% |
| **③ 负载分布** | `numberOfLevels`、`minimumWidth`/`maximumWidth`、DAG 拓扑、`executedAt` + `runtimeInSeconds` 可还原时间线 | **✓ 结构维度最好**：层数 + 宽度就是并行度剖面 |
| **④ SLA** | **无**。schema 里唯一沾边的是 `priority`（43% 实例有填），但它是调度优先级，不是 SLA | **✗** |
| **⑤ 作者自用的刻画量** | 见上方完整字段表 + 填充率统计 | **✓✓ 本次调研的标准答案** |

### 给 slides 的核心论点

1. **"一个 workflow 是怎么被刻画的" 有标准答案，就是 WfFormat v1.6。**
   拆成两半：`specification`（DAG + 文件大小 + 层数/宽度，机器无关）与 `execution`（时长 + 核数 + CPU + 内存 + 读写字节，一次运行的测量）。
   这个二分法**建议直接被我们的 API 采纳**——它正好对应"workflow 声明什么"与"实际发生了什么"。

2. **标准词汇表里没有网络。** 不是遗漏一两个字段，是整个维度缺席：无带宽、无延迟、无 deadline、无位置、无跨机流量。
   四份材料独立指向同一结论。**这是第一层 API 存在必要性的最强论据。**

3. **连本地 I/O 都只有 14% 的实例记录。** 社区测的是时间和 CPU。
   → 我们如果要求 workflow 声明网络需求，**面对的不只是"字段不存在"，还有"根本没人测过"**。
   这对第一版 API 应该做多重是个现实提醒：字段要少、要能估、要允许缺省。

4. **规模跨 3–5 个数量级**（任务 5→9805，数据 0.5MB→144GB）。API 必须把规模当参数，不能假设一个"典型 workflow"。

5. **WfChef / WfGen / WfBench 这条链是现成的实验基础设施**：从真实实例挖 recipe → 任意规模生成合成 workflow → 生成可配置 CPU/内存/IO 压力的 benchmark。
   **如果我们要做"多 workflow 竞争共享"的实验（纪要第七节 Harvey 的真问题），这套东西可以直接用来造多个并发 workflow 负载。**
   这可能比 VIT 那条线更快见效——值得在下周提。

### 待补 / 局限

- **仍然没有 HEP。** 31 个应用覆盖生信、天文、农业、地震学、NLP，**依旧一个高能物理都没有**。
  三份材料（PegasusHub、WfInstances、Pegasus 文档）一致缺失 → **HEP workflow 只能从 Raphael 手里拿，公开数据集里没有。**
- 数据密集度指标是本地 I/O 代理，非网络强度，见上方警告。
- 未读 WfCommons 框架论文原文（Coleman et al.）与 WfChef/WfBench 论文；若要引用"作者如何论证这些字段的选择"，需补读。
- 本次分析用的实例库已 clone 到会话 scratchpad（887 MB，`wfi/`），**属临时文件不入库**；需要复现时重新 `git clone https://github.com/wfcommons/WfInstances`。
