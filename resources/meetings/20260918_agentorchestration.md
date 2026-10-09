# 2026-09-18 SciNet 全体会议：agent orchestration、telemetry 与综合软件架构

> **日期**：按用户在 2026-09-19 所说的“昨天”记为 2026-09-18；`Agent Orchestration.pptx` 的最后修改时间也是 2026-09-18。转写本身没有日期或时间戳。
>
> **材料**：用户提供的会议自动转写、会议截图、[`resources/slides/Agent Orchestration.pptx`](../slides/Agent%20Orchestration.pptx)，以及用户随会议材料补充的 Site-RM、SENSE、Otter 与 NRP 链接。
>
> **参会者**：截图或转写中可确认的人员包括 Linxuan Zhong、Sourabha Bharadwaj Bangalore Murali、KK Ramakrishnan、Kiran、Harvey Newman、Raymond Matson、John Graham、Mariam；开场还提到 Punit 组的一位新成员。此名单可能不完整。
>
> **说话人可靠性**：自动转写没有逐段 speaker label。本文仅在称呼或上下文足够明确时写人名；其余用“与会者”。Harvey 的部分归属依据 Kiran 后面对 “Harvey 所说的 world model” 的回指，仍属于上下文判断。
>
> **整理口径**：不复述 Linxuan 已在 slides 中讲过的设计，只记录他人对此的评价、追问和补充；Sourabha 的 telemetry 汇报和 Kiran 的综合架构则按会议内容展开。外部系统的能力只记录会中说法或用户补充的资料，未经核实的接口、资源政策和 demo 计划不写成既定事实。

## 核心摘要

与会者对这版 agent orchestration 的总体反应是正面的：**方案从完整 workflow 和运行时变化出发，没有把问题预先简化成单次传输或单一 agent；bundle、quote / hold / commit、`repaired` / `runtime schedule failure` 也给出了可继续细化的闭环骨架。** Kiran 认为这与她准备介绍的总体软件架构相近，可以合并进去。

反馈的重点不是推翻两层 agent 设计，而是要求把它扩展成一个真正的 workflow 系统：scheduler 除了 network agent，还必须能够纳入 compute、instrument、storage 和 site 状态；digital twin 应承担某种 world model 角色；运行中要持续更新 task progress、time to completion 和随时间变化的剩余资源，而不是只在提交时生成一次静态计划。

Sourabha 提出的 telemetry agent / service 试图提供一个逻辑统一的数据入口：从 SENSE API、Site-RM / Prometheus、perfSONAR、自定义探测和 HTCondor 等来源取得网络、站点和计算状态，再供 scheduling agent 与 network agent 使用。John 补充，SENSE 可以随路径部署 Prometheus exporters / Grafana，Site-RM 也有站点资源接口；但多位与会者同时强调，外部系统通常不能直接接管站点的任务调度，只能请求、协商并获得进度与预计完成时间。

**本次没有定稿 telemetry 的接口、部署或优化算法，也没有做实测。** 特别是 Site-RM 能提供哪些公开 API、哪些指标由 SENSE 自动部署、如何把任务进度和网络状态关联到同一 workflow，仍需向 ESnet / SENSE 专家核实。

Kiran 随后给出一张更完整的软件架构：以 Pegasus workflow 为入口，经 workflow enrichment、task organizer、资源 agents 和 optimizer，把任务映射到 compute 与 network 资源；virtual infrastructure twin 充当 world model，flow engine 与外围 harness 负责运行这些组件。她认为 Linxuan / Sourabha 的接口和 telemetry layer 可以直接并入这套结构。

后半场最重要的现实问题是：**架构假定能够按需取得大量计算资源，但现有 DOE 设施常通过长期 allocation committee 分配资源。** 团队需要向 Ian Foster 和 American Science Cloud / IRI 团队核实其公开 API 背后是否已有真正可调用的 on-demand compute，还是只提供架构或状态查询。NRP 因为不要求传统 allocation，被认为适合作为早期原型环境；更大资源能否通过 Genesis 项目获得，仍是开放问题。

