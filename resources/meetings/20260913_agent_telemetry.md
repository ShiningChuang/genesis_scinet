# 2026-09-13 SciNet 组内讨论：agent / WMS 执行边界与跨计算、网络、实验设备的遥测关联

> **日期**：根据用户在 2026-09-14 所说的“昨天”记为 2026-09-13；转写本身没有日期或时间戳。
>
> **材料**：用户提供的两段会议录音自动转写，以及随后补充的讨论用 slide 截图；未提供原始音频，转写无可靠的说话人标注。
> - **A：与 KK、Sourabha 的会议**。开头为 `Hipervisor, Alan, how are you doing?`，附件标识 `cd756b0d-37be-4fc4-884b-9a5ea192816e/pasted-text.txt`。本文的主要依据。
> - **B：会后与 Sourabha 的单独讨论**。开头为 `Trying to say think I think the whole point...`，附件标识 `8cc6a196-9f23-4a75-a20b-6e1c1a809bcb/pasted-text.txt`。只作为双方当时的理解与候选思路，不能代替 KK 的意见或已确认的设计。
> - **C：Overview 流程图（页码 2）**。用户补充确认，这是与 KK 全程讨论的流程图。下文按截图记录原设计的组件、箭头和三种循环；**图上内容是被讨论的方案，不代表 KK 已认可的结论**。
>
> **参会者**：A 为 KK、Linxuan Zhong、Sourabha；B 为 Linxuan Zhong、Sourabha（依据用户说明及既有会议记录）。发言归属主要由上下文判断；无法可靠区分两位学生的发言时记作“汇报方”或“双方讨论”。
>
> **整理口径**：下文区分“原 slide 的设计”“KK 明确提出的要求”“会上解释但仍未对齐的设计”“会后推测”。外部工具能力仅记录会中说法，未据此核实 Pegasus、SENSE 或 Prometheus 的实际接口。常见误识别按上下文还原为 workflow、WMS、scheduling agent、network agent、telemetry、SENSE、NDT；不据开场误识别人名推断额外参会者。

## 核心摘要

**KK 要求把完整 workflow 的执行和反馈闭环解释清楚：调度必须同时考虑计算、传输和实验设备之间的依赖；运行时的遥测需要在一个了解这些依赖的共同实体中关联，再支撑 agent 的协商与计划更新。** 原图已画出 agent 间的协商、故障反馈和 report 箭头，也明确写了 WMS 与网络侧两类信息来源；但谁负责把两者对应到同一 workflow 的实际执行、据此推导相互影响，仍未解释清楚。这是结合 slide 对 KK 质疑的更准确定位，不能理解成“原图完全没有反馈或信息交流”。

会议也澄清了两点：一是 scheduling agent 不能只把 DAG 转成 transfer windows，还要先考虑 compute 和完整 task 的时间安排；二是如果将 agent 定位为向 WMS 提供计划的 advisor，就必须解释清楚 WMS、agent、SENSE / NDT API 和实际执行之间的边界。

**本次没有定稿架构。** KK 倾向让遥测先汇入 WMS 或专门的 telemetry entity，再按 workflow 上下文分发；但谁调用哪些 API、统一实体放在哪里、现有 WMS 能否提供这些能力，仍需继续讨论。会后双方提出独立 telemetry service 的候选方案，也仍有未解决的问题。

## 零、讨论所依据的 Overview 原图（用户会后补充）

### 1. 组件与原图中的职责文字

| 组件 | Slide 中的标注 | 作为会议背景应如何理解 |
| --- | --- | --- |
| Data model（side-hung） | `WfFormat · WfCampaign`；`WfPlatform = static snapshot, seeds the ledger` | 数据模型侧挂在 WMS 上方；WfPlatform 被设定为初始化 ledger 的静态快照，不能据此认为它已提供实时遥测 |
| Scientists / operators | `natural language`；`explain, negotiate, normalize input` | 与 scheduling agent 双向交互，解释、协商并规范化输入 |
| Workflow management system（WMS） | `DAG, task deadlines` | 接收 execution plan，并提供 workflow 输入和执行 report；框内没有写清执行工具或物理组件接口 |
| Scheduling agent | `DAG → transfer windows`；`slack · cross-workflow arbitration` | 强调传输窗口与跨 workflow 仲裁，正是 KK 追问 compute 调度在哪里的上下文 |
| Network agent | `capacity ledger · quote engine`；`① self-repair ≤ 30 s` | 原设计包含容量状态、报价与主动修复职责，不是仅转发请求的无状态组件 |
| SENSE-O/NDT | `interchangeable` | 图中将二者作为可替换的下层对象，但没有明确区分 API、控制系统与实际执行环境 |

