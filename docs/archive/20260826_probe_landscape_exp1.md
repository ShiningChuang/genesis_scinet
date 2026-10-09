# Current Experiment Plan

> 一句话总览:Exp1 是一次背景调研而非运行实验——建立 AI 驱动科学实验闭环的系统全景，理解 AI 如何选择实验、编排 workflow、调用设备与利用 digital twin，并据此看清 SciNet 在完整科研 pipeline 中的位置。

## 目标

本阶段不提出或验证性能假设，也不运行代码。目标是形成一套足以支撑后续方向收敛的判断框架，回答四组问题:

1. **概念边界**:AI for Science、autonomous experimentation、self-driving laboratory、digital twin、scientific workflow、AI agent 分别指什么，彼此是什么关系?
2. **闭环怎样运行**:AI 如何从历史数据中选择下一次实验，怎样做自动调参和实验规划，怎样把计划安全地转成仪器动作，再怎样利用结果继续迭代?
3. **系统怎样支撑**:一个端到端 autonomous science pipeline 需要哪些控制、workflow、数据、计算、网络、可靠性和 provenance 组件?
4. **现有工作做到哪里**:代表性论文和平台解决了什么问题、依赖什么基础设施、还缺什么；其中哪些问题落在 SciNet 的网络与数据传输边界内?

Exp1 完成时应能:

- 画出一个端到端闭环并解释每层的职责与接口；
- 比较 AI 选择实验的主要方法及其适用条件；
- 解释高层 AI planner 与底层设备控制、安全联锁之间为什么必须分层；
- 区分 simulation、emulation、digital shadow 与严格意义的 digital twin；
- 按功能而不是按热词整理代表论文和平台；
- 从上述全景中提炼出后续询问合作方、判断 SciNet 研究边界所需的具体问题。

## 关键要素

- **研究对象**:AI 驱动的科学实验闭环及其系统基础设施，而非某一科学领域的预测模型。
- **资料范围**:
  - AI 如何用于科学实验；
  - autonomous experimentation；
  - self-driving laboratory；
  - digital twin；
  - AI 如何选择实验；
  - AI 如何控制实验设备；
  - AI 如何做自动调参和实验规划；
  - scientific computing workflow；
  - AI agent 如何参与科研 pipeline；
  - 相关系统论文与平台。
- **分析主线**:

  ```text
  科学目标 / 约束
        ↓
  planner / experiment-selection policy
        ↓
  workflow orchestrator / resource scheduler
        ↓
  protocol compiler / device-control layer / safety interlocks
        ↓
  physical instrument or calibrated digital twin
        ↓
  data acquisition / transfer / provenance / analysis
        └──────────────────────→ 更新模型并选择下一次实验
  ```

- **证据口径**:
  - 概念定义优先采用标准机构、项目官方文档和同行评审论文；
  - 平台能力以论文、官方文档或代码仓库实际声明为准；
  - 论文中的单个成功案例不外推为通用能力；
  - 事实、作者主张和我们针对 SciNet 的推断分开表述；
  - `resources/conversation_20260727.md` 只作为项目背景线索，不作为外部事实的最终证据。
- **产出形式**:
  - 一张概念与系统分层图；
  - 一份核心术语和方法说明；
  - 一张代表论文 / 平台对照表；
  - 一组面向 SciNet 合作方的核验问题；
  - 本轮调研结论先在对话中供我消化，再由我决定哪些内容人工沉淀进最新一卷 `docs/knowledge_{YYYYMMDD}.md`（当前为 `docs/knowledge_20260728.md`）。
- **运行与数据**:不适用。本阶段不创建 config、不调用 `scripts/run_experiment.py`、不产生 `runs/`、不写 `EXPERIMENTS.md` 或 `docs/findings_{YYYYMMDD}.md`。
- **硬性约束**:只做背景理解和方向判断，不提前实现系统，不把可能的研究方向写成已经确定的项目任务。

## 可行性与风险

- **术语边界模糊**:很多工作把自动化工作流、机器人实验室和真正闭环的自主实验都称为 autonomous。调研时需检查系统是否真的根据新观测改变下一步实验，而不是只执行预先写好的批处理流程。
- **digital twin 容易被泛化**:只有虚拟模型而没有特定真实对象、状态同步、校准或验证时，更接近 simulator / emulator，而不能仅凭名称视为严格的 twin。
- **demo 与系统能力不可混同**:单一化学反应或材料案例成功，不代表平台已具备跨领域的规划、容错、审计或规模化能力。
- **AI 选择与 AI 控制是两层问题**:选择下一个实验通常是统计决策；把它可靠、安全地执行则属于 workflow、控制和仪器集成。将两者混写会遮蔽真正的系统研究问题。
- **agent 热度可能掩盖基础设施**:LLM agent 能生成计划或工具调用，不等于它能直接、安全地控制仪器；实际系统仍需 typed API、约束检查、权限、联锁、状态机、失败恢复和 provenance。
- **与 SciNet 的关联需要克制**:完整 autonomous lab 是应用场景；SciNet 当前明确关注的是其下方跨机构网络、数据传输、workflow 协调与可靠性。不能因调研范围较大而把整个闭环误认成本组交付范围。