## 一、对 agent orchestration 汇报的评价与追问

### 1. 整体结构得到正面评价

Harvey（按上下文判断）认为，这套结构的优点是能对真实运行中的变化作出反应，而不是只做一次性规划。把同一 workflow 的多个 transfer 作为 bundle 处理，也让系统可以定义长期指标，评估在资源不可能全部满足时“实际能做到多好”。

他特别肯定了以 **workflow** 为决策单位的方向：scheduler 的目标不应只是让一条传输成功，而应在多个 workflow 之间仲裁，尽量增加在 deadline 前完成的 workflow 数量。限制因素可能来自网络，也可能来自站点、仪器、计算或存储；这些都应进入同一套规划逻辑。

Kiran 在本段汇报结束后说，这部分 “really good”，并认为它与自己准备展示的总体架构相似。她后续的 task organizer、resource agents、virtual infrastructure twin 和 harness 可以吸收这里的接口与 telemetry 设计。这个评价表示两套架构可合并，**不表示具体组件边界已经获全体确认**。

### 2. Scheduler 最终还要面对 compute 与 instrument 资源

一位与会者直接追问：当 scheduling agent 与 network agent 交互时，它是否也要与 compute agent 和 instrument agent 交互？

汇报方解释，目前 diagram 有意把重点收窄到 scheduler 与 network agent，计算与设备相关 agents 尚未画全。与会者接受可以先以网络为例推进，但提醒：**定义 workflow 的同时也必须说明当前明确不覆盖什么。** 当前图不能让人误以为网络是 workflow 唯一的动态资源。

讨论中形成的方向是：

- scheduling agent 仍是理解 DAG、deadline 和跨 workflow 关系的核心实体；
- network agent 处理网络容量、路径和 SENSE provisioning；
- compute / instrument 资源可以由其他 agent 或资源实体提供状态与候选方案；
- 这些新实体如何与 scheduler 协商，本次没有展开，也没有决定是否复制 network agent 的接口形式。

### 3. Digital twin 应进一步解释为 world model

Harvey提出，图中的 digital twin 也可以理解为 **world model**：大量决策依赖系统对当前整体状态的认识，例如同时存在多少 workflow、各自的属性和进度、站点及资源发生了什么变化。

这条反馈把 digital twin 的职责从“可替换 SENSE 的网络测试环境”扩展到了“支持全局决策的状态模型”。但会议只提出了这个需求，**没有决定 world model 是否等于 telemetry store、是否保存 workflow execution state、或由哪个 agent 维护。**

### 4. 运行时需要持续更新 progress 与 time to completion

与会者强调，资源分配之后必须有反馈循环。无论通过 polling 还是由工具主动上报，系统都需要区分正常进展与显著偏差，并根据进度更新计划。

会上反复提到两个时间相关量：

1. **各 task / transfer 的预计完成时间**。多个任务共享资源时，time to completion 应随执行进展持续更新。
2. **随时间变化的剩余资源**。可用带宽或其他容量不能被看成一个常数；scheduler 与 network agent 需要知道不同时间段还能分配多少。

Harvey把这与 proposal 中的“remaining work”联系起来：若要在运行中重排，系统不仅要知道已经发生什么，还要知道剩余工作量和新的预计完成时间。

### 5. 交互背后还需要明确的优化问题

一位与会者指出，当前展示清楚了组件之间如何请求和回应，但底层最终应有一个 optimization problem formulation，负责从多个候选 offer、workflow deadline 和资源冲突中作出可解释的选择；Raymond 可以在这部分提供帮助。

这是一项后续设计要求。会议没有选择目标函数、约束形式或求解器，也没有决定哪些选择由确定性优化完成、哪些由 agent / LLM 完成。

## 二、Sourabha 的 telemetry 方案

### 1. Telemetry agent 的定位

Sourabha 把 telemetry agent 描述成一个**逻辑统一的服务**。它不替代 SENSE、HTCondor 或站点已有的监控系统，而是从不同系统取得状态，再按 agent 所需的形式提供出来：