### 2. 原图确实画出的交互

| 方向 | 图上的标签 / 颜色 |
| --- | --- |
| WMS → scheduling agent | 蓝色 `submit / refine` |
| Scheduling agent → WMS | 灰色 `execution plan` |
| Scientists / operators ↔ scheduling agent | 蓝色双向箭头，旁注自然语言交互 |
| Scheduling agent ↔ network agent | 蓝色双向箭头，上方合并标注 `quote / hold / commit / response` |
| Network agent → SENSE-O/NDT | 蓝色 `ServiceIntent` |
| Network agent → scheduling agent | 橙色 `① repaired` 与黄色 `② at_risk` 两条反馈 |
| WMS → scheduling agent | 绿色 `③ report` |
| Scheduling agent → network agent | 绿色 `③ report` |
| SENSE-O/NDT → network agent | 绿色 `③ report` |

图中**没有画出 WMS 到实际执行环境的连接**，也没有单独的 compute / 实验设备或统一 telemetry 组件。结合 A 段可理解 KK 为什么持续追问“WMS 到底与谁交互”。这属于图示表达上的缺口，不足以证明口头方案完全没有考虑实际执行。

图下注明：自然语言仅用于人与系统的边界，两个 agents 之间使用 **typed quote protocol**。因此不能把本图理解成两个 agents 靠自由自然语言对话来交换所有信息；具体协议字段没有在这张 Overview 中展开。

### 3. 三种循环及其边界

| 循环 | Slide 原设计 | 不能据此认定的内容 |
| --- | --- | --- |
| ① Fast loop，≤ 30 s | network agent 内检测偏差、修复路径；向 scheduler 回报 `repaired` | 这是设计目标，不是实测恢复性能；图中没有展开修复对 task deadline、compute 或其他 workflow 的影响判断 |
| ② Slow loop，minutes | `at_risk` 向上推送，由 scheduler 重新进行跨 workflow 仲裁 | 没有定义何时从自修复升级为 at_risk，也没有说明计算侧变化如何触发该循环 |
| ③ Long loop，across runs | 两类来源：WMS 报告实际运行情况，network agent 从 SENSE-O/Twin 拉取 link state；两者用于下一次计划 | 两种来源与 report 箭头已经存在，但没有明确关联观测的责任实体、关联方法和数据契约 |

这里的 ≤ 30 s、minutes、across runs 是原 slide 的时间尺度设定，**不是三种遥测的采样周期，也不是 KK 在本次会议中逐项批准的指标**。

### 4. 补图后对会议含义的修正

**原方案已经区分运行中的恢复 / 仲裁与跨运行学习。** 因此会后关于“correlation 是否只服务未来 workflow”的困惑，要放在这个三循环框架下理解：KK 既谈到了未来估计，也用当前链路故障说明依赖如何影响正在执行的安排。

**原方案已有双来源 report 和 agent 间通信。** KK 的问题仍然成立于更具体的一层：这些箭头如何保证网络事件与对应 task、计算阶段及实验设备活动被共同理解？不能仅凭“有 report 箭头”断言问题已经解决，也不能将他的质疑整理成“完全没有设计反馈”。

**原图给 network agent 的职责比“advisor”一词更具体。** 它会发出 ServiceIntent、维护 capacity ledger，并执行 self-repair。结合 A 段，待澄清的是这些资源控制动作与 WMS 的执行命令如何分工；不能未经讨论就把图改述为所有底层交互都必须经 WMS。以上三点是对 A、B、C 的交叉整理，不是新增的会议决定。

## 一、与 KK 的会议：主要讨论

### 1. 先解释 WMS 相对于 workflow schema 和 scheduling agent 的职责

