# 2026-09-20 Cross-site orchestration：全局 agents 与 Site Agent 的职责划分

> **来源**：2026-09-20 对话，以及 Linxuan 当晚对 WMS、network agent、scheduling agent 和多站点架构的思考。
>
> **状态**：本文记录的是**当前个人判断和待讨论的架构假设**，不是项目已经确认的设计。尤其是 WMS、SENSE 和各站点 scheduler 的实际能力仍需通过文档、代码或合作方确认。

## 一、问题起点：为什么 WMS 之外还需要 agents？

当前判断是，传统 WMS 主要在已经给定的计算与网络环境中执行 workflow。它可以依据 DAG 启动 tasks、调用数据传输工具并跟踪执行，但未必能够主动处理下面这种未来资源规划：

> 已知两小时后需要从 Site A 向 Site B 传输数据，系统提前选择一条可行 circuit path、预约 bandwidth 和 time window，并在运行时根据网络变化自动调整。

今天这类网络资源配置往往还需要 operator 参与，例如由人通过 SENSE 申请路径，类似在 CloudLab 中由人预留 physical nodes。SciNet 希望构建的是自动科学实验闭环，因此目标是让系统自动完成资源请求、协商、执行和反馈，不依赖人在每次 workflow 中手动配置。

这部分目前应表述为一个**待验证的能力缺口**，不能直接断言所有 WMS 都做不到。后续需要分别核对 Pegasus、具体传输工具和 SENSE 的现有接口。

## 二、为什么同时需要全局 scheduling agent 和 network agent？

一个 network agent 不足以完成整个 workflow 的调度，因为它理解网络，却不理解完整 workflow。

### Global network agent

它接收的是网络需求，例如：

- source 与 destination；
- 数据量；
- earliest start 与 latest finish；
- bandwidth、可靠性或优先级要求。

它负责：

- 查询网络容量和候选路径；
- 与 SENSE 交互，执行 quote、hold、commit、modify 和 release；
- 监控网络状态与实际传输；
- 局部修复网络问题，无法修复时报告 `at_risk` 或 failure。

但它不知道 file dependency、task dependency，以及不同 workflows 之间应如何取舍。因此它只能回答“网络能够提供什么”，不能独立决定“整个 workflow 应怎样运行”。

### Global scheduling agent

它理解：

- workflow DAG；
- task 与 file dependencies；
- compute、instrument 和 transfer 的先后关系；
- deadline、priority 与 slack；
- 多个 workflows 之间的竞争。

它将 workflow 需求转换成 transfer windows，向 network agent 请求 offers，再结合 compute 和 instrument 条件选择全局方案。

两者的关系可以概括为：

> Scheduling agent 提出需求并做 workflow-level 取舍；network agent 面向 SENSE，把网络需求变成可执行的资源承诺。



## 三、为什么 cross-site 会成为独立问题？

不同站点通常是异构且自治的。每个站点可能有独有的：

- compute nodes、accelerators 和 local scheduler；
- scientific instruments；
- storage、DTN 和数据访问方式；
- queue、load、allocation 和使用政策；
- campus network、Site-RM 与安全边界；
- 故障状态和维护窗口。

两个全局 agents 不应直接了解并控制每台本地机器、每件仪器和所有站点内部策略。这样不仅实现复杂，也可能越过站点权限边界。

因此，多站点架构至少需要一种站点侧组件，把本地异构性封装成统一接口，并保留本地自治权。

## 四、当前个人倾向：全局功能 agents + 每站点一个 Site Agent

Linxuan 当前更倾向于：

- scheduling agent 和 network agent 保持全局；
- compute agent 和 instrument agent 也可以是全局资源协调角色；
- 每个站点部署一个 Site Agent；
- Site Agent 负责本站内部的适配、协商、执行与状态汇报。

```text
                         Workflow / WMS
                               │
                    Global Scheduling Agent
                      │        │         │
                      │        │         └── Global Instrument Agent
                      │        └──────────── Global Compute Agent
                      └───────────────────── Global Network Agent ── SENSE
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
             Site Agent A     Site Agent B     Site Agent C
                 │                │                │
          local scheduler   local scheduler   local scheduler
          instruments       instruments       instruments
          storage / DTN     storage / DTN     storage / DTN
          local network     local network     local network
```

图中表示逻辑职责，不代表所有 global agents 必须是独立进程，也不表示所有命令都绕过 WMS 或站点原有控制系统。

## 五、Site Agent 具体做什么？

Site Agent 是全局框架与一个站点之间的**本地代理、策略边界和适配层**。

### 1. 汇报本站能力

向全局 compute / instrument / scheduling / network agents 提供经过抽象的能力信息，例如：