- network agent 使用网络拓扑、容量、service state、路径探测和故障信息；
- scheduling agent 使用 task events、compute slots、设备事件和文件事实；
- 两类 agent 可以订阅或查询同一个逻辑入口，而不必各自重新实现所有采集器。

slides 中进一步把这一过程写成 `collect → normalize → timestamp → store → expose`，并区分历史 time series 与带 TTL 的 current snapshot。会上主要讲的是来源和用途，**没有确认存储技术、schema、订阅协议或 freshness SLA。**

### 2. 规划状态与运行时观测来自不同接口

Sourabha 将网络数据大致分为两类：

| 类别 | 会中给出的来源与示例 | 用途 |
| --- | --- | --- |
| 控制面 / 规划状态 | SENSE API：topology、节点或端点能力、service / reservation state、intent status | 了解可以配置什么、已配置什么 |
| 运行时观测 | Site-RM 暴露的 Prometheus endpoints、perfSONAR，以及按需 ping、RTT、throughput 等自定义探测 | 判断当前路径是否按预期运行、定位退化或故障 |

这一区分很重要：SENSE 的 topology 或 reservation state 不能自动等同于实测吞吐、loss 或主机负载。Telemetry service 需要同时保留控制面状态与实测指标，并带上时间与来源。

### 3. 计算侧可以接入 HTCondor / 站点资源状态

Sourabha 还提出从 HTCondor API 获取 slot 信息，例如可用内存、CPU cores 和 slot 状态。这些数据主要供 scheduling agent 使用，network agent 不一定消费，但可通过同一 telemetry service 归一化。

John 补充，SENSE Site Resource Manager（Site-RM）也提供站点资源接口，可查询站点的 worker nodes 与计算资源；他指出目前相关能力很多基于 Kubernetes，因此若最终目标是 Condor 或 Slurm，还要明确 Site-RM 的资源视图与这些 scheduler 的关系。