KK 一开始追问：workflow 文件已经定义 tasks、DAG、依赖和期限，scheduler 又负责排任务，那么额外的 workflow management system（WMS）究竟做什么？仅说“它运行真实 workflow”还不够具体。

汇报方以 Pegasus 为例解释当前设想：

- workflow schema 描述要做什么以及任务间关系；
- scheduling agent 与 network agent 生成计划、协商资源和约束；
- WMS 根据计划调用执行与文件传输工具，管理实际运行，并回报执行历史和观测数据。

KK 据此把当前设想理解为：**agents 提供执行建议，WMS 是发出实际执行命令、连接底层组件的执行与监控层。** 他同时说明，这与自己此前的理解不同：他原来设想 scheduler 接收 workflow 后，与 network agent 协作，由 network agent 接口到底层网络。

Sourabha 用 control plane / data plane 作类比时，KK 又作了细化：**WMS 也在发控制命令，不是亲自搬运数据；真正的数据移动发生在端系统、传输工具和网络之间。** 因此不能简单把 WMS 画成 data plane 就认为边界解释清楚了。

### 2. 图中的 SENSE / NDT API 与实际网络需要分开说明

这部分讨论有多轮澄清，不能把其中某一轮理解直接当成最终决定。补充的 slide 显示，右侧框实际写的是 `SENSE-O/NDT — interchangeable`，中间箭头写的是 `ServiceIntent`；框上没有直接写“API”。因此下表中的 API 解释来自汇报方口头澄清，正是原图与口头表达需要对齐的部分。

| 讨论阶段 | 当时的解释或要求 | 保留下来的问题 |
| --- | --- | --- |
| KK 按 advisory role 理解当前方案 | 建议把 agents 放在 WMS 上方，由 WMS 对接实际网络或 NDT；NDT 在这里替代真实网络作为执行环境 | 图中的箭头应与口头解释一致 |
| 汇报方进一步解释原图 | 图里的 SENSE / NDT API 表示网络配置、资源请求接口；network agent 与该 API 交互，WMS 使用返回的端点和时间窗口发起实际传输 | 资源配置与传输执行是两类交互，WMS 未必直接调用该 API |
| KK 在这一轮复述后继续讨论细节 | 理解到原图设想 WMS 不直接调用该 API，而由 network agent 负责 | 局部理解不等于整个架构已获认可 |
| 后半段讨论遥测时 | KK 再次质疑：既然 agents 被描述为 advisor，为何又各自直接接触物理环境获取遥测？ | 执行、资源请求和遥测三类交互仍需统一解释 |

因此，会议能支持的是“**必须明确接口与执行对象、修正图文之间的不一致**”，不能概括为“已决定 WMS 调用所有 SENSE API”，也不能概括为“KK 已认可 network agent 独立处理所有底层交互”。

### 3. Scheduling agent 必须覆盖计算与传输，而不只是 transfer windows

在介绍把 DAG 转成 transfer list / transfer windows 时，KK 反复追问为什么只谈 transfer window。一个 workflow 的 tasks 有先后关系，执行中既有 compute，也有 data transfer；scheduler 必须把这些部分都纳入时间安排。

汇报方解释，给 network agent 的信息确实只需要是 transfer windows。KK 接受这个接口层面的说法，但强调：**scheduler 在生成 transfer window 之前，必须先考虑 compute 的调度和完成时间。** 例如上游计算产生数据后，才能启动对应传输；传输起点不能脱离上游实际执行来决定。

会上也确认 scheduler 要做跨 workflow 的仲裁，并讨论了根据 earliest start、deadline 和 slack 推导传输窗口。

这里的澄清是职责范围，不是要求立刻修改 schema，把 compute 和 transfer 强制塞进同一种 task 表示。具体数据模型和计算站点选择机制尚未在本次会上定稿。

### 4. 科学家要求与 workflow 定义共同产生实际执行期限

KK 追问 task deadlines 从哪里来，以及 scientists / operators 与谁交互。讨论中区分了两类输入：

- **Workflow 定义**：任务依赖，以及相对于某个执行起点的时间约束等；
- **科学家 / 操作者要求**：实验实际何时开始、何时需要结果，以及对期限的调整。