## 步骤与进度

- [x] **S0 对齐**:确认 Exp1 只做背景调研，不运行实验；确定研究问题、证据口径和产出。
- [x] **S1 建立概念地图**:定义并区分 AI for Science、autonomous experimentation、self-driving lab、scientific workflow、AI agent 和 digital twin。
- [x] **S2 拆解决策闭环**:调研 AI 选择实验、自动调参、主动学习、Bayesian optimization、多目标 / 约束 / 成本感知规划及停止条件。
- [x] **S3 拆解执行闭环**:调研 protocol 表达、workflow 编排、设备 API、控制系统、安全联锁、数据采集、provenance、失败恢复和 human-in-the-loop。
- [x] **S4 整理代表工作**:按“实验选择、实验室自动化、计算工作流、agent、digital twin、跨站数据 / 网络”分类比较代表论文和平台。
- [x] **S5 映射到 SciNet**:标出完整闭环中 SciNet 负责与不负责的层，提炼需要向合作方核验的问题以及后续可测系统问题的来源。
- [x] **S6 用户消化与收敛**:决定下一轮先深入 scientific workflow，理解各系统组件在一个具体闭环中的位置以及 SciNet 的优化边界。
- [x] **S7 具体 workflow 解剖**:以“站点 A 科学仪器采集 → edge 预处理 → 跨站传输 → 站点 B HPC/GPU 分析 → AI 动态选择下一次测量”为组合型教学示例，标出异构资源、queue、staging、environment、恢复、provenance 和动态任务的位置，并区分 SciNet 能直接影响与不能直接影响的部分。该例综合了真实论文中分别展示的自主 X-ray 测量、跨设施 instrument-to-HPC workflow 与 VIT/EPICS/container federation，但不是对某一个已部署系统的逐项复现，也尚未确认是合作方 SciNet workload。
- [x] **S8 Intent 与 Flow Engine 解剖**:结合首次 SciNet 周会 slides 和 ESnet SENSE 官方资料，区分 workflow intent、network service intent、operator/network policy 与 SLA，并用 HEP 数据在计算作业开始前跨站 staging 的例子说明 SciNet Flow Engine 如何把声明式需求转成跨域资源查询、NDT 验证、agent/hardware action、监控、冲突处理和闭环适配。
- [x] **S9 外部生态与 UCR 接口定位**:核对 ESnet、IRI / IRI Facility API、AmSC Product Catalog、SC26 NRE 与 NVIDIA Omniverse 的官方资料；区分网络基础设施、跨设施公共 API、能力目录、现场 demo 通道和 digital-twin 平台，并据首次周会 slides 将 UCR 当前高层任务收敛为 agent / monitoring / API 与合作方 NDT 的集成，而不把尚未拿到的 NDT 实现细节误写成既定架构。
- [x] **S10 Agent 通信顶会论文调研**:筛查近三届 OSDI、NSDI、SOSP、ICML、MLSys 的正式论文，将 agent 通信拆为消息语义、通信拓扑、依赖与异步调度、跨站可靠传递、telemetry/反馈以及 policy/safety 六层；区分直接研究 multi-agent communication 的 ML 工作与可作为 SciNet Agent–NDT–hardware 基础设施的系统工作，并提炼仍未被现有论文覆盖的 WAN-aware、NDT-validated、可追溯跨域 agent communication 问题。

## 待办与决策

- **结题时无未完成的本轮任务。** S0–S10 均已完成。
- 下一轮是否继续深入跨站数据与控制路径，由用户在新实验对齐时决定，不属于 Exp1 的遗留执行项。
- 哪些通用知识需要沉淀进最新一卷 `docs/knowledge_{YYYYMMDD}.md`，仍由用户人工决定与维护。
- 合作方实际 digital twin 的实现细节仍需通过后续会议核验；这是未来方向收敛的外部输入，不作为 Exp1 未完成项。

## 当前状态

**Exp1 已于 2026-08-26 结题。** 首轮全景调研（S1–S5）、具体 scientific workflow 解剖（S6–S7）、intent / policy / SLA / Flow Engine 的概念拆解（S8）、外部生态与 UCR 接口定位（S9），以及 agent 通信顶会论文调研（S10）均已完成。用户后续消化、人工维护 knowledge，以及选择下一研究方向不阻塞本轮结题。本轮没有运行实验，没有 run，也没有可登记到 `EXPERIMENTS.md` / findings 的实验结论。

## 实验历史

- **Exp1（已结题，2026-07-28—2026-08-26）**:AI 驱动科学实验、autonomous experimentation、self-driving laboratory、digital twin、实验选择、设备控制、科学工作流、AI agent 与相关系统平台的背景调研；不运行实验。