用户补充的会外资料把 [Site-RM](https://github.com/sdn-sense/siterm) 定位为 SENSE 在设施 / 站点边缘的自动化组件，用来衔接跨域服务与本地资源。仓库首页指向 [SENSE documentation](https://sdn-sense.github.io/)。这一背景有助于理解 John 的建议，但**具体 API 与部署方式仍需按本项目环境核对，不能只凭会议转写认定。**

### 4. 站点不会把本地 scheduler 的控制权直接交出来

Harvey（按上下文判断）对“查询空闲 slots 后由本系统直接调度站点资源”的表达提出保留：现实中的实验或站点通常不会允许外部 agent 接管自己的 work queue 和本地资源调度。

更可行的交互是：

- 本系统向站点请求或协商资源；
- 站点自己的软件栈决定如何执行；
- 站点持续报告任务进度、完成比例与预计完成时间；
- SciNet 上层根据这些信息调整网络预约和 workflow 计划。

因此 compute agent 若存在，更可能扮演资源协商与状态适配层，而不是直接替代站点 scheduler。本次没有确定它的具体 authority。

### 5. Compute 的 best effort 与整节点预留是一个待评估的取舍

John 提出，计算侧至少存在两种运行方式：

- 使用更多共享资源做 best effort，可能获得更高平均吞吐，但会遇到中断或性能波动；
- 预留整台 physical node，资源与性能更可预测，但更难获得。

这一取舍会影响 scheduler 对 runtime、queue delay 和 network endpoint 性能的估计。会议没有选择其一，只把它作为 compute-resource agent 和实验设计需要显式考虑的变量。

### 6. SENSE / Site-RM 已有的 telemetry 能力需要向专家核实

John 根据已有了解补充：SENSE orchestrator 可以沿 provisioned path 配置 telemetry，可能通过选项启用，部分情况下默认启用；路径上可获得 Prometheus exporters 与 Grafana dashboards。Site-RM 也有 API 可提供站点资源信息。

他同时明确说自己只知道这些能力存在，详细 setup 应向相关专家询问。结合用户提供的 Otter action items，需要联系：

- Eustace Blakas；
- Tom Lehman；
- Mohammed Sada。

需要索取的不只是口头说明，还包括公开文档、API 入口、metrics 列表、部署配置和可供学生复现的示例。该行动由 Kiran、Mariam 负责。

## 三、运行时链路故障示例

Sourabha 用 slides 中的最后一个例子说明 telemetry 如何进入 network agent 的 fast loop。该例是拟议流程，不是已运行的 demo。

### 1. 正常建立服务

Scheduling agent 先提交 transfer requirement，network agent 通过 quote / hold / commit 流程选择资源并调用 SENSE 建立服务。Telemetry agent 在服务运行期间提供 circuit 或 path 的状态。

### 2. 发现吞吐或链路异常

若实测带宽低于承诺或预期，network agent 先请求 circuit-level telemetry；需要进一步定位时，再沿 end-to-end path 检查各 link 的状态和 loss 等指标。

这里的关键补充是：network agent 不只知道“传输变慢”，还应尽量缩小到具体路径或链路，并取得足以驱动修复的证据。本次没有定义阈值、采样频率或故障判定算法。

### 3. 尝试局部自修复

若定位到问题链路，network agent 可以在新的 SENSE request 中使用 exclusion list，要求重新 provision 一条避开该链路的路径。若新的路径仍能满足原 commitment，则由 network agent 完成修复，并向 scheduling agent 报告 `repaired`。

这对应 fast loop 的候选实现。会议没有验证所有 SENSE 环境都支持相同的 exclusion 行为，也没有测量 repair latency。

### 4. 修复失败则回到 workflow 层重排

如果 network agent 找不到仍能满足 deadline 的 offer，它应把 `runtime schedule failure` 或等价的 at-risk 事件交给 scheduling agent。后者再从 workflow 与跨 workflow 的角度决定是否移动窗口、重新排序、降级或通知用户。

这个流程得到与会者的认可，但仍缺少几个接口细节：failure event 应带哪些字段、scheduler 多久必须回应、重排后是否沿用同一套 quote / hold / commit 协议，以及更新后的 execution plan 如何同步回 WMS。

## 四、Kiran 的综合软件架构

### 1. 从 proposal 图走向可开始搭建的软件结构

Kiran 表示，她正在把 proposal 中的概念图转换成可以逐步实现的软件架构。她的图与 Linxuan / Sourabha 的设计具有明显对应关系：

| Kiran 图中的部分 | 会中描述的职责 | 与前半场方案的关系 |
| --- | --- | --- |
| Pegasus workflow input | 提供原始 workflow / DAG | 对应 WMS 与 workflow schema 的输入侧 |
| Workflow enrichment agent | 向 workflow 增加网络等资源参数 | 可接收 Linxuan 方案中的 transfer requirement 与 endpoint 信息 |
| Task organizer | 把大 DAG 拆成较小 tasks，识别 task dependencies | 对应 scheduling agent 的 decomposition，但边界尚未对齐 |
| Resource agents | 查询并请求 compute、network 等不同资源 | Network agent 可成为其中一个专门 agent；compute agent 尚未定义 |
| Optimizer | 处理资源分配和多个 workflows 的竞争 | 对应前半场的 cross-workflow arbitration 与待定义的优化问题 |
| Virtual infrastructure twin | 保存基础设施规格和状态，充当 world model | 对应 Harvey 对 digital twin 的扩展解释 |
| Flow engine | 承载上面各组件的运行与交互 | 前半场没有同名组件 |
| Harness | 包围并组织 agents、tools、模型与执行环境 | Kiran 认为这是总体实现必须补上的一层 |

Kiran 的目的不是另起一套架构，而是把现有工作合并进去。她明确指出 Linxuan / Sourabha 的 telemetry layer 在自己的图中缺失，应该加入综合架构和 harness。

### 2. American Science Cloud / IRI 作为 compute 侧候选接口

Kiran 根据 American Science Cloud 的公开材料，找到了一组经 IRI 发布的 API 和相关代码。她描述其中包含 GET / PUT 类接口，可查询 OLCF、ALCF 等设施当前有哪些计算资源，并称这些接口在上一年 7 月已经公开。

她建议团队实际测试这些 API，再把 compute resource information 与 SENSE 提供的 network resource information 合并。她设想 compute 与 network 各有相应 agents，task organizer 和 optimizer 再将 tasks 分配到这些资源。

这些说法在会上没有现场验证。尤其需要区分：

- API 是只提供目录与可用状态，还是能够真正申请资源；
- 返回的“available”是否表示普通用户可立即使用；
- agent 能否直接提交或分配 jobs，还是只能向设施已有系统提出请求；
- OLCF / ALCF 是否采用相同接口、权限和分配政策。

### 3. 未来可能是 agent-to-agent 的设施接口

Kiran 提到 American Science Cloud 本身也在设计管理平台的 agentic framework。由此产生一个候选集成方式：SciNet agents 不直接控制底层设施，而是与 American Science Cloud、IRI、SENSE 等平台自己的 agents 交互，由对方完成本地 allocation 或 provisioning。

她在图中加入了 SENSE agent，也提出需要了解 IRI / compute-facility agents 的通信方法。**这只是目标形态；会上没有拿到 agent API、身份认证、协议 schema 或可运行 endpoint。**

## 五、关键现实问题：计算资源能否真正按需获得

### 1. 架构假设与现有 allocation 制度可能冲突

在 Kiran 介绍 compute APIs 时，一位与会者提出全场最直接的可行性问题：架构看起来假定系统可以根据 workflow 当场取得大量资源，但现实中经常要通过年度或长期 allocation committee。如果一次请求需要几个月审批，动态 orchestration 就无法按图运行。

这不是对 API 形式的小问题，而是架构能否成立的前提：

- 查询到资源不代表能够立即使用资源；
- agent 能发起请求不代表设施会自动批准；
- 原型可用少量资源不代表规模化 workflow 能获得同样的 access；
- 技术演示中的 on-demand 与设施治理中的 allocation 需要分开描述。

与会者要求把这个问题拿到线下核实，避免在没有真实资源路径的情况下继续扩展架构。

### 2. Kiran 将向 Ian Foster 核实 Globus / American Science Cloud 的实际能力

Kiran 回应，她在 Ian Foster 的报告中看到 Globus 调用多个计算设施的资源，并据此分配 Globus jobs。她认为已有代码，不只是概念架构，并表示可以向 Ian Foster 进一步确认。

需要确认的重点是：

1. 这些实现是否已经在真实设施运行；
2. 资源是否可由 workflow 按需请求，而不经过长期 allocation；
3. 可用规模、权限、排队与配额限制是什么；
4. SciNet 是否能直接使用相同接口和代码。

Otter action items 将这项工作列给 Kiran、Mariam。本次会议没有得到最终答案。

### 3. NRP 可作为不依赖传统 allocation 的原型环境

John 指出 NRP 不要求相同形式的 allocation，可以让团队更容易开始 prototype。会议后段再次回到这一建议：先在 NRP 上证明系统能够运行，再用已有结果向更大的设施申请资源或完成 onboarding。

团队同时强调，NRP 适合早期原型不等于它解决了最终资源问题。Bridge 等更大平台是否能通过 Genesis 项目、director's discretionary allocation 或其他渠道提供“ready access”，仍需单独询问。

## 六、两套架构的合并与进一步评价

### 1. 前半场方案没有过早简化问题

在看到 Kiran 的整体架构后，一位与会者再次评价 Linxuan / Sourabha 的汇报：其逻辑是合适的，因为没有一开始就把问题简化到系统无法表达真实 workflow 的程度。

他把这与此前讨论过的 VI single-agent 方案作对比：单一 agent 的设计预设了系统只能处理较简单问题，从而把限制写进了整体结构。当前方案保留了更多“open handles”，允许后续接入 compute、instrument、telemetry、optimizer 和多个外部平台。

这里的肯定针对的是**问题分解方式与可扩展性**，不等于前半场展示的所有接口都已正确或完整。

### 2. 合并后的架构仍需继续细化

会议倾向把两张图合并，而不是选其中一张：

- Kiran 的图提供 flow engine、harness、外部 compute agents 和整体软件容器；
- Linxuan / Sourabha 的图提供 WMS、scheduling agent、network agent、SENSE 接口和 typed verbs；
- telemetry layer 补足 Kiran 图中原本缺少的运行状态入口；
- virtual infrastructure twin / world model 为 optimizer 和 agents 提供一致的环境状态。

但 task organizer 与 scheduling agent 是否重复、optimizer 属于 scheduling agent 内部还是独立组件、world model 与 telemetry state 如何分工，本次仍没有对齐。

### 3. 可以用 AI 审视架构，但不能把批评当设计结论

一位与会者提到，自己曾让某个 AI 工具查看 proposal 和架构图，工具指出了一些薄弱点与待决策处；转写中的工具名近似 “open claw”，无法可靠识别。他建议以后可以把这类 critique 作为补充反馈，帮助团队发现遗漏。

会议没有要求把 AI 输出直接写进设计，也没有决定具体工具或 review 流程。能确认的只是：外部 critique 可作为发现问题的输入，最终判断仍由项目组完成。

## 七、真实 science use case 与外部合作方式

### 1. 架构需要一个足够具体的 workflow 验证

会上谈到一个 AI-native research ecosystem workshop。与会者认为，许多领域参与者习惯从自己已有的 workflow 与局部需求出发，不熟悉 agentic architecture、harness 和跨资源闭环，因此仅靠抽象架构很难获得有效反馈。

团队需要带着一个真实但足够小的 use case 进入合作：

- workflow 的 tasks 与 dependencies 可明确表达；
- 至少包含 compute 与 network 两类资源；
- 能显示 telemetry 变化如何触发计划调整；
- 外部平台只需回答具体接口问题，而不是从头参与架构设计。

会上把 high-energy physics workflow 作为候选，并提出可以先做一个只有两项活动的简单场景。有人建议最快在下一周拿出初步 use case，然后再去询问设施 agents 如何对接。**这是推进建议，不是已承诺的交付日期。**

### 2. IRI / American Science Cloud 接入与 science use case 是两个问题

与会者提醒，接入 IRI 或 American Science Cloud 主要解决平台和资源接口；它本身不是 science use case。Use case 必须来自具体 workflow，说明科学活动为何需要这些 tasks、数据移动和 deadline。

因此可并行推进两条线：

- 用 American Science Cloud / IRI API 了解 compute-resource 接口；
- 用一个 HEP workflow 定义实际 tasks、数据依赖和预期运行行为。

只有两者汇合，才能验证 agent orchestration，而不是只展示 API 调用或架构图。

### 3. 与外部团队合作应从具体问题开始

会上对外部团队是否愿意投入存在不同判断。一种担心是，对方有自己的 milestones，只会提供被动接口，不会帮助 SciNet 共同设计。另一种意见认为，Genesis 项目具有正式身份和共同利益，只要提出具体、可回答的问题，相关人员很可能会转给正确专家并作出回应。

最终讨论更接近后一种推进方式：**先把自己的原型和问题做具体，再主动询问，不要预设对方会拒绝。** 这也解释了为什么需要收集公开链接、参加相关活动并直接联系 telemetry / compute 专家。

### 4. Chicago hackathon 是了解 American Science Cloud API 的候选机会

Kiran 提到几周后 Chicago 有一个 hackathon，将演示如何使用 American Science Cloud APIs。她建议团队考虑参加，以便实际接触接口和资源。

会议没有确认参会人员、预算或行程，因此当前只能记为候选机会。

## 八、从架构讨论转入共同实现

### 1. 共享 diagram、slides 与代码空间

Kiran 表示已把自己的 diagram 上传到团队 Google folder，并会通过 email 发给 Sourabha 和 Linxuan。她请两人把本次 slides 发给她，以便一并存放。

她还创建了一个 GitHub project，准备把团队成员加入为 users，随后开始建立目录并放入代码。这里的目标是把分散的 agent、API client 和 harness 逐步变成共同工程；本次没有确定 repository URL、目录结构或代码所有权。

### 2. SENSE code 与 API 链接需要集中保存

John、Harvey 等人在 chat 中分享了 SENSE code 与 API 相关链接。会议专门讨论了如何保存这些信息，避免链接随 chat 丢失。建议在共享位置集中登记，使不同机构的学生可以分工阅读、试用并积累共同知识。

### 3. 综合实现的近期形态

从全场讨论可还原出一个尚未定稿的近期实现路径：

```text
一个简化的 science workflow
        ↓
workflow enrichment / task decomposition
        ↓
scheduling / optimization across tasks and workflows
        ↓
compute-resource interface + network agent / SENSE
        ↓
telemetry feedback into world model / runtime state
        ↓
局部修复或 workflow-level rescheduling
```

这只是把会上分散意见串起来的整理，不是会议批准的正式 milestone。尤其 compute API、world model 和 telemetry correlation 仍未定稿。

## 九、SC26、NRP 与行政更新

### 1. SC26 demo 尚处在探索阶段

会议后段有人询问是否需要外部 LLM 服务，以及是否已有 SC26 demonstration 计划。团队回应正在考虑能否在 SC 做一些展示，但没有提交记录、确定场地或明确 demo 内容。

讨论提到 SC 场地可能有 NRP nodes，Harvey 的 booth 也可能提供 NRP 资源（转写将 booth 识别成 `book`，此处按上下文还原）。这些都属于可能的基础设施条件，不代表 demo 已获接受。

### 2. NRP hosted LLM 可供开发使用

John 在 chat 中分享了 [NRP hosted LLMs](https://nrp.ai/llms/) 的入口，并称团队可以免费使用。会上将它视为外部 LLM 服务的一个可立即尝试的来源。

这解决的是模型调用与小规模 agent prototype 的入口，不代表任何模型已经被选定，也不回答 LLM 应放在架构中的哪个决策边界。

### 3. 资源策略：先在 NRP 证明，再申请更大规模

会议建议先利用 NRP 做出可运行结果，证明系统能够完成 workflow orchestration；之后再询问 Bridge 或其他大规模设施能否通过 Genesis 项目取得更大资源。这样可以把资源申请从抽象需求变成有原型和测量依据的请求。

### 4. 合同与经费进展

会议简短更新了合同状态：KK 相关合同已完成，预计很快收到资金；Caltech 是下一项，之后还提到 HPE。有人正在审阅协议中的若干条款，若有变更需与 Miriam 协调；Miriam 被称为该 agreement 的 overseeing officer。

这部分转写较破碎，只能确认大致进展，不能据此判断具体生效日期、金额或条款。

### 5. 下次会议

开场曾讨论 Tuesday 与 Friday 哪个时段更合适，但没有形成清晰的新长期时间。散会前确认：**下一次仍在 Tuesday、same time。** 转写对具体小时识别不一致，因此本文不记录精确时间。

## 十、全会形成的方向与边界

### 得到支持的方向

- 保留 scheduling agent 与 network agent 的分层；前者做 workflow / cross-workflow 决策，后者面向网络资源和 SENSE。
- 将 Linxuan / Sourabha 的接口设计与 Kiran 的 flow engine / harness 架构合并，而不是继续维护两套平行图。
- 把 telemetry layer 加入综合架构，让 compute、network 和 instrument 状态能进入运行时决策。
- 运行时持续跟踪 progress、time to completion、remaining work 和随时间变化的剩余容量。
- Network agent 先尝试局部修复；无法维持 commitment 时再升级到 scheduling agent 做 workflow-level rescheduling。
- 用一个小而真实的 science workflow 驱动接口验证，并把 NRP 作为早期 prototype 环境。
- 与外部平台交互时提出具体接口问题，而不是等待对方替项目定义架构。

### 本次没有决定的事项

- Telemetry service、world model 与 workflow execution state 是一个实体还是不同层次。
- 谁负责把 raw metrics 关联到具体 workflow、task、transfer 和 commitment。
- Task organizer、optimizer 与 scheduling agent 的职责是否重叠。
- Compute agent 可以查询、请求和控制到什么程度，哪些动作必须留给站点 scheduler。
- American Science Cloud / IRI API 是否真正提供免长期 allocation 的 on-demand compute。
- Site-RM、SENSE telemetry、Prometheus、perfSONAR 和 HTCondor 的确切接口、部署前提与刷新频率。
- Optimization problem 的目标函数、约束、求解器及与 LLM 的边界。
- 故障事件和 scheduler 回应的 typed schema，以及重排后的 WMS 同步流程。
- SC26 demo 的内容、场地、提交方式与资源需求。

## 十一、行动项

| 行动 | 负责人 | 状态 / 目的 |
| --- | --- | --- |
| 联系 Eustace Blakas、Tom Lehman、Mohammed Sada，索取 SENSE telemetry setup 的说明与公开入口 | Kiran、Mariam | 待办；核实 John 会中提到的能力 |
| 分享 American Science Cloud / IRI compute-resource API 列表及相关代码 | Kiran、Mariam | 待办；供团队测试与集成 |
| 向 Ian Foster 核实 Globus / American Science Cloud 是否已能按需请求 compute，而不经过长期 allocation committee | Kiran、Mariam | 待办；这是综合架构成立的关键前提 |
| 把 telemetry layer 加进综合 software architecture 与 harness design | Kiran、Mariam | 待办；吸收 Linxuan / Sourabha 的方案 |
| 把本次 `Agent Orchestration` slides 发给 Kiran，并放入共享 Google folder | Linxuan、Sourabha | 待办 |
| 将 Kiran 的 diagram 发给 Linxuan、Sourabha，并放入共享目录 | Kiran | 已称完成上传，email 待发 |
| 把团队成员加入新 GitHub project，开始建立目录和代码 | Kiran | 已创建 project；成员与结构待补 |
| 集中保存会上分享的 SENSE code、API 与 telemetry 链接 | 团队 | 待办；避免 chat 链接丢失 |
| 把多 workflow 选择明确成 optimization formulation | 待定；Raymond 可协助 | 尚未定义问题与接口 |
| 选择一个小型 HEP workflow，形成可向外部平台提出具体问题的 use case | 团队 | 建议项；尚未正式分工或承诺日期 |
| 评估参加 Chicago American Science Cloud API hackathon | 团队 / Kiran | 候选项；尚未确认 |
| 探索 SC26 demo，并确认可用的 NRP nodes、场地与提交方式 | 团队 | 候选项；尚未形成计划 |
| 先在 NRP 上完成 prototype，再询问 Bridge 等设施的更大规模 access | 团队 | 建议的资源推进顺序 |

## 十二、会议材料与链接

- 本次汇报 slides：[`Agent Orchestration.pptx`](../slides/Agent%20Orchestration.pptx)
- Site-RM source：[sdn-sense/siterm](https://github.com/sdn-sense/siterm)
- SENSE documentation：[sdn-sense.github.io](https://sdn-sense.github.io/)
- Site-RM / SENSE 背景材料：[CERN presentation](https://indico.cern.ch/event/1185600/contributions/5109192/attachments/2545788/4383989/Automated%20Network%20Services%20for%20Exascale%20Data%20Movement%20%281%29.pdf)、[EPJ Web of Conferences paper](https://www.epj-conferences.org/articles/epjconf/pdf/2024/05/epjconf_chep2024_01009.pdf)、[NSF PAR copy](https://par.nsf.gov/servlets/purl/10548846)
- ESnet：[es.net](https://www.es.net/)
- Otter full summary：[meeting summary](https://otter.ai/u/OauZBdiGG5a6BtZsZ6q5Y4HsxE4?utm_source=va_chat&utm_content=wrapup_v4&tab=chat&message=e64b5610-1e5d-4320-8bff-91322b36340b)
- John 在 chat 中分享的 NRP hosted LLM 服务：[nrp.ai/llms](https://nrp.ai/llms/)