- 可以使用的计算类型和规模；
- 仪器能力与可用时间；
- storage、DTN、network endpoints；
- local scheduler 类型；
- allocation、认证和使用限制。

全局层不需要看到每台机器的全部内部细节，只需要足以做跨站决策的信息。

### 2. 监控并上报本站状态

Site Agent 汇总本地系统的实时或近实时状态，例如：

- queue length、load 和预计等待时间；
- task ready、started、finished、failed 等事件；
- instrument 状态和数据产出时间；
- storage / DTN 状态与文件位置；
- local network、endpoint 和设备故障；
- 预计完成时间及对既有承诺的偏差。

任何会影响跨站 transfer window 或 workflow deadline 的变化，都需要上报全局层。

### 3. 翻译统一请求

把全局层的统一资源请求翻译成本地接口，例如：

- Slurm、HTCondor 或 Kubernetes；
- instrument control system；
- storage / DTN 工具；
- SENSE Site-RM 或 campus network controller。

因此，global agents 不必针对每个站点重新实现一套 API client。

### 4. 执行本地 admission 与协商

Site Agent 不应机械接受全局命令。它需要根据本地权限、policy 和真实状态：

- 接受请求；
- 拒绝请求并说明原因；
- 给出 counter-offer，例如更晚的开始时间或更小的资源规模；
- 将已接受的请求提交给本站原有 scheduler 或 controller。

这正是“站点保留本地控制权”的含义。全局层负责协调，最终本地资源仍由站点已有系统管理。

### 5. 做有限的本地恢复

Site Agent 可以处理不影响全局计划的小问题，例如：

- 在等价 local nodes 之间重新选择；
- 重新提交失败的 local task；
- 切换本站 DTN；
- 更新本地绑定，但仍满足原来的时间承诺。

如果本地恢复会改变数据 ready time、跨站 transfer window 或 workflow deadline，则必须报告 global scheduling agent，由全局层重新规划。

## 六、Site Agent 不负责什么？

在当前假设下，Site Agent 不负责：

- 优化所有站点上的完整 workflow；
- 在多个 workflows 之间进行全局优先级仲裁；
- 独自选择跨域端到端网络路径；
- 取代 Slurm、HTCondor、Kubernetes 或 instrument controller；
- 越过站点 policy 直接分配本地资源。

换句话说，Site Agent 负责**本站内部如何兑现承诺**；global agents 负责**各站点的承诺如何组成一个完整 workflow 计划**。

## 七、一次 cross-site workflow 的交互示例

假设一个 workflow 要在 Site A 的仪器产生数据，在 Site A 预处理，再传到 Site B 计算。

### 规划阶段

1. WMS 将 DAG 与 deadline 交给 global scheduling agent。
2. Global instrument / compute agents 通过 Site Agents 查询可用时间、queue 和候选资源。
3. Site Agent A 回答仪器和预处理任务最早何时完成；Site Agent B 回答远端计算何时可开始。
4. Global scheduling agent 根据这些候选结果生成跨站传输需求。
5. Global network agent 向 SENSE 查询并预约 Site A 到 Site B 的路径与时间窗口。
6. Global scheduling agent 选择能够满足整体 deadline 的组合，并将计划交回 WMS 与相关 Site Agents。
7. 各 Site Agent 通过本站 scheduler / controller 落地本地任务；network agent commit 跨站网络资源。



### 运行阶段

1. Site Agent A 发现预处理延迟 15 分钟，上报新的 data-ready time。
2. Global scheduling agent 判断原 transfer window 是否仍可用。
3. 若只需移动网络预约，则向 global network agent 发出新的 requirement。
4. Network agent 通过 SENSE modify，或重新 quote、hold、commit。
5. Site Agent B 根据更新后的 arrival time 调整本地 compute request。
6. 若 deadline 无法满足，global scheduling agent 在多个 workflows 之间重新仲裁或通知用户。

这个例子体现了边界：Site Agent 了解本地事实，全局 agents 理解跨站依赖和全局影响。

## 八、与 KK 提议的分歧

KK 提出的候选方向是：

> 每个 site 可能各有一个 scheduling agent 和 network agent，同时再通过协议或中央 controller 做全局 scheduling 与 network coordination。

这与当前个人倾向的区别如下：


