# Knowledge(2026-07-28 卷)

> 通用知识点(工具行为 / 系统特性 / 领域事实),不随实验过期。**纯人工维护,agent 不写、不新建**(扫到可给评价,但不改)。
> **本文件是 knowledge 的一卷**,文件名日期 = 本卷起始日期。写大了就手动新建 `knowledge_{新日期}.md` 续写,**最新卷 = 日期最大的那个**(`ls docs/knowledge_*.md` 看全部);旧卷原地保留即是归档,不进 `archive/`。

# 一些start/overview/概念

## AI 如何选择实验

典型闭环是：

1. 定义候选实验参数 x、观测结果 y、目标和约束。
2. 用已有数据拟合 surrogate model，估计结果及不确定性。
3. acquisition function 在“尝试当前最优条件”和“探索未知区域”之间权衡。
4. 执行一个或一批实验。
5. 更新模型，直到达到预算、精度、目标或停止条件。

不同科学问题对应不同方法：

- **最大化 yield、性能或纯度**：Bayesian optimization。
- **尽快学准整个响应面或相图**：active learning、uncertainty sampling。
- **区分竞争科学假设、减少参数不确定性**：Bayesian experimental design、expected information gain。
- **多个冲突目标**：multi-objective BO，返回 Pareto frontier；例如同时考虑性能、成本、毒性和能耗。[qNEHVI paper](https://proceedings.neurips.cc/paper/2021/hash/11704817e347269b7254e744b5e22dac-Abstract.html)
- **存在危险或设备限制**：constrained/safe BO，只在估计安全区域内搜索。[Safe BO example](https://proceedings.mlr.press/v205/rothfuss23a.html)
- **实验有长期状态、动作会改变后续可选动作**：model predictive control、RL 或其他 sequential planning。
- **设备可并行但耗时不同**：batch/asynchronous、cost-aware scheduling。

BoTorch 是通用 BO 研究框架；Phoenics、Atlas、Olympus 更贴近化学和实验规划。[BoTorch paper](https://proceedings.neurips.cc/paper/2020/hash/f5b1b89d98b7286673128a5fb112cb9a-Abstract.html)、[Phoenics](https://pubs.acs.org/doi/10.1021/acscentsci.8b00307)、[Atlas](https://pubs.rsc.org/en/content/articlehtml/2024/dd/d4dd00115j)

LLM 可以帮助提出目标、生成候选和解释结果，但最终选择最好仍经过显式约束、可计算 acquisition function 或可验证规则，而不是直接相信自然语言判断。

## AI 如何控制设备

实际系统通常采用逐层降级：

```
自然语言计划
→ 结构化实验 protocol
→ workflow task
→ 设备抽象 API
→ vendor driver / EPICS IOC / robot controller
→ actuator
```

代表基础设施包括：

- **EPICS**：大型科学设施常用的分布式控制系统，提供设备监控、告警、自动序列、数据采集和反馈控制。[EPICS documentation](https://docs.epics-controls.org/en/latest/)
- **Bluesky + Ophyd**：Bluesky 负责编排和数据采集，Ophyd 把 EPICS、HTTP 或其他设备接口封装成 `trigger/read/set` 等统一抽象，并支持 pause/resume、错误处理、metadata 和 adaptive acquisition。[Bluesky](https://blueskyproject.io/)、[Ophyd](https://blueskyproject.io/ophyd/)
- **SiLA 2**：面向实验室设备互操作的 typed service 标准，基于 HTTP/2、gRPC 和 Protocol Buffers。[SiLA 2 technical note](https://sila-standard.com/wp-content/uploads/2018/12/SiLA2-TechNote.pdf)
- **HELAO**：把设备和实验动作包装成异步 Web 服务，再由 orchestrator 调用。[HELAO paper](https://advanced.onlinelibrary.wiley.com/doi/abs/10.1002/admi.202101987)
- **AlabOS**：管理样品、任务、设备状态和资源冲突，支持并发实验及 human intervention。[AlabOS paper](https://www.sciencedirect.com/org/science/article/pii/S2635098X24001839)

系统设计上，agent 不应该拥有无约束的原始电机、温度或阀门写权限。安全边界应由 typed schema、状态机、权限检查、物理联锁和本地控制器强制；LLM 主要负责高层 planning 和 tool selection。

## Scientific workflow 与普通程序的区别

科学计算 workflow 通常表达为任务及数据依赖图，需要处理：

- CPU/GPU/HPC/edge 等异构资源；
- HPC queue 和动态任务调度；
- 数据 staging、缓存和跨站传输；
- container/environment；
- retry、checkpoint、失败恢复；
- 参数、代码、输入输出和 provenance；
- 根据运行中新数据动态产生后续任务。

**Parsl** 负责任务依赖和跨集群/HPC执行。[Parsl](https://parsl.readthedocs.io/en/stable/)  
**Colmena** 在 Parsl 上增加 AI steering：结果一返回，agent 就能更新模型并决定下一批 simulation；其系统论文明确把 reaction、decision、dispatch latency 和大对象数据传输视为扩展瓶颈。[Colmena paper](https://journals.sagepub.com/doi/10.1177/10943420241288242)  
**Globus Flows/Transfer** 更偏跨机构的可靠数据移动、身份认证和服务编排，能让仪器产出自动触发 transfer、compute、index 和人工审批。[Globus Flows](https://www.globus.org/platform/services/flows)

物理实验比计算 workflow 更难，因为很多动作不可简单重试：样品已经混合、试剂已经消耗、炉子已经升温。系统必须跟踪现实状态，而不能假设 task 是无副作用的纯函数。

## 最值得认识的系统与案例


| 系统/论文                       | 它真正展示的能力                                                                                                                                                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mobile Robotic Chemist      | 10 维空间内用 batch Bayesian search，8 天运行 688 次实验；代表“优化器＋移动机器人＋现有仪器”闭环。[Nature](https://www.nature.com/articles/s41586-020-2442-2)                                                                                                                     |
| A-Lab                       | 文献模型、active learning、粉末处理机器人和 XRD 分析组成材料合成闭环。修订后的可信口径是 57 个目标中确认合成 36 个；最初 40 个成功中有 4 个仅凭 XRD 无法确认，且“novel material”措辞被纠正。[论文](https://www.nature.com/articles/s41586-023-06734-w)、[作者更正](https://www.nature.com/articles/s41586-025-09992-y.pdf) |
| ChemOS                      | 连接 optimizer、机器人、characterization、数据库和人类界面的中央 orchestration 层。[论文](https://pubmed.ncbi.nlm.nih.gov/32298284/)                                                                                                                                     |
| INTERSECT                   | ORNL 的 federated system-of-systems：连接仪器、机器人实验室、edge/HPC、数据和 AI，而不是某个单独 SDL。[ORNL](https://www.ornl.gov/intersect)                                                                                                                                 |
| Virtual Infrastructure Twin | 用网络虚拟化和容器复制跨站仪器与计算基础设施，并通过测量校正 twin 与物理 testbed 的差异。[ORNL paper](https://www.ornl.gov/publication/virtual-framework-science-federations-instruments-access-and-control)                                                                           |


---



# scientific workflow的例子

最关键的一句话是：

> Scientific workflow 不是“一段依次运行的脚本”，而是一个跨仪器、edge、网络、存储、HPC/GPU 和 AI planner 运行的分布式状态机。SciNet 位于这些组件之间的数据与控制通路上。

下面用一个现实可行但尚未确认就是合作方 workload 的例子说明。

## 例子：AI 引导的远程显微镜扫描

假设：

- 站点 A 有昂贵的 X-ray 显微镜；
- 站点 A 有一台 edge server；
- 站点 B 有 HPC/GPU 集群；
- AI 根据刚刚拍到的图像，决定下一次应该扫描样品的哪个位置；
- 两个站点通过科研广域网连接。



### 1. CPU/GPU/HPC/edge 异构资源

这个例子中存在四类计算：


| 资源       | 位置   | 做什么                    |
| -------- | ---- | ---------------------- |
| 仪器控制器    | 站点 A | 电机、曝光、传感器、联锁           |
| Edge CPU | 仪器旁边 | 快速校准、压缩、异常检测和缓存        |
| HPC CPU  | 站点 B | 大规模重建、simulation、数据预处理 |
| GPU      | 站点 B | 图像分割、模型推理、模型更新         |


为什么不把所有东西都发到 GPU？

- 仪器控制需要低延迟，必须接近设备；
- 原始数据可能太大，应该先在 edge 筛选或压缩；
- 一些重建程序更适合 CPU；
- AI inference/training 更适合 GPU。

SciNet不决定 GPU kernel 怎样执行，但可以影响：

- 数据应该传到哪个计算站点；
- 数据能否及时到达 GPU；
- 是否因为网络拥塞导致昂贵 GPU 空等；
- 是否应把部分计算留在 edge，减少跨站传输。

---



### 2. HPC queue 和动态任务调度

Workflow orchestrator 提交任务后，任务不会立即获得 GPU，而是进入 Slurm/PBS 一类的 HPC queue：

```
Job submitted
    ↓
等待 GPU allocation
    ↓
输入数据就绪
    ↓
启动 container
    ↓
执行分析
```

这里有两个不同的 scheduler：

1. **HPC scheduler**：决定哪个 job 获得哪块 GPU。
2. **Workflow scheduler**：决定现在应该提交哪些 job、哪些任务依赖哪些结果。

SciNet通常不能直接缩短 HPC 排队时间。但网络可能间接制造两种浪费：

- GPU 已经分配，但输入数据还没传完；
- 数据早已传到错误站点，AI 又决定把任务放到另一台集群。

因此可能需要联合考虑：

```
计算资源什么时候可用
            +
数据什么时候能到达
            +
当前网络是否拥塞
```

不过“修改 Slurm 排队策略”属于 HPC scheduling；“根据网络状态调整数据和任务放置”才可能进入 SciNet 邻近范围。

---



### 3. Data staging、缓存与跨站传输

数据通常不会从显微镜直接流进 GPU memory，而会经过：

```
仪器本地 buffer
  → edge cache
  → WAN transfer
  → HPC landing storage
  → parallel filesystem / object store
  → GPU node local storage / memory
```

**Staging** 的含义是：在计算开始前，将数据放到计算能够高效访问的位置。

缓存则可能出现在：

- edge 保留原始数据，防止 WAN 中断；
- HPC storage 保留重建后的中间结果；
- GPU 节点缓存模型权重；
- 网络侧或数据服务缓存重复使用的数据。

这里正是 SciNet 最直接的位置：

```
[Site A edge] ═════ SciNet / WAN ═════ [Site B storage + HPC]
```

SciNet可能优化：

- 走哪条路径；
- 如何避免拥塞；
- 是否并行使用多条路径；
- bulk data、checkpoint 和控制消息如何区别对待；
- 传输失败后怎样恢复；
- 哪个 workflow 的数据更紧急；
- 是否提前把下一阶段需要的数据传过去。

---



### 4. Container/environment

GPU job 需要的不只是输入数据，还需要一套确定的软件环境：

```
container image
+ CUDA / library versions
+ reconstruction code
+ trained model
+ configuration
```

Container解决的是“同一段分析代码能否在另一台机器正确运行”，不是网络问题。

但网络仍会间接影响：

- container image 是否需要跨站拉取；
- 大模型权重是否提前缓存；
- 不同站点是否重复传输同一个 environment；
- environment 不可用是否导致 workflow 延迟。

因此：

> Container负责计算环境一致性；SciNet负责把 environment、模型和数据可靠地送到需要它们的地方。

---



### 5. Retry、checkpoint 和失败恢复

不同失败由不同层恢复。

#### 情况 A：WAN 中途断开

Edge仍保存原始数据，传输系统从断点恢复，SciNet可能重新选路。

```
主要责任：数据传输系统 + SciNet
```



#### 情况 B：GPU job 被抢占或节点宕机

Workflow orchestrator找到最近的 checkpoint，重新提交 job。

```
主要责任：workflow runtime + HPC scheduler
SciNet只负责checkpoint的传输和可达性
```



#### 情况 C：显微镜出现危险状态

本地 EPICS/PLC/interlock 立即停止设备，不能等待远程 AI 或网络判断。

```
主要责任：本地设备控制和安全系统
不属于SciNet
```



#### 情况 D：站点 B 的 GPU queue 太长

Workflow可以改投另一个计算中心，但前提是数据能及时迁移过去。

```
主要责任：workflow/resource scheduler
SciNet提供网络状态和跨站数据通路
```

这说明“resilience”不是一个统一 retry 按钮，而是不同层各自负责不同故障。

---



### 6. 参数、代码、输入输出和 provenance

一次任务至少要记录：

```
谁发起的
科学目标是什么
输入数据是哪一份
扫描位置和曝光参数
使用了哪个分析代码 commit
使用哪个 container digest
模型版本是什么
运行在哪个 GPU 节点
产生了哪些输出
AI 为什么选择下一次扫描
中间是否失败或重试
```

Provenance是这些实体之间的关系图：

```
raw image
  + scan parameters
  + code version
  + model version
        ↓
analysis result
        ↓
next experiment decision
```

SciNet不负责定义“模型版本”或“实验参数”的科学含义，但它可能：

- 携带 workflow/project identity；
- 将网络 telemetry 与某个科学任务关联；
- 记录某次传输用了什么路径、何时发生丢包或拥塞；
- 帮助解释为什么一个 workflow 变慢或失败。

这正对应 SciNet 官方描述中的：用 science project information 标记流量，并把异构网络运维数据与 scientific workflow 关联。[ORNL SciNet](https://www.ornl.gov/project/ai-powered-operations-self-driving-science-research)

---



### 7. 根据新数据动态产生后续任务

传统静态 workflow：

```
扫描100个位置 → 全部传输 → 全部分析
```

运行前任务图已经完全确定。

动态 workflow：

```
扫描位置 A
   ↓
AI 发现 A 附近存在异常结构
   ↓
取消原计划中的低价值区域
   ↓
增加 A1、A2、A3 三个高分辨率扫描
   ↓
为新数据动态创建 transfer 和 GPU analysis task
```

这使负载变得难以预测：

- 下一分钟会产生多少数据并不确定；
- 新任务可能比旧任务优先级高；
- GPU、存储和网络需求会突然变化；
- workflow 的关键路径会随 AI 决策改变。

这就是 SciNet强调“science-aware”的原因：网络不能只看到一批无意义的 TCP/UDP flow，而需要理解至少部分 workflow context。

## SciNet究竟优化哪一段

整个闭环延迟可以粗略写成：

```
T_loop =
    T_measure
  + T_edge
  + T_transfer
  + T_queue
  + T_compute
  + T_decision
  + T_control-return
  + T_failure-recovery
```

SciNet直接影响的主要是：

```
T_transfer
T_control-return
network-caused failures
network recovery time
```

间接影响：

```
数据未到导致的 GPU idle
跨站任务放置
checkpoint 恢复速度
动态 workflow 的资源等待
```

通常不直接影响：

```
仪器曝光时间
GPU kernel 运行速度
Slurm 的排队政策
AI 选择实验的算法质量
设备本地安全联锁
```



## “Science-aware network”比普通网络多知道什么

同一个 workflow 里可能同时存在三类流量：


| 流量         | 特征  | 真正需求 |
| ---------- | --- | ---- |
| 下一次扫描命令    | 很小  | 延迟敏感 |
| 原始图像       | 很大  | 吞吐敏感 |
| Checkpoint | 中等  | 恢复关键 |
| 历史数据归档     | 很大  | 可以等待 |


普通网络主要看到地址、端口、带宽和拥塞。

理想的 SciNet 还知道：

```
workflow ID
科学项目
当前 workflow stage
数据依赖
deadline / latency sensitivity
数据敏感性
源仪器和目标 GPU
失败会阻塞哪些后续任务
```

它就可能作出这样的决定：

> “归档流量虽然很大，但暂时延后；先保障控制消息和正在阻塞 GPU 的图像数据。”

这不是让网络替 AI 决定“下一次扫描哪里”，而是让网络知道：

> **AI 已经决定了下一步，现在什么数据和控制消息最关键，怎样使这个决定尽快且可靠地落地。**

因此最准确的定位是：

```
AI planner：决定下一步科学行动
Workflow runtime：把行动变成跨资源任务
SciNet：保障这些跨机构任务之间的数据与控制依赖
```

SciNet 不是整个 scientific workflow，也不是它的“大脑”；它是 workflow 穿越不同机构时的 science-aware 数据与控制基础设施。

---



## 什么是 intent

先给最重要的区分：

> `Workflow intent`、`network policy` 和 `SLA` 不是同一件事。  
> Intent 表达“想达到什么结果”，policy 表达“系统必须遵守什么规则”，SLA 表达“网络承诺达到什么可测服务水平”。

SciNet Flow Engine 则负责把这三样东西转成真正的跨域网络动作，并在运行中持续检查和调整。

在 intent-based networking 中，intent 是声明式的目标：

> 告诉系统“我要什么”，而不是告诉每一台交换机“具体怎样配置”。

例如，科学 workflow 不应该自己写：

```
在交换机 A 创建 VLAN 310
在交换机 B 的端口 7 配置 queue 4
在域 C 创建 MPLS tunnel
把 DSCP 设置为 32
```

它应该表达：

```
我要把数据集 D 从站点 A 传到站点 B；
必须在站点 B 的 HPC job 开始前到达；
传输失败时要自动恢复；
这批数据不能走不受信任的路径。
```

ESnet SENSE 的官方定位就是让 application/workflow 通过 intent interface 表达高层服务需求，再由 orchestrator 和各域 Resource Manager 创建端到端网络服务。[SENSE overview](https://sense.es.net/)、[SENSE architecture](https://sense.es.net/architecture)

Intent 不一定是自然语言，也不一定需要 LLM。在 SENSE 中，它可以是结构化 schema；SciNet slides 也画了 JSON/YAML interface。

## 四层容易混淆的东西


| 层次                      | 回答的问题                | 示例                                    |
| ----------------------- | -------------------- | ------------------------------------- |
| Science/workflow intent | 科学 workflow 想完成什么    | “数据必须在 HPC job 开始前到达”                 |
| Network service intent  | 需要网络提供什么能力           | “A→B、这个时间窗口、所需带宽、安全要求”                |
| Network policy          | 网络执行时必须遵守什么规则        | “该 flow 进入保证带宽队列；后台流量只能 best effort”  |
| SLA                     | 网络对 workflow 做出的可测承诺 | “保证 20 Gbps；服务在 00:00–02:45 有效；失败要告警” |
| Device configuration    | 最终怎样配置设备             | P4 rule、queue、VLAN、L3VPN、MPQUIC path  |


其中前两层说“what”，后两层逐渐进入“how”。

## 具体例子：HEP 数据 staging

以下数据量和时间是为了说明概念，不是周会给出的实际参数。

假设一个 HEP workflow：

- 站点 A 有一份 20 TB 的 event data；
- 站点 B 的 HPC allocation 在凌晨 03:00 开始；
- 数据必须在 02:45 前传完；
- 同一网络上还有不紧急的历史数据归档。



### 原始 workflow intent

科学家或 workflow manager 真正关心的是：

```
workflow: hep-analysis-42
dataset: event-data-D
source: site-A
destination: site-B
must_be_ready_before: "02:45"
reason: "HPC allocation starts at 03:00"
failure_behavior: "notify scheduler early or choose another site"
security: "approved research domains only"
```

这里甚至不必写带宽，因为科学家关心的是“不要让已经预约的 HPC 空等”。

这就是 workflow intent：包含科学任务的目的、依赖和 deadline。

### Intent Characterization 做什么

它把科学需求翻译成网络能理解的需求。

20 TB 在约 3 小时内传完，平均需要约 15 Gbps；考虑协议开销和抖动，系统可能请求一个示意性的 20 Gbps 服务。

得到 network service intent：

```
endpoints:
  source_dtn: site-A-dtn
  destination_dtn: site-B-dtn
time_window:
  start: "00:00"
  end: "02:45"
bandwidth:
  requested: 20 Gbps
qos:
  class: guaranteed
workflow_context:
  workflow_id: hep-analysis-42
  blocking_resource: site-B-hpc-allocation
security:
  allowed_domains: approved-only
```

SENSE 已支持表达 connection、QoS class、capacity 和查询最大可用带宽；其 QoS 示例包括 `guaranteedCapped`、`softCapped` 和 `bestEffort`。[SENSE technical report](https://www.osti.gov/servlets/purl/1670785)

### 为什么需要 network policy

设备无法直接执行：

> “不要让 HPC 空等。”

它只能执行具体规则。因此需要派生 network policy：

```
Policy 1:
属于 workflow hep-analysis-42 的 A→B 数据进入保证带宽 traffic class。

Policy 2:
00:00–02:45 为它保留端到端容量。

Policy 3:
历史归档流量降为 best effort，不能抢占关键 workflow。

Policy 4:
只允许经过符合安全要求的域和 endpoint。

Policy 5:
如果主路径无法满足承诺，允许 Flow Engine 选择备用路径。
```

此外还有另一类 policy：网络运营方自己的约束，例如：

- 单一项目不能占用超过某个比例；
- 某些路径不能承载敏感数据；
- 关键控制流量优先于 bulk transfer；
- 不允许两个 agent 同时修改同一条网络资源。

所以实际关系是：

```
Workflow intent
      +
当前网络状态
      +
运营方 policy
      ↓
可接受的 network service
```



### 为什么需要 SLA

假设网络只说“我尽力传”，workflow scheduler 仍然不知道：

- 要不要现在申请 HPC；
- 数据能否按时到达；
- 是否应该换到另一个计算中心；
- 什么时候应该判定传输失败。

SLA 把网络服务变成可依赖、可监控的承诺。例如：

```
service_window: "00:00–02:45"
guaranteed_capacity: 20 Gbps
availability_target: ...
violation_notification: immediate
measurement:
  - achieved_throughput
  - packet_loss
  - transfer_progress
```

严格说，SLA、SLO 和 QoS 也有区别：

- **QoS**：网络采用的服务机制或类别；
- **SLO**：某项具体可测目标；
- **SLA**：对一组 SLO、责任和违约处理的正式约定。

SciNet slides 使用的是比较宽泛的 “new SLAs for Science”，未说明是否真的是法律/商业意义的 SLA。当前更安全的理解是：

> 面向 scientific workflow、可被监控和验证的服务承诺。



# SciNet Flow Engine 的目的是什么

一句话：

> Flow Engine 是把声明式 intent 持续转换成可执行、可验证、可恢复的跨域网络动作的 runtime。

它不是：

- 数据传输程序本身；
- 交换机；
- 单个路由算法；
- LLM；
- 科学 workflow manager；
- Network Digital Twin。

它更像一个面向网络的 Kubernetes controller 或 workflow runtime：

```
期望状态：workflow需要什么
实际状态：网络现在是什么样
差异：哪里不满足
动作：调用agent和设备API进行调整
然后继续监控和reconcile
```

周会图里 Flow Engine 包含：

- task queue；
- distributed job queue；
- SciNet database；
- dynamic task branching；
- configuration management；
- conflict resolution；
- Network Resource Manager agent；
- route optimization agent；
- security enforcement agent。

这说明它的重点不是“调用一次最短路径算法”，而是组织整个控制过程。

## HEP 例子中 Flow Engine 怎样运行



### 第一步：接收和验证 intent

Flow Engine 收到：

```
20 TB数据必须在02:45前到达站点B
```

它先检查：

- endpoint 是否存在；
- 用户是否有权限；
- 时间和数据量是否合理；
- 目标存储、DTN 和 HPC allocation 是否对应；
- intent 是否与运营方 policy 冲突。



### 第二步：查询资源

它向多个 Resource Manager 查询：

```
站点A内部网络是否可用？
站点A的DTN是否有容量？
WAN有哪些可行路径？
站点B入口和DTN是否可用？
是否存在已预约的其他关键workflow？
```

SENSE 的架构也是由 Orchestrator 接收请求，再协调不同管理域的 Resource Manager；每个 RM 只负责本域资源。[SENSE architecture](https://sense.es.net/architecture)

### 第三步：生成候选计划

例如：

```
Plan A:
主路径P1，20 Gbps，00:00开始。

Plan B:
P1和P2并行，使用MPQUIC。

Plan C:
提前开始传输，但只能保证15 Gbps。

Plan D:
改发到另一个具有可用HPC资源的站点。
```

如果当前资源无法满足 intent，Flow Engine 不应该静默失败，而应返回：

```
原请求不可满足；
可以提前30分钟开始，或者把带宽降到15 Gbps。
```

这对应 SENSE 的 query/negotiation 能力。

### 第四步：在 NDT 中检查

在真正修改网络前：

- 检查路径是否可达；
- 检查新配置是否与现有规则冲突；
- 模拟链路故障或背景流量；
- 预测能否满足 SLA；
- 检查是否会影响其他 workflow。

注意：周会 slides 只写了 NDT 用于 “testing, configuration checks”。上述更细步骤是合理展开，还没有证据表明合作方 NDT 已全部实现。

### 第五步：生成并排序底层任务

Flow Engine 把计划拆成有依赖的动作：

```
1. 站点B创建接收端和安全规则
2. WAN建立服务路径
3. 站点A配置DTN和traffic class
4. P4 agent安装flow rule
5. SmartNIC/MPQUIC agent配置数据通路
6. 检查端到端连通性
7. 通知workflow开始传输
```

为什么需要 task queue？

因为第 6 步不能在第 1–5 步完成前执行，而且不同管理域的操作可能异步完成或失败。

### 第六步：持续监控和动态分支

假设凌晨 01:00 主路径发生拥塞：

```
Monitoring发现：
按当前速度，数据可能到03:20才传完
        ↓
SLA violation predicted
        ↓
Flow Engine创建新任务分支
        ↓
NDT测试备用路径
        ↓
route agent切换部分流量
        ↓
security agent确认新路径合规
        ↓
继续传输
```

这里就是 slides 中的 `dynamic branching of tasks`。

### 第七步：处理冲突

假设另一个 workflow 也要求同一时间占用相同链路。

Flow Engine必须决定：

- 两者是否能同时满足；
- 是否根据 deadline 调整；
- 是否延迟 background transfer；
- 是否拒绝其中一个请求；
- 多个 route agent 的修改是否互相覆盖。

这就是 `configuration management` 和 `conflict resolution` 的意义。

### 第八步：完成和释放资源

数据完成后：

- 验证目标端数据完整；
- 通知 HPC workflow 输入已就绪；
- 释放临时网络资源；
- 保存 intent、计划、配置、telemetry 和 SLA 结果。



## Characterization 和 Flow Engine 的边界


| 组件                                | 主要职责                   |
| --------------------------------- | ---------------------- |
| Intent Characterization           | 理解需求、补全语义、把科学依赖翻译成网络需求 |
| Flow Engine                       | 在运行时计划、执行、协调、监控和修复     |
| Network Digital Twin              | 在真正应用配置前测试候选动作         |
| Resource Manager / hardware agent | 操作一个具体网络域或设备           |
| Monitoring                        | 提供真实状态并判断 SLA 是否满足     |


所以：

```
Intent Characterization = 编译器前端
Flow Engine             = runtime + controller
NDT                     = test/sandbox
Hardware agents         = device drivers/executors
```

最后压缩成一句话：

> Task 1 研究“怎样把 scientific workflow 说的话翻译成网络语言”；Task 2 的 Flow Engine 研究“怎样让这句话在一个不断变化、跨多个机构的真实网络中持续成立”。

---



# ESnet 是什么

ESnet 全称 Energy Sciences Network，是美国能源部 DOE 面向科研的专用高性能广域网，由 Lawrence Berkeley National Laboratory 运营。

你可以把它理解成：

> DOE 科学设施之间的“国家级科研骨干网 + 网络服务平台”。

它连接国家实验室、HPC 中心、科学仪器、大学和其他研究设施。它不仅提供链路，还开发网络监控、性能诊断、按需网络服务和网络编排工具，例如 perfSONAR、OSCARS、SENSE 等。[ESnet 官方介绍](https://www.es.net/about/our-mission)

例如：

```
BNL/实验仪器
    │
    │ 大规模科学数据
    ▼
ESnet 跨州科研骨干网
    │
    ▼
NERSC/OLCF/ALCF 等 HPC
```

所以 ESnet 是：

- 真实的网络基础设施；
- 网络运营者；
- 网络服务提供者；
- 同时也是网络控制与编排工具的研发方。

它不是一个 API，也不是一个单独的软件。

---



# IRI-API 是什么

IRI 是 DOE 的 Integrated Research Infrastructure 计划，目标是把实验设施、数据设施、HPC 和 ESnet 连接成一个可以协同使用的基础设施生态。[DOE IRI 官方介绍](https://iri.science/)

IRI-API，更准确地说是 IRI Facility API，是不同设施共同采用的一组标准化 API。它希望解决的问题是：

> 不管后面是 NERSC、OLCF、ALCF，还是其他 AmSC 站点，workflow 和 agent 都能用相似的接口查询资源、提交任务和管理数据。

例如，一个 agent 想在 NERSC 提交分析任务：

```
GET  /status/...        查询设施是否可用
GET  /account/...       查询 allocation/account
POST /compute/...       提交计算任务
GET  /compute/...       查询任务状态
POST /filesystem/...    操作站点文件
```

每个设施在 API 后面写自己的 adapter：

```
统一的 IRI API
       │
       ├── NERSC adapter → Slurm、NERSC 存储、NERSC 账户
       ├── OLCF adapter  → OLCF 调度器和存储
       └── 其他站点 adapter
```

官方 Python reference implementation 当前包含 facility、status、account、compute、filesystem、storage、task 等接口组。[IRI Facility API 参考实现](https://github.com/doe-iri/iri-facility-api-python)

AmSC 页面还把 resource orchestration 和 WAN management 列为目标能力。不过要特别注意：截至目前它仍标为 **Incubator、v0.1**，各设施可以只开放自己已经实现的接口，所以不能把它当成已经完成、所有站点一致可用的成熟标准。[AmSC IRI-API 页面](https://amsc.energy.gov/products/iri-api/)

## ESnet 和 IRI-API，UCR 更需要关注哪个

如果必须二选一，**IRI-API 与 UCR 当前 Task 3 的距离更近**；但 UCR 不能忽略 ESnet/SENSE。

原因是第一次周会里给 UCR 的高层任务是：

> Integration with Monitoring, Agents and APIs；让 SciNet agents 通过 monitoring 和 digital twin 层与 hardware agents 协调；merge/test NDT。

而 slides 把“研究 ESnet offered tools”主要写在 Task 2 Flow Engine 下，不是 UCR 主导的 Task 3。[第一次周会 PDF，第 3–5 页](/Users/lxzhong/Documents/GitHub/genesis_scinet/resources/28July2026-meeting.pdf)

因此目前可以这样排优先级：

1. **最高优先级：合作方 NDT**
  - NDT repo 是什么；
  - 怎么启动；
  - 输入输出 schema；
  - 如何注入 topology、traffic、failure；
  - 怎样返回指标；
  - 是否支持来自真实网络的 telemetry。
2. **第二优先级：Agent/NDT/monitoring API**
  - Agent 如何提交候选方案；
  - NDT 如何返回结果；
  - 多 agent 如何共享状态；
  - 任务 ID、异步执行、错误处理和 provenance 怎么设计。
3. **第三优先级：IRI-API**
  - 它是否会成为 SciNet agent 调用站点、计算、数据和 WAN 能力的公共接口；
  - UCR 是否需要为 NDT 写一个 IRI-compatible adapter；
  - 当前真正可用的是哪些 endpoint。
4. **需要理解但未必由 UCR 主导：ESnet/SENSE**
  - 它提供哪些真实网络能力；
  - Flow Engine 最终如何与 ESnet 服务对接；
  - NDT 中应该模拟哪些 ESnet capability。

也就是说：

> ESnet 是 UCR 将来要对接的真实网络环境和能力来源；IRI-API 更可能是 UCR 代码直接面对的公共接口之一。

两者不是竞争关系。ESnet 本身也是 IRI 体系的参与者。

---



# `amsc.energy.gov/product-catalog` 是什么

它更准确地说是 **AmSC 能力和产品目录**，不是论文成果库。

页面自己的描述是：搜索 American Science Cloud 生态中的 tools、services、datasets、models、documentation 和其他资源。[AmSC Product Catalog](https://amsc.energy.gov/product-catalog/)

里面现在列出的内容包括：

- Model Access Gateway；
- Federated ID/SSO；
- AmSC User Portal；
- IRI-API；
- AmSC Python SDK；
- Curated Software Stacks；
- Data Movement；
- Data Lakehouse；
- Data Catalog。

每个条目可以包含：

- 能力说明；
- 当前状态，如 Incubator；
- 版本；
- demo/MVP 目标；
- documentation；
- source code；
- feature request 入口。

所以它有三种作用：

1. 让项目组知道 AmSC/Genesis 已经在开发什么，避免重复造轮子；
2. 告诉用户这些能力怎样访问、成熟到什么程度；
3. 作为以后可复用软件和服务的展示、发现入口。

“是不是希望我们以后把成果展示在这里？”——**有这种可能，但周会 slides 没有明确说 SciNet 必须在这里登记成果**。如果 SciNet 最终产出的是可供其他项目使用的 service、API 或工具，例如 SciNet Flow Engine service、NDT adapter，那么很适合进入 catalog；如果产出只是论文、实验结果或 SC demo，则不一定放在这里。

因此这次发链接更像是在说：

> 先看看 Genesis/AmSC 已有哪些产品、API 和基础设施，SciNet 应该怎样接入其中。

---



# “NVIDIA Omniverse digital twin ideas” 是什么

周会 slides 里只有一句 “Nvidia omniverse DT-ideas”，因此它目前只是一个待探索的方向，并没有给出已经确定的架构。

Omniverse 是 NVIDIA 基于 OpenUSD 的数字孪生开发平台，主要负责：

- 表达设施、设备和空间结构；
- 汇聚 CAD/3D/设备模型；
- 接入实时 telemetry；
- 运行或调用物理仿真；
- 可视化 what-if 场景；
- 为 AI agent 提供仿真环境和合成数据。

[NVIDIA Omniverse Digital Twins](https://docs.omniverse.nvidia.com/digital-twins/latest/overview.html)

对 SciNet 来说，可能的用法是：

```
Omniverse / OpenUSD
  ├── 可视化实验设施、HPC、交换机、链路和机房
  ├── 展示实时 telemetry 和 workflow flow
  ├── 让用户交互式修改某个场景
  └── 调用外部 network simulator/NDT 来计算结果
```

NVIDIA 最近的 AI Factory Digital Twin 架构甚至把 network、thermal、electrical、grid 等仿真统一到一个 digital-twin runtime 中，并用 NVIDIA Air 建模和验证网络拓扑。[Omniverse DSX Blueprint](https://docs.omniverse.nvidia.com/dsx/latest/overview.html)

但这不意味着 Omniverse 自己就是适合 SciNet 的 WAN 网络仿真器：

- Omniverse 强项是 3D/OpenUSD、数据集成、可视化和物理仿真框架；
- WAN packet、queue、routing、TCP/traffic engineering 的准确性仍需要专业网络 simulator/emulator 或外部模型；
- NVIDIA Aerial Omniverse Digital Twin 主要针对 5G/6G 无线传播，也不能直接等同于 ESnet 类广域科研网络。

所以当前最稳妥的理解是：

> Omniverse 可能是 NDT 的展示和集成外壳，也可能用于 AI Factory/data-center 场景；它是否会成为 SciNet NDT 的核心，目前完全没有确定。

---



# 对 UCR、Agent 和 NDT 的理解

可以先用下面这个闭环理解：

```
workflow intent / SLA
          │
          ▼
Agent 生成一个或多个候选网络方案
          │
          ▼
SciNet Flow Engine
解释 intent、应用 policy、处理多 workflow 冲突
          │
          ▼
UCR 建设或集成的 Agent ↔ NDT 接口
          │
          ▼
NDT 读取 topology、configuration、telemetry
测试候选方案、故障和 what-if 场景
          │
          ▼
返回可行性、预测性能、违规项和失败原因
          │
          ▼
Agent / Flow Engine 修改或选择方案
          │
          ▼
权限与安全检查
          │
          ▼
hardware agent / network controller
          │
          ▼
真实网络
          │
          └── 新 telemetry 回到 monitoring/NDT
```

例如 Agent 提出：

> 在 14:00–15:00 为 BNL→NERSC 的 workflow 建立 200 Gbps 路径，并保证 50 TB 数据在 GPU 作业启动前传完。

NDT 不应该只返回 `yes/no`，而可以返回：

```
candidate A:
  feasible: false
  reason: shared link L3 only has 80 Gbps residual capacity

candidate B:
  feasible: true
  predicted throughput: 176 Gbps
  predicted completion: 13:55
  policy violation: none
  failure test: survives link L4 failure, not L7 failure
```

然后 Agent/Flow Engine 再选择 B，或者重新规划。

但是，“NDT 就是 ns-3/OMNeT++ 的一比一真实环境模拟”不够准确。

更准确的关系是：

```
ns-3 / OMNeT++ / Mininet / containerlab / virtual routers
                         │
                         ▼
                 可能成为 NDT 的模型层
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
真实 telemetry      真实拓扑/配置       双向控制接口
       └─────────────────┼─────────────────┘
                         ▼
                    完整 NDT
```

NDT 相对于普通仿真器增加了：

- 与某个特定真实网络的对应关系；
- 来自真实网络的 topology、configuration 和 telemetry；
- 根据真实观测进行校准；
- 面向 agent/controller 的稳定输入输出接口；
- 验证后的决策可能回到真实网络；
- 持续的生命周期、版本和状态管理。

而且不要求“一比一复制所有东西”。小网络可以逐设备虚拟化；大型网络通常必须混合使用：

- packet-level simulation；
- emulation/virtual NOS；
- 数学模型；
- queue/network calculus；
- learned surrogate model；
- knowledge graph；
- 历史数据与实时 telemetry。

简单地一比一复制大型真实网络，资源成本可能根本不可接受。当前 IRTF 的 NDT 架构草案也把 ns-3 视为 NDT 的前身或一种低保真变体，关键差异在于 NDT 有真实—虚拟映射和闭环接口；该文档目前仍是 Internet-Draft，不是正式标准。[IRTF NDT 架构草案](https://datatracker.ietf.org/doc/draft-irtf-nmrg-network-digital-twin-arch/12/) NIST 对一般 digital twin 的描述也强调它应当是动态、数据驱动并与物理对象连接和同步的表示。[NIST Digital Twin Essential Elements](https://www.nist.gov/digital-twins/essential-elements)

最后，对 UCR 任务最严谨的当前表述是：

> UCR 在 Phase 1 的明确任务，是让 SciNet agents 能通过 API 和 monitoring 与合作方 NDT 交互，并完成 merge、test 和多 agent 通信 demo。至于 NDT 底层究竟使用 ns-3、OMNeT++、emulator、数学模型还是混合架构，目前的周会 PDF 没有答案；action item 甚至仍是“把 NDT repo 发给大家”。因此不能提前假设它是一比一模拟器。

---



# X-machines



## 1. Multi-agent 是怎么搭的



### 1.1 单个 agent 的形式化骨架：X-machine

FLAME 的核心不是"agent 类"，而是**带记忆的扩展状态机**（§3.1, p.44-47）：

```
A = (Σ, Γ, Q, M, Φ, F, q₀, m₀)
     输入 输出 状态集 记忆 转移函数集 状态转移 初态 初始记忆
其中 Φ : Σ × M → Γ × M     （消息+记忆 → 消息+记忆）
     F : Q × Φ → Q          （状态跳转由函数决定，不是由条件决定）

```

关键区别（Fig 3.2, p.46）：同一只觅食蚂蚁，纯状态机需要 5 状态 + 大量条件边；X-machine 把复杂度挪进 **memory 变量**，状态数和边数大幅下降。**状态迁移由"执行了哪个函数"驱动，而不是由 if 条件驱动**——这是它能被静态分析、自动并行化的前提。

建模流程被固定成 5 步（§3.3, p.53 / §4.7, p.71）：

1. 识别有哪些 agent
2. 每个 agent 的 memory 变量
3. 每个 agent 的 functions
4. agent 之间的 messages（含输入 filter）
5. 画出**一次 iteration 内**的函数流程图



### 1.2 各案例的 agent 数量与角色


| 模型                           | agent 数/类 | 角色                                                        |
| ---------------------------- | --------- | --------------------------------------------------------- |
| Fox-Rabbit（教学，p.71-84）       | 2 类       | Fox（chase / check survival）、Rabbit（dodge / post location） |
| Sugarscape（p.96-97）          | 2 类 + 1   | Citizen、**Sugar**、Averager                                |
| 社会网络（p.110）                  | **1 类**   | Actor（1000 个，靠异质 memory 区分；跑 30,000 iteration 才稳定）        |
| 人群/行人（p.115-116）             | 3 类       | Person、**Generator**、**Corridor**（墙体/路径信息）                |
| Cournot 经济（p.137-140）        | 3+1+1     | 3 个 Firm + **Demand_Price**（充当环境，算价格）+ Averager           |
| Virtual Mall（p.152, 156-158） | 4 类       | Mall、Person、**Environment**、**Message counter**           |
| EURACE 欧洲经济（p.248）           | **15 类**  | 完整经济体，GPU 版跑不动，只能上 HPC                                    |
| 蚂蚁（p.203-209）                | 6 类       | Ant、Pheromone、Generator、FoodGenerator、Nest、Food           |
| 癌症用药（p.226-229）              | 4 类       | Cell、DrugA、DrugB、**DrugGenerator**                        |
| Drosophila 胚胎（p.190）         | 3 类       | Source、Protein、Compartment（100 个隔室）                       |
| 医院 PatientFlow（p.277-278）    | 多类        | Patient / receptionist / nurse / doctor / 辅助资源            |


规模：单机 HPC 可跑到 **500,000 agents**（p.61）。

### 1.3 四个反复出现的设计模式（这部分对我们最有参考价值）

**① Generator agent —— 框架不能凭空造 agent** FLAME 里 agent 只能由**另一个 agent** 调 `add_X_agent()` 创建。所以几乎每个动态模型都专门养一个 generator：Pheromone Generator、FoodGenerator、DrugGenerator、人群 Generator。它读"请求消息"、去重、分配唯一 ID、再实例化（p.220-221 的 `produce()` 甚至要手工去重防止同坐标重复生成 pheromone）。

**② 环境必须被建模成一个中心 agent** FLAME **没有全局环境概念**——这是书里自己列的缺陷（§3.5 "Static global conditions", p.58）："agents behave in a world with no changing conditions… This requires a central agent to be programmed into the system if the model needs a world representation." 于是：Cournot 里的 `Demand_Price`、Mall 里的 `Environment`、行人里的 `Corridor`、蚂蚁里的 `Nest`，全是这个模式。Virtual Mall 更进一步，把**策略库和消息缓冲都塞进 Environment agent**，目的是"remove the communication dependency within the strategy gene of every agent, allowing free access for functions to be moved around"（p.152）——即解耦，让函数可重排。

**③ 被动实体也要建成 agent** Sugar、Food、Pheromone 本身不做决策，但仍是 agent。原因很简单：**只有 agent 能发消息**，不发消息就无法被别人感知。Sugar 的全部职责就两条：`post_location` 和 `check_eaten`（p.99）。

**④ Averager / collector agent** 专门订阅所有指标消息、做统计落盘，不污染业务 agent（Cournot、Mall 都有）。

## 2. 协调与通信机制



### 2.1 通信基元：message board，不是点对点

Libmboard（§3.4, p.54）。agent 把消息 **post 到公共 board**，所有 agent 从 board 读，**从不点对点投递**。理由直接写在书里：避免 N² 次单播，且便于跨节点打包。

API 形态（p.66-67, 77）：

```c
add_foxInformation_message(FOXX, FOXY);           // 写
msg = get_first_rabbitInformation_message();      // 读
while(msg) { ...; msg = get_next_..._message(msg); }

```



### 2.2 同步点：整个机制的核心（§3.4.2, p.57-58, Fig 3.14）

Xparser 从模型描述**自动推导出函数依赖图**，把所有 agent 函数排成 **layers**（Mall 模型的 stategraph Fig 6.22 有 16 层）。规则是：

```
所有产生消息 M 的函数执行完
  → message board 上锁（synchronization point）
  → 全部写入完成
  → 解锁
  → 所有消费 M 的函数才被调度执行

```

带来的三个后果，书里说得很直白：

- **好处：结构性无死锁。** §3.4.2 列了死锁四条件，同步点从模型描述层面就排除了它们。
- **代价 A：一个 iteration 内 agent 不能改主意。** "This allows all agents to follow particular plans and cannot change their behavior during a time step."（p.57）要改，只能加 rule database 或 flag，并且同步点得围着这些 choice function 重新排。
- **代价 B：emergence 被抑制。** §3.5（p.59）承认："The agents have pre-knowledge of what to do and makes it impossible for them to learn and change their behavior. This prevents emergence to occur at lower levels."



### 2.3 时间驱动 vs 事件驱动

FLAME = **time-driven + synchronous update**（所有 agent 同时刻更新、并行）；SWARM = event-driven（任一 agent 动作就更新环境）。异步更新（agent 按各自内部时钟或随机序）FLAME 不支持（p.29）。

### 2.4 三层通信优化

**① Board 层过滤（filters + iterators, Fig 3.12, p.56 / §6.3.2, p.150）** 过滤条件写在 XML 里，C 代码一个字不改，但省掉大量遍历：

```xml
<input><messageName>strategies_for_firm</messageName>
  <filter><lhs>a.id</lhs><op>EQ</op><rhs>m.firm_id</rhs></filter>
</input>

```

另有 `message_range` 做空间范围过滤，建立"局部社交圈"。

**② 三种消息生命周期（p.68）**


| 类型        | 语义           | 例子                  |
| --------- | ------------ | ------------------- |
| Immediate | 读完即删         | "兔子被吃"、"职位已满"       |
| Counter   | 存活若干步、被所有人读  | 价格、成本               |
| Handshake | 读旧消息 → 生成新消息 | application → hired |


**③ Iterator 必须随机化（p.68）** `MB_Iterator_Create` 之后要随机化，否则 agent 永远偏向 board 里靠前的消息，结果系统性有偏。

### 2.5 并行与放置：通信开销是主导因素

MPI + SPMD，分布式 message board 定期同步（Fig 3.11）。两种 partitioning：**geometric**（按 agent 的 x,y 空间位置分）vs **round-robin**（按 agent 编号轮转）。

实测结论（§8.4, p.244-245，Fig 8.4）：

- **Epithelium 模型**：round-robin 全面优于 geometric；geometric 到 16 节点还可以，**32 节点时因 agent 间距离拉大、跨节点消息暴涨而显著变慢**。
- **Sugarscape**：agent 总数完全相同（21,020），**只改初始空间分布**，仿真时间就变了——random 分布最快（通信落在同一 processor 内），separate areas 最慢（被迫跨 processor）。
- 结论原文："messaging between agents is a key factor for simulation times… How the agents are initially distributed influences their communications being either locally on the same processor or across nodes."

Table 3.1 / Fig 3.13（p.56）给了 EURACE 在三个平台上 2→16 processor 的每 iteration 时间：Hector 单调下降 29.8→21.7s，而 HAPU 在 34.6~92.3s 之间剧烈抖动，完全不 scale。

## 3. 对我们（SciNet）的三点直接关联

我把这部分单列，且明确标注是**我的判断，不是书里的结论**：

1. **同步点 = 一个 BSP/barrier 模型。** 跨机构 workflow 协调若照搬这个语义，好处是可静态验证无死锁，坏处是每轮受最慢参与方支配（尾延迟）——这正好是我们关心的可靠性/韧性问题的一个具体形态。
2. **geometric vs round-robin partitioning ≈ "通信感知的 agent 放置"。** 书里的实测（同样 agent 数、只改分布就改变仿真时间）是"放置策略决定跨节点流量"的一个干净证据，可以作为我们做 science-aware routing / placement 时的类比参照或对照基线。
3. **FLAME 的四条缺陷（§3.5, p.58-59）对做 network digital twin 是硬限制**：无全局环境、agent 不能学习/自适应、假设完美理性与完美信息、**没有网络拓扑概念**（"FLAME models are independent agents with no links between them. FLAME does not create neighborhoods, unless specified"）。如果合作方的 twin 是 FLAME 系的，这四条要提前确认。

---

# 最近系统和机器学习顶会（OSDI、NSDI、SOSP、ICML、MLSYS, ....），有无能够给我们项目提供帮助的、关于agent之间通信的论文

## Codex:

有，而且 2025–2026 年已经出现一批非常贴近 SciNet 的论文。但需要区分两种“agent 通信”：

- ML 视角：agent 应该和谁通信、发送什么、通信几轮。
- 系统视角：消息怎样可靠传递、如何异步调度、失败怎样恢复、动作怎样经过 policy/NDT 验证。

对 UCR 的 Task 3，第二类通常更重要。

### 最值得优先读的六篇


| 优先级 | 论文                                                                                                                                          | 解决的问题                                                                   | 对 SciNet 的直接启发                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 1   | [Murakkab, OSDI 2026](https://www.usenix.org/conference/osdi26/presentation/chaudhry)                                                       | 用声明式表示描述 agentic workflow，将逻辑与模型、硬件配置解耦；runtime 根据 SLO 动态重配置            | 几乎就是 SciNet Flow Engine 的系统参照：把 workflow intent、agent DAG、SLA 和底层资源分开     |
| 2   | [AIOpsLab, MLSys 2025](https://proceedings.mlsys.org/paper_files/paper/2025/hash/d1f9e4a9f109b6e8b75ed362736f22ec-Abstract-Conference.html) | 提出 Agent–Cloud Interface，连接 agent、telemetry、故障注入、动态环境和评价器               | 最接近 UCR 的 Agent–NDT–monitoring integration；可以直接参考其 interface/testbed 组织方式 |
| 3   | [G-Designer, ICML 2025](https://proceedings.mlr.press/v267/zhang25cu.html)                                                                  | 根据任务动态选择 multi-agent 通信拓扑，避免所有 agent 全连接                                | SciNet 可以根据 workflow、故障和网络状态动态决定 planner、route、security、NDT agents 的通信关系  |
| 4   | [Agentix, NSDI 2026](https://www.usenix.org/conference/nsdi26/presentation/luo)                                                             | 将整个 agent program 而非单个 LLM request 作为调度单位，识别调用依赖和 head-of-line blocking | Flow Engine 不应只调度孤立消息，而应看到完整 workflow/agent dependency graph              |
| 5   | [Picsou, OSDI 2025](https://www.usenix.org/conference/osdi25/presentation/frank)                                                            | 两个跨集群 replicated state machines 怎样在失败下高效、一致地通信                          | 虽然不是 AI agent 论文，但很适合思考跨机构 agent 的 ACK、重传、去重、恢复和一致状态                      |
| 6   | [ShieldAgent, ICML 2025](https://proceedings.mlr.press/v267/chen25ae.html)                                                                  | 用独立 guardrail agent 检查另一个 agent 的完整 action trajectory 是否符合显式 policy     | 在网络配置进入 NDT/真实硬件前增加 policy agent，而不是依赖 planner 自己保证安全                     |


其中我认为应最先精读的是 **Murakkab、AIOpsLab 和 G-Designer**。

### 其他有价值的论文

- [Parrot, OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/lin-chaofan)：用 Semantic Variable 显式表达多个 LLM 调用之间的数据流。启发是 agent 不应只交换自由文本，而应交换具有类型和依赖关系的 artifact。
- [AI Metropolis, MLSys 2025](https://proceedings.mlsys.org/paper_files/paper/2025/hash/4f31327e046913c7238d5b671f5d820e-Abstract-Conference.html)：跟踪 agent 之间的真实依赖，允许 out-of-order execution，避免全局同步造成的假依赖。适合 NDT scenario 并行测试和动态 workflow branching。
- [FlashInfer-Bench, MLSys 2026](https://proceedings.mlsys.org/paper_files/paper/2026/hash/37e44c4b5321605735be9761f9b758fc-Abstract-Conference.html)：通过统一 schema 表示 workload、implementation 和 evaluation，形成 agent 生成—测试—验证—部署闭环。它虽然是 GPU kernel 场景，但“统一 trace/schema + 安全部署”的模式与 SciNet 很接近。
- [Fine-Tuning Language Models Using Formal Methods Feedback, MLSys 2024](https://proceedings.mlsys.org/paper_files/paper/2024/hash/b0131b6ee02a00b03fc3320176fec8f5-Abstract-Conference.html)：在抽象 world model 或高保真 simulator 中验证 agent 产生的 controller。这就是“Agent 提方案 → NDT 验证 → 反馈 agent”的标准闭环参照。
- [Communicating Activations Between Language Model Agents, ICML 2025](https://proceedings.mlr.press/v267/ramesh25a.html)：让模型通过内部 activation 而非自然语言通信，计算量低于自然语言通信的四分之一。它是最直接的 agent communication 论文，但对 SciNet 的异构、跨站 agent 不太实用，因为要求访问模型内部表示并紧密耦合模型实现。
- [Multi-agent Architecture Search via Agentic Supernet, ICML 2025](https://proceedings.mlr.press/v267/zhang25bi.html)：针对不同任务动态选择 agent 数量、LLM/tool calls 和协作结构。适合思考“不是所有 workflow 都启动全部 agents”。

最近 SOSP 主会中，我没有找到比上述论文更直接的 agent communication 工作；不应为了凑会议而把一般分布式系统论文强行称为 agent 论文。

### 把这些论文放进 SciNet 架构

它们正好可以拼成下面六层：

```
Workflow intent / Science SLA
              │
              ▼
1. 选择 agent 及通信拓扑
   G-Designer / MaAS
              │
              ▼
2. 显式描述消息、数据和依赖
   Parrot / FlashInfer Trace
              │
              ▼
3. workflow-aware 调度与异步执行
   Murakkab / Agentix / AI Metropolis
              │
              ▼
4. 跨站可靠传递与状态恢复
   Picsou 一类 distributed-systems mechanism
              │
              ▼
5. policy、安全和动作验证
   ShieldAgent
              │
              ▼
6. NDT / telemetry / hardware interaction
   AIOpsLab + formal-methods simulator loop
```

这说明 UCR 需要关注的“agent 通信”不应只是：

```
{"message": "请测试这条路径"}
```

更合理的通信对象可能是：

```
workflow_id: hep-stage-103
sender_role: route_optimizer
receiver_role: ndt_validator
intent_version: 7
action:
  type: reserve_path
  source: BNL
  destination: NERSC
  bandwidth_gbps: 200
preconditions:
  telemetry_snapshot: ts-8821
deadline: 2026-08-03T14:00:00Z
ndt_scenario_id: scenario-41
idempotency_key: action-793
parent_event: plan-205
payload_ref: globus://dataset/...
policy_status: pending
```

bulk scientific data 不应放在 agent 消息里；消息只携带 intent、控制信息、状态和数据引用，实际数据走 SciNet/data-transfer plane。

### 现有论文留下的项目机会

在本轮检查的这些顶会论文中，没有一篇同时解决：

- 跨机构/WAN 环境；
- workflow intent 和 Science SLA；
- 动态 agent 通信拓扑；
- NDT 验证；
- monitoring feedback；
- hardware agent 控制；
- retry、去重、版本和 provenance；
- 多管理域 policy。

多数 ML 论文假设 agent 都在同一框架内，通过可靠的本地调用通信；多数系统论文又不理解 scientific workflow intent。

因此，一个很贴合 SciNet/UCR 的研究表述可能是：

> 面向跨机构科学 workflow，设计一个 WAN-aware、policy-enforced、NDT-validated 的 agent communication runtime。

它的核心研究对象不是“agent 聊天效果”，而是：

- 消息应该采用什么 typed schema；
- 谁应该和谁通信；
- 怎样根据 workflow SLA 和网络状态动态改变通信图；
- NDT 结果过期或 telemetry 更新时，如何检测 stale decision；
- WAN 失败后如何 retry 而不重复执行硬件操作；
- 如何保留完整的 decision/action provenance。



## Claude:

搜完了。先说结论：**有，而且有一篇几乎是为你们的场景写的**（Cortex, NSDI '26）。但整体上，"agent 间通信"在顶会里目前被切成了三个互不相通的块，没人从科学网络的角度把它们串起来——这个缺口本身对你们有意义。

先标注可信度，免得引用踩坑：

- ✅ **已从官方页面核实**：SIGCOMM 2026 accepted list、Cortex 与 Agentix 的 USENIX 页面、KVCOMM 的 arXiv/OpenReview
- ⚠️ **仅来自第三方整理页 / 搜索摘要，引用前须核对原文**：其余 NSDI '26 / OSDI '26 / ICML 2026 篇目
- USENIX 官方的 NSDI '26 accepted-papers 页对我返回 403，所以那份清单我是从第三方笔记站拿的

### Tier 1：直接对口"跨机构 workflow 协调"

#### ⭐ Cortex — NSDI '26（最该读的一篇）

**Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching**（NUS / USTC / Toronto / Sea AI Lab，arXiv 2509.17360）

它的问题设定几乎就是你们的问题设定：

> agent 模型和知识/数据源**位于不同 datacenter 或 region，之间隔着 WAN**；agentic 应用靠 MCP 协议或通用 RPC 跨广域网取数据 → 两个后果：**跨区延迟** + **金钱成本**。

做法：给 agent 的 remote tool call 建跨区缓存。两个抽象——Semantic Element（query 的 embedding + 延迟/成本/静态性等**性能感知元数据**）和 Seri（两级检索：向量索引粗筛 + 轻量 LLM judger 精验）。再配语义感知的 cache hit 定义、成本感知淘汰策略、主动预取。结果：search workload 上 hit rate >85%、吞吐 3.6×，coding 任务 +20%。

**为什么对你们关键**：这是我搜到的唯一一篇把"agent 之间/agent 与远端数据源之间的通信"当作**一等网络问题**来测量和优化的顶会论文。它的指标口径（跨区延迟、cache hit rate、每次 tool call 的成本）可以近乎一比一映射到你们的跨机构场景——而这正是你们现在缺的"可测的东西"。

#### Agentix — NSDI '26

**Agentix: An Efficient Serving Engine for LLM Agents as General Programs**（Luo et al.；即 Autellix arXiv 2502.13965 的会议版，改了名）

把 agent program 当**一等调度实体**，拦截 program 发出的 LLM call，把 program-level context 喂给调度器，按"该 program 已完成的调用"来抢占和排优先级。单线程 / 分布式两套算法。同延迟下吞吐比 vLLM 高 4–15×。

核心诊断是 **head-of-line blocking 同时发生在单个请求层和 program 层**。这个"两层队头阻塞"的框架，换到网络上就是流级 vs workflow 级的排队——跟你们的 science-aware 调度是同构问题。

#### 科学设施侧的 agentic 讨论（不是顶会正会，但最对口你们的项目定位）

- **The (R)evolution of Scientific Workflows in the Agentic AI Era: Towards Autonomous Science**（SC'25 Workshops, arXiv 2509.09915）
- **AGENT4SC 2026**（1st Workshop on Agentic AI for Large-scale Science）、**A2SD-2026**、**Agentic AI for User Facilities: Workshop Report**

这些直接讲：agent 要**跨设施移动 PB 级数据、触发 实验↔计算 co-scheduling、经 ESnet 协调**；并点名了几个空白——**长时间跨设施 workflow 的认证/授权（持久身份、受限权限、可审计访问）**、调度可见性、能耗核算、可复现性保证。

如果你们要写 Phase 2 proposal，这几份是现成的"问题合法性"背书。

### Tier 2：agent 间通信的真实载荷是什么

这一块的共同发现很重要：**多 agent 之间传的其实不是文本，而是 KV cache / latent 状态**——那就变成了带宽问题。


| 论文                                                                                                                       | 核心                                                                                                                                                       | 数字                                 |
| ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **KVCOMM**（NeurIPS 2025, arXiv 2510.12872）                                                                               | agent 收到上游消息要**从头 reprocess 全部 context**；KV cache 在单 agent 有效但多 agent 因前缀发散不能直接复用（"offset variance problem"）。提出共享 KV-cache 复用 + context-aware offsetting | 三 agent、单 H100，prefill 平均 **6.7×** |
| **DroidSpeak**（NSDI '26，⚠️待核对）                                                                                           | 首个让 **KV cache 跨分布式节点、跨不同 LLM 复用**的分布式推理系统（架构相同即可）。动机明写：agentic 系统里多个专用 LLM 按用户/任务/角色协作                                                                  | —                                  |
| **Beyond Tokens: A Unified Framework for Latent Communication in LLM-based Multi-Agent Systems**（arXiv 2606.05711，⚠️待核对） | 传 KV cache 让下游 agent 跳过 prefill 直接解码，省算力；但要交换**高维 latent 变量**，通信开销非平凡                                                                                    | 明确指出这是**算力 vs 通信的 trade-off**      |


**这一条对你们最有价值**：如果多 agent 科学 workflow 的 agent 间流量从"几 KB 文本"变成"几百 MB KV cache / latent"，那么"跨机构 agent 通信"就不再是控制面问题，而是**数据面问题**——直接落在你们的 GPU-to-GPU 传输和 science-aware routing 上。这是一个可以做测量、可以出数字的切口。

### Tier 3：GPU 集合通信（对口你们的传输模块）

SIGCOMM '26（✅ 官方列表）：

- **Connecting 100K+ GPUs: Building the Communication Stack for Large-Scale LLM Training**
- **ZipCCL** — 集合通信的无损压缩
- **OptCCL** — 最优集合通信算法的可扩展综合
- **UBEP** — 重构生产 superpod 的专家并行通信库
- **PReCCL** — **带内遥测 + 工作负载重分配** 做 performant & resilient 集合通信 ← 这篇跟你们"可靠性与韧性"最对口
- **DualPath** — 通过 disaggregated KV-cache 存储 I/O 加速 agentic LLM 推理
- **Connex** — 动态 LLM serving 的端点移动性原语

NSDI '26（⚠️待核对）：**FAST**（异构 GPU 集群 All-to-All 调度）、**HeteCCL**、**ForestColl**（任意网络拓扑的吞吐最优集合通信）

### Tier 4 & 5：概念参考（不建议现在深读）

**ML 侧的通信协议学习**（⚠️均待核对）：Bandwidth-Efficient Multi-Agent Communication through Information Bottleneck and Vector Quantization（arXiv 2602.02035，宣称带宽降 41.4%）、HieraMAS（intra-node LLM mixture + inter-node topology 联合优化）。有人维护了 [ICML 2026 agent 论文阅读清单](https://github.com/jiaxianyan/icml-2026-agent-papers)。

**OSDI '26 编排侧**（⚠️待核对）：**Murakkab**（agentic workflow 编排，联合优化 accuracy/latency/energy/cost）、**OpenTela**（把碎片化 HPC 集群统一成容错的异构 LLM serving 平台——跨机构味道最重的一篇）、Weave / RollArt / DynaRL / RLinf（agentic RL 的跨集群调度）。

### 我搜到的一个空白

**我没有找到**任何一篇把"多 agent 科学 workflow 在广域科学网络上产生的流量"作为**测量对象**的论文。现有工作要么在单集群内优化 KV cache（Tier 2），要么在 datacenter 内优化集合通信（Tier 3），要么把 WAN 当作要绕开的黑箱去做缓存（Cortex）。**没人去刻画这个流量长什么样。**

必须说清楚：这是"我几轮搜索没找到"，不是"不存在"。但如果成立，这正好落在 SciNet 的定位上，而且是个能在 Phase 1 六个月内出结果的形态。

### 建议的下一步（一个）

**精读 Cortex（arXiv 2509.17360），并只做一件事：把它的问题设定和指标口径，逐条对照你们的跨机构场景，列出"哪些直接成立、哪些不成立"。**

理由：你们现在的首要任务是把"要解决什么问题"收敛成一个可测的假设。Cortex 已经替你们验证了"agent 跨 WAN 通信是真问题"并给出了一套可复用的度量方式（跨区延迟 / hit rate / 每调用成本）；而它与你们的差异点——它面向商业云的 region 间，你们面向科学设施间；它优化的是 tool call 的**控制面**，你们关心的可能是 KV cache 级别的**数据面**——很可能就是你们的切入口所在。

读完再决定要不要往 Tier 2 展开。我没有往 `resources/` 或 `docs/` 写任何东西。

**Sources:**

- [Cortex: Achieving Low-Latency, Cost-Efficient Remote Data Access For LLM via Semantic-Aware Knowledge Caching (USENIX)](https://www.usenix.org/conference/nsdi26/presentation/ruan-cortex)
- [Cortex (arXiv 2509.17360)](https://arxiv.org/abs/2509.17360)
- [Agentix: An Efficient Serving Engine for LLM Agents as General Programs (USENIX)](https://www.usenix.org/conference/nsdi26/presentation/luo)
- [Autellix (arXiv 2502.13965) — Agentix 的预印本](https://arxiv.org/abs/2502.13965)
- [KVCOMM: Online Cross-context KV-cache Communication for Efficient LLM-based Multi-agent Systems (arXiv 2510.12872)](https://arxiv.org/abs/2510.12872)
- [KVCOMM (OpenReview)](https://openreview.net/forum?id=yGOytgjurF)
- [ACM SIGCOMM 2026 Accepted Papers](https://conferences.sigcomm.org/sigcomm/2026/accepted/)
- [NSDI '26 Spring Accepted Papers (USENIX)](https://www.usenix.org/conference/nsdi26/spring-accepted-papers)
- [NSDI 2026 论文整理（第三方）](https://paper.lingyunyang.com/reading-notes/conference/nsdi-2026)
- [OSDI 2026 论文整理（第三方）](https://paper.lingyunyang.com/reading-notes/conference/osdi-2026)
- [The (R)evolution of Scientific Workflows in the Agentic AI Era (arXiv 2509.09915)](https://arxiv.org/pdf/2509.09915)
- [AGENT4SC 2026 — 1st Workshop on Agentic AI for Large-scale Science](https://agent4sc.github.io/)
- [A2SD-2026 Workshop](https://autonomousscience.org/workshops/a2sd-2026/)
- [Agentic AI for User Facilities: Workshop Report](https://www.tandfonline.com/doi/full/10.1080/08940886.2026.2649097)
- [Beyond Tokens: A Unified Framework for Latent Communication in LLM-based Multi-Agent Systems (arXiv 2606.05711)](https://arxiv.org/html/2606.05711v3)
- [Bandwidth-Efficient Multi-Agent Communication through Information Bottleneck and Vector Quantization (arXiv 2602.02035)](https://arxiv.org/pdf/2602.02035)
- [ICML 2026 agent 论文阅读清单](https://github.com/jiaxianyan/icml-2026-agent-papers)
- [The 3rd Workshop on Networks for AI Computing (NAIC), SIGCOMM 2026](https://conferences.sigcomm.org/sigcomm/2026/naic/)