KK 强调，总要有一个地方把相对时间转换为实际时钟时间。Scheduling agent 应结合 workflow 定义和用户要求，协商得到实际 execution plan，而不是只从 schema 中读取相对 deadline 就认为完成了调度。

汇报方描述科学家可以通过 scheduling agent 获取反馈、修改期限。**这不等于会议确认科学家永远不与 WMS 交互**；KK 对各方交互的粒度仍有追问。转写对相对期限究竟以 task start 还是 workflow start 为基准也不够一致，具体字段语义待核对。

### 5. 执行反馈要用于修正估计，但没有选定学习算法

会上讨论到 task runtime 和中间文件大小可能只是估计。汇报方设想 WMS 记录真实运行时间、真实中间文件大小，反馈给 scheduling agent，帮助后续安排。

KK 用类似 reinforcement learning 的说法描述这种反馈关系，但随即有保留措辞。**能确认的是“利用实际执行修正后续估计和计划”，不能据此写成“已决定采用强化学习”。** 具体预测器、更新规则或训练方式均未确定。

### 6. KK 的主要质疑：遥测分流后，谁关联完整 workflow 的运行状态？

当前汇报中的分工是：WMS 回报 task 开始、完成、runtime 等执行信息；network agent 从网络侧 API 或测量工具取得网络遥测。Slide 的 long loop 对此直接写了 `Two sources`，并画出 `WMS → scheduling agent → network agent` 与 `SENSE-O/NDT → network agent` 两条绿色 report 路径。因此这里的争议不是 agents 之间完全不交换信息，而是汇总、关联与解释这些信息的职责尚未说明。

KK 认为，这种分法没有提供充分理由：为什么计算侧信息通过 WMS，网络侧信息却单独进入 network agent？除了服务器计算，实验设备也有状态和时序；如果每个组件只知道自己的部分，谁知道整体执行发生了什么？

他用一个科学实验闭环说明问题：

> 化学反应 / 实验设备产生数据 → 本地计算 → 跨站点传输 → 远端计算 → 返回数据 → 调整实验或进入下一步。

这些活动相互依赖。上游计算变慢、实验产出的数据量变化、网络带宽受限，都可能改变后续活动的开始时间和持续时间。系统需要把观测与相应 workflow 的执行关系联系起来，才能理解变化的影响，并更新调度或未来估计。

**KK 明确澄清，他并不是要求 scheduling agent 读取所有 raw network telemetry。** Network agent 可以继续负责使用网络原始指标；关键是系统里必须有地方保留并处理跨组件的依赖，不能把遥测分别交给各组件后，就没有人把它们关联起来。

### 7. 故障例子：知道链路变慢，还要知道哪些任务会受影响

KK 以链路故障后的带宽下降举例：A、B 之间的可用带宽从 `x` 变为 `x/2`，某次传输所需时间可能从 `y` 变为 `2y`。这是会上用于说明问题的简化例子，不是测量结果或普适性能公式。

关键问题是：

1. 哪些 data transfers 使用了受影响的端点 / 路径？
2. 这些 transfers 属于哪个 workflow、与哪些前后任务相关？
3. 传输耗时变化如何传到 scheduler，使其调整相关执行安排？
4. 不使用故障路径的 transfers，如何避免被误认为同样受影响？

汇报方回应依赖已经在 DAG schema 中定义。KK 认可静态依赖存在，但继续追问：**如何把运行时的故障和带宽变化对应到这些依赖上，让 scheduler 知道某次传输会变慢？** 仅有 DAG，并没有解释这个运行时关联过程。

### 8. KK 提出的方向：一个共同的遥测汇总与关联实体

KK 多次建议，让遥测首先到达 **WMS 或专门的 telemetry agent / monitoring entity**，再把适当信息分发给 scheduling agent、network agent，必要时也供 WMS 使用。

他倾向 WMS 的理由是：WMS 应了解 workflow 定义与实际执行，可将遥测放入 workflow 上下文，供 agents 协商和决策。他也提到专门的 telemetry entity，并认为 agent 形式可能便于按需请求额外指标；**没有规定必须由 LLM 实现，也没有定稿具体部署方式。**