| 方案                                                | 优点                                                | 风险 / 需要回答的问题                                                        |
| ------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------- |
| 每站点都有 scheduling + network agents                 | 本地决策快；每个 agent 可深入理解本站资源；局部故障可以自治处理               | 重复实现较多；需要复杂的 agent-to-agent 协议；多个本地 scheduler 如何形成全局最优不清楚；状态和承诺可能冲突 |
| 全局 scheduling / network agents + 每站点一个 Site Agent | 全局 workflow 与网络资源只有一个协调视图；协议和优化问题较集中；站点异构性由统一边界封装 | 全局组件可能成为瓶颈或单点；状态可能过期；Site Agent 职责可能过宽；需要明确哪些局部决策可自治                |


目前不能仅凭直觉否定 KK 的方案。需要先澄清他所说的 “individual scheduling/network agent” 是：

1. 具有独立目标和决策权的完整 agent；还是
2. 部署在 Site Agent 内部、分别适配 local scheduler 与 local network 的轻量模块。

如果是第二种理解，两种方案可能主要是**组件命名和封装层次不同**，并没有根本冲突。

## 九、一个可能的折中：Site Agent 内部保留两个适配模块

可以采用 hybrid 结构：

```text
Global Scheduling Agent        Global Network Agent
           │                           │
           └──────── Site Agent ───────┘
                         │
              ┌──────────┴──────────┐
              │                     │
     scheduling adapter      network adapter
              │                     │
      Slurm / HTCondor        Site-RM / DTN /
      instrument queues       campus network
```

这里：

- 全局 agents 保留跨站 workflow 和 network optimization；
- Site Agent 是本站统一身份、policy 和 telemetry 出口；
- scheduling adapter 与 network adapter 负责各自领域的本地协议；
- adapter 可以执行局部规则，但不成为另一套独立的全局 optimizer。

这既避免让两个全局 agents 直接管理全部本地细节，也避免每个站点复制两套完整智能 agent。

## 十、仍需进一步决定的问题



### 1. Command 还是 request？

原始思考中写到 Site Agent “receive commands from Network Agent and Scheduling Agent”。更准确的接口可能是 **request / negotiate / commit**：global agent 提出需求，Site Agent 根据本地 policy 接受、拒绝或 counter-offer，而不是无条件执行命令。

### 2. Site Agent 有多少本地决策权？

需要定义哪些变化可以自行处理，哪些必须升级。例如更换等价节点或 DTN 可以本地修复；改变完成时间、资源规模或跨站端点则可能需要全局重排。

### 3. Network agent 与 Site Agent 如何共同使用 SENSE？

一种可能是 global network agent 直接面向 SENSE orchestrator，Site Agent 只提供本站 endpoints、策略和最后一段网络状态；另一种可能是 Site Agent 通过 Site-RM 承担更多本地 provisioning。需要根据 SENSE 的真实控制边界决定。

### 4. Global compute / instrument agents 是否真的需要独立存在？

它们可能是独立资源 agents，也可能只是 global scheduling agent 内的 capability services。需要看它们是否具有独立状态、协议和决策职责，避免为了对称而增加 agents。

### 5. 全局协调采用中央 controller 还是分布式协议？

逻辑上可以先做 centralized coordinator 作为 Phase 1 proof of concept；将来若存在扩展性、自治或故障隔离要求，再研究多个 global / regional coordinators 之间的协议。

### 6. 状态的新鲜度与故障边界

全局决策依赖 Site Agent 汇报的状态，需要明确 timestamp、TTL、subscription 和失联处理。如果某 Site Agent 不可达，全局层应把本站状态视为 unknown，而不能继续依赖旧快照。

### 7. WMS 的真实能力边界

需要验证 WMS 是否确实只能在给定 endpoints / links 上执行，以及它是否已有资源预约、站点选择或网络服务调用能力。Network agent 的必要性应建立在已确认的能力差距上。

## 十一、当前结论

当前个人意见是：

> Scheduling、network、compute 和 instrument 的跨站协调保留在全局层；每个站点部署一个 Site Agent，封装本地 scheduler、仪器、存储、DTN、网络、policy 和 telemetry。Site Agent 提供状态与候选能力，接受并协商全局请求，再通过本站原有系统执行。

这个方案的核心不是“中央系统控制所有站点”，而是：

> **全局层负责跨站协调，Site Agent 负责本地自治和执行。**

但 KK 提出的 per-site scheduling / network agents 仍需进一步理解。下一步最值得澄清的不是 agent 数量，而是每一层的 **authority、state、decision 和 protocol**。只有这些边界明确后，才能判断它们应当是完整 agents、Site Agent 内部 adapters，还是中央服务的分布式实例。

> **文字歧义说明**：原始消息中 “network agent talks to SENSE with human-engagement” 与前后“完全自动、无人参与”的目标矛盾。本文按上下文理解为：network agent 自动执行原本需要 operator 参与的 SENSE 交互，即目标是 **without human engagement**。