会议结束时，KK 仍认为 advisory role 与当前直接采集遥测的解释不一致，要求继续想清楚后再讨论。由于疲劳而结束会议，提到可次日继续，未约定明确时间。

## 二、会后与 Sourabha 的讨论：未经 KK 确认

> 本节记录双方如何尝试理解前一场会议。部分说法在讨论过程中已被修正，其余也不能直接升级成项目设计结论。

### 1. 用多条 transfer 的故障恢复例子理解职责

Sourabha 设想，一条 100 Gbps 链路承载 10 个来自不同 workflow / task 的 transfers。链路故障后，scheduler 找出受影响的 transfers 及剩余数据量，再向 network agent 请求可用替代资源，重新安排传输，例如把两组 transfers 分到不同替代连接。

这个例子试图说明 scheduler 如何结合 workflow 信息与网络反馈。但例子中的两个前提均未确认：

- “network agent 只知道总容量占用，不知道单个 transfer”是当时的假设；尤其在它接收 transfer list、提供 offers 的设计下，需要重新明确它究竟维护哪些映射。补图中的 `capacity ledger · quote engine` 与 `self-repair` 也表明，不能直接把它理解成只知道链路总占用的简单报告组件。
- “scheduler 决定新路径”也只是会后设想；选择资源方案、指定 virtual circuit 与计算底层物理路径之间的边界没有厘清。

双方意识到，这个例子仍主要讨论网络传输，尚未把 compute 延迟如何改变后续传输安排讲完整。

### 2. 独立 telemetry service 成为候选解释，但网络状态仍不可缺少

双方尝试用“底层物理资源—WMS—上层 agents”的层次解释 KK 的意见，同时提出时效性疑问：如果 WMS 主要按 task 事件更新，而 network agent 要按自己的节奏维护网络容量状态，信息是否会过期？**这是对当前设想的担忧，不是已确认的 WMS 能力限制。**

Sourabha 一度提出 network agent 更像应答服务，可能不需要直接读取 telemetry。Linxuan 反问：不知道当前网络状态，如何给出可用容量 offers，又如何维护 hold / commit 之后的资源占用？随后 Sourabha 承认 network agent 确实需要知道当前网络状态。

补图后可以明确，Linxuan 提到“图中的三种 actions / 不同频率”的上下文对应 fast、slow、long 三种循环。不过原图只给出循环的时间尺度，未规定具体轮询频率；独立获取状态是否必要、统一入口能否满足时效性，仍需接口设计来回答。

讨论后形成的**候选方案**是：由独立 telemetry service 从底层或监控端点收集 compute 与 network 状态，两个 agents 按需查询；network agent 仍需获得足够新鲜的信息来维护容量状态。

这还没有回答 KK 的全部问题：**统一采集入口之后，谁把这些指标关联到 workflow / task / transfer，并计算相互影响，仍未明确。** 此句是结合 A、B 两段转写作出的整理判断。

### 3. 需要弄清 Pegasus 与现有监控系统实际提供什么

Sourabha 根据浏览 Pegasus 页面时的印象提到 catalogs、site 信息、scheduler、monitoring service 和资源访问，并追问：如果 WMS 已有这些模块，新 scheduling agent 是其中一部分、替代现有 scheduler，还是外部 advisor？本次没有答案。

双方也提到 DMM / SENSE 相关论文第 3.2 节中的 Prometheus 与传输监控，说法涉及周期查询吞吐量、动态调整带宽。但转写没有附论文全文或明确接口证据，且双方对“经 SENSE 获取”还是“直接查询 Prometheus”存在疑问，故只保留为待核对线索。

关于 compute telemetry，双方讨论了 CPU / GPU 利用率、节点当前负载，以及 task 完成后的 execution report 与运行中的连续观测之间的区别。`top`、`perf` 等仅是讨论中的工具例子；GPU 工具名称转写不清，不强行补全。

**WfFormat 能记录某些 execution 字段，不等于 WMS 已经提供实时查询或推送接口。** 这是双方质疑所指向的接口问题，尚待检查实际系统。

### 4. Correlation 用于当前运行还是未来计划：会后仍有误读风险

Sourabha 表示不确定 KK 所说的 correlation 是用于当前 workflow 的调整，还是用于未来 workflow 的预测和 placement，讨论中还出现“已运行的任务不动，新的 workflow 到来时再考虑状态”的设想。

**对照 A 段，不能把 KK 的要求限定为未来 workflow。** KK 同时谈到当前故障导致传输变慢、需让 scheduler 得知影响，以及利用历史执行更新未来计划。具体如何调整正在运行的任务没有确定，但只考虑未来新请求不能覆盖他的故障例子。

此外，“加入 CPU / GPU utilization 就补齐了问题”也不足以概括 A 段：KK 明确提到了物理实验设备及其与 compute、transfer 的依赖。独立 telemetry service 是否足够，要看它与 workflow 上下文如何衔接。

### 5. 会后提出用一个最小 workflow 手工走通端到端流程

Sourabha 建议先选简单 happy path，逐步写清楚每个组件做什么：

1. 已知输入文件位于站点 S1，设定 T1 在 S1 处理它；
2. T1 产生中间文件，需要传到 S2；
3. T2 需要 GPU，设定 S2 提供 GPU，T2 在 S2 消费中间文件并产生输出。

文件位置固定、T1 在 S1 执行、S2 有可用 GPU，都是为简化例子作出的假设，不是一般调度规则或已获得的真实科学 workflow。双方提到还没有拿到真实例子，并讨论后续再考虑 replica 选择、站点选择和冲突。

手工走通的目的，是明确每一步用了什么 SENSE / NDT 能力、什么 WMS 能力、什么 telemetry，以及谁产生计划、谁发出执行命令。**这是会后建议，尚未实施，也不是 KK 当场分配的实验任务。**

## 三、后续事项与未决问题

### 会议及会后明确提出的后续事项

| 事项 | 来源与责任表述 | 当前状态 |
| --- | --- | --- |
| 重新解释、修改架构图，使 advisor、资源请求、实际执行、监控之间的关系一致 | A：KK 要求汇报方继续思考 | 未完成，需继续与 KK 对齐 |
| 继续思考遥测与 agent 职责，并修改 slides | B：Linxuan 表示会继续考虑 | 会后打算，非架构定稿 |
| 检查 WMS 的组织方式、可提供的信息和 telemetry 能力 | B：Linxuan 请 Sourabha 查看，对方回应会检查（归属按上下文） | 待核对实际接口 |
| 选一个简单 workflow 手工推演端到端信息流与执行流 | B：Sourabha 提议 | 尚未执行 |

上述事项未形成具体完成日期；“明天继续聊”没有落实为明确会议时间。

### 下一次对齐需要回答的问题

- **共同实体放在哪里、负责到哪一步？** WMS、独立 telemetry service，还是二者配合；谁维护 workflow 与观测之间的对应关系，谁把状态变化转成调度影响？
- **哪些调用属于谁？** 资源查询、offer / hold / commit、网络配置、传输启动、遥测获取应分别说明，避免用一个“与网络交互”的箭头概括所有事情。
- **Compute 如何进入调度？** 已知执行站点与可选站点分别怎么处理；上游 compute 的实际结束时间和产出数据量如何更新 transfer window？
- **遥测如何保持新鲜并可关联？** 事件、周期查询或主动请求如何组织；哪些信息已有接口，哪些需要补充？

这些是从讨论整理出的待决项，并非会上已确定的新实现要求。

## 四、关键转写定位片段

以下保留短片段便于回查 A 段；均来自自动转写，不视为核验过音频的精确引语。

| 主题 | A 段原始转写片段 |
| --- | --- |
| WMS 被解释为执行引擎 | `the workflow management system is the actual execution engine` |
| Scheduler 还必须安排计算 | `the scheduler has to first also schedule the computes` |
| 相对时间要落到实际时钟 | `Somewhere all the relative times have to be converted to real times` |
| 不是要求 scheduler 获取原始网络指标 | `I'm not saying that the scheduling agent needs to get the rough uh network information` |
| 遥测需要先到共同实体 | `either a telemementary agent or the work for management system, one of those two places` |
| 必须有人保存相互依赖关系 | `have no place that keeps track of their interdependence` |
| 会末仍要求继续思考 | `Think through these things` |
