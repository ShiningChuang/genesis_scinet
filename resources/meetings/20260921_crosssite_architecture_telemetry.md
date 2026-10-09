# 2026-09-21 组内会议：cross-site agent architecture 与 hierarchical telemetry

> **参会者**：KK、Linxuan Zhong、Sourabha
>
> **材料**：会议自动转写，以及 `[agent orchestration for cross-site.pptx](../slides/agent%20orchestration%20for%20cross-site.pptx)` 的六页内容。
>
> **分工**：Linxuan 讲第 1–3 页；Sourabha 讲第 4–6 页。
>
> **整理口径**：第一部分不复述 Linxuan 的汇报，只记录 KK 的评价和修改要求。第二部分记录 Sourabha 三页的内容及其与 KK 的讨论。转写没有说话人标签，本文结合汇报分工、称呼和上下文判断发言归属；无法确认的细节标为待核实。

## 核心摘要

KK 基本认可这套 cross-site 分层，但要求把它画成一个明确的**逻辑集中式全局系统**：Scheduling、Compute、Instrument、Network Agents 构成中央组件，与各站点的 Site Agent / local network component 协调。短期不应尝试让所有站点 agents 通过新协议完全分布式地重建全局调度功能。

他对前三页提出的主要修改是：每个 site 可能同时拥有 compute、instrument、storage 和 network，不应把站点画成互斥资源类型；Site Agent 内应明确 local scheduler、instrument controller、storage management 和 network-facing component；Compute / Instrument offers 必须包含实际资源与数据生成特征；Telemetry Service 只负责测量、监控和确定性汇总，offers 直接在 resource agents 与 Scheduling Agent 之间传递。

Sourabha 提出的 hierarchical telemetry 分为 local detail、site telemetry transformation 和 normalized global state。KK接受“原始高频细节留在本地、全局只看 decision-relevant summary”的方向，但要求删掉不必要的 publish/subscribe 设计：Site Agent 应先消费本站告警并尝试恢复，只有本地无法处理时才逐层上报。他还要求 attribution 图明确区分 local 与 central，并将最后的 compute-node failure 示例改成 network-link failure，使工作范围聚焦网络。

## 第一部分：KK 对 Linxuan 第 1–3 页的反馈



### 1. 总体方向可行，但 central 与 site 的部署关系必须画清

KK 一开始指出，他尚不清楚中央组件实际运行在哪里，以及它们如何与 individual Site Agents 协调。讨论后，他给出的短期方向是：

- Scheduling、Compute、Instrument、Network Agen；
- 这个中央系统应当真实运行在某个系统或服务器上，而不是只存在于概念图中；
- 中央 Scheduling Agent 和中央 Network Agent 分别负责全局调度与跨站网络协调；
- Site Agents 负责本站接口和执行；
- WMS 同样先按中央实体理解，不考虑每个站点各部署一个 WMS 再互相协调。

KK 不支持 Phase 1 直接采用完全分布式架构。让所有 Site Agents 通过新协议共同实现全局 scheduling、compute 和 network coordination 会显著增加复杂度，短期难以合理完成。

#### 修改要求

- 在图中用一个外框明确圈出 logically centralized / global agent system。
- 明确中央组件与 participating sites 的边界。
- 不要让读者误解为几个 global agents 任意分散部署、再靠未定义协议形成全局决策。



### 2. 各站点不是互斥资源类型

KK 纠正了图中可能产生的理解：Site A 不一定只有 compute，Site B 也不一定只有 instrument。一个站点可以同时拥有：

- compute；
- instruments；
- storage；
- DTNs 与 network endpoints；
- 对应的 scheduler、controller 和 management components。

图中的 “Site Agent A with compute resources” 和 “Site Agent B with instrument resources” 只能作为例子，不能暗示站点必须按资源类型划分。

#### 修改要求

- 在图或讲述中明确说明这些是 examples。
- Site Agent 框内应表达本站可以同时包含多类资源。



### 3. Site Agent 内应明确四类本地组件

KK认为每个 participating site 至少要表达以下本地能力：

1. compute 的 job scheduler；
2. instrument controller；
3. storage management；
4. 与网络相关的 local component / interface。

其中前三项分别管理本站计算、仪器和存储。网络部分的名称与实现仍需确认：它可能是 Site Agent 内的 network adapter，也可能是 local network agent，与中央 Network Agent 协调。

KK倾向让中央 Network Agent 控制 SENSE 侧的端到端 virtual circuit provisioning；Site Agent 本身未必直接调用 SENSE。各站点仍需一个本地 network-facing component，用于提供 endpoint、能力、策略和状态，并与中央 Network Agent 交互。

#### 未解决

- 本地 network component 是否应称为 local Network Agent；
- 它与 Site-RM、SENSE Orchestrator 和中央 Network Agent 的确切调用关系；
- 哪些网络故障可由本站透明恢复，哪些必须经中央 Network Agent。



### 4. Resource agents 通过 Scheduling Agent 协调

KK追问 Compute、Instrument 和 Network Agents 是否彼此直接通信。Linxuan解释，当前设计让它们都通过 Scheduling Agent 协调，不建立横向 agent-to-agent 依赖。KK接受了这一解释。

当前逻辑是：

```text
Compute Agent ─────┐
Instrument Agent ──┼── Scheduling Agent
Network Agent ─────┘
```

Scheduling Agent 持有完整 workflow dependency，并把一个资源的 offer 转换成另一个资源的新 requirement。Resource agents 各自负责本领域资源，不需要理解完整 DAG。

### 5. Telemetry Service 不应传递 offers 或作资源决策

KK最初追问为什么 Scheduling Agent 不再直接连接 Telemetry Service，并要求回看上一版架构。讨论中出现了“Network Agent 把 offers 放进 telemetry，再由 Scheduling Agent 获取”的解释，KK明确否定：

- network / compute / instrument offers 应直接发送给 Scheduling Agent；
- Telemetry Service 是 measurement and monitoring component；
- telemetry 可以存储测量结果，也可以做 averaging、smoothing、normalization 等确定性处理；
- 这些处理可以由普通程序或规则完成，不需要把 telemetry 设计成会决策的 agent；
- Telemetry Service 不应成为 resource agents 与 Scheduling Agent 之间的控制消息总线。

会议因此继续使用 **Telemetry Service**，而不是 Telemetry Agent。

运行事件如何到达 Scheduling Agent 的当前解释是：相应 resource agent 消费 telemetry，把底层事实转换成 `repaired`、`at_risk`、`delayed` 等语义事件，再报告 Scheduling Agent。Telemetry 与 Scheduling Agent 是否保留只读查询接口并未单独定稿，但业务主路径不应经 telemetry 传递 offers。

### 6. Compute Agent 的 offer 不能只写开始和结束时间

KK确认 Compute Agent 按 task 工作，并认可它比较不同站点的 queue time、earliest start、predicted runtime 和 finish time。对于 resource sharing 与 whole-node reservation，他将其理解为共享 service / resource 与 bare-metal 或整节点资源之间的区别。

他指出当前示例 offer 只写 `earliest_start` 和 `predicted_finish` 不够。Compute Agent 不应隐藏实际提供的资源，offer 还应说明：

- CPU 数量与类型；
- GPU 数量与类型；
- memory；
- 必需的软件环境或其他 task-specific resources；
- shared 还是 whole-node / reserved；
- offer 来自哪个 site。

中央 Compute Agent 收集多个 sites 的 offers，再交给 Scheduling Agent 选择；图中的 Compute Agent 不是某个 individual site 的 local component。

### 7. Instrument Agent 必须表达数据生成方式

KK接受 Instrument Agent 处理 instrument matching、reservation window、preparation、experiment runtime 与 facility policy 等条件，但指出数据输出不能只写最终 total size 和一个 `dataReadyAt`。

仪器可能边运行边产生并传输数据，因此 Instrument Agent 还应表达：

- 数据输出到哪里；
- total amount 是否固定；
- 数据是实验结束后一次性 ready，还是持续 streaming；
- streaming duration；
- 预计 data rate；
- 数据生成或 processing 的结束时间。

例如，`2 TB at 12:15` 与“40 分钟内持续以某一速率产生数据”会导致完全不同的 network requirement 和 compute earliest start。

#### 修改要求

- 将 slide 中只强调 `dataReadyAt + 2 TB` 的例子扩展为 `total size / duration / rate / destination`。
- 不要默认所有 instrument data 都在实验结束后一次性产生。



### 8. Compute 与 Instrument 可以复用统一资源协议

KK没有反对 Compute Agent 和 Instrument Agent 通过 Site Agents 使用相似的资源协商 verbs：

```text
request → offer → hold → commit → modify / release
```

但具体字段应按资源类型扩展。Compute offer 需要 compute quantity 与 environment；instrument offer 需要 preparation、run、data production 和 facility constraints。

### 9. Site Agent slide 的术语和表述需要修改



#### 9.1 DTN 与 network endpoint 要区分

KK追问 DTN 与 network endpoint 的区别。讨论中形成的解释是：

- DTN 是承担数据传输的 physical node；
- network endpoint 是对外可识别的 interface / address / name；
- endpoint 还应带 capability，例如接口能支持 1 Gbps、100 Gbps 或其他速率。

Site Agent 发布网络能力时，需要同时给出 **identity and capability**，不能只列一个 endpoint 名称。

#### 9.2 Site-RM 必须标明网络含义

KK看到 `Site-RM` 时无法直接判断它是什么，要求图中明确标注它属于 SENSE / network side，而不是另一种 compute controller。

应将其表达为类似：

```text
SENSE Site-RM / local network resource interface
```

具体 API 和控制边界仍需查证。

#### 9.3 Counter-offer 的语句要改清楚

原 slide 写 “counter-offers against local allocation, policy and live state”。KK认为 `against` 容易让人误解。

更准确的表达应是：

> Site Agent accepts, rejects, or returns a counter-offer to the central resource agent, based on local allocation, policy, and live state.

Counter-offer 的接收方是中央 Compute / Instrument / Network Agent；local allocation、policy 和 state 是 Site Agent 作出回应的依据。

#### 9.4 Local recovery 要加 “when possible”

KK接受 Site Agent 在不改变 global commitment 的前提下做本地恢复，例如替换本地机器。但并非所有故障都能本地解决，因此应明确写：

> recovers locally **when possible**, without changing the global commitment.

若恢复会改变完成时间、endpoint 或其他全局承诺，就必须升级到 global agent。

## 第二部分：Sourabha 第 4–6 页的内容及与 KK 的讨论



### Slide 4：Hierarchical telemetry



#### 1. Sourabha 提出的三层结构

Sourabha 将 telemetry 分成三层：

1. **Local resource domain**：保留精细、本地特有的状态；
2. **Site Telemetry Service**：完成关联、清洗、归一化和摘要；
3. **Global state + global agents**：使用跨站一致的 decision-relevant summaries。

本地层可保留：

- exact node ID、GPU ID 与 utilization；
- local scheduler 的 job ID、partition、QoS 和状态；
- instrument-specific 字段，例如 EPICS PV names；
- 本地单位和数据格式；
- task 到 local resource 的绑定。

这些细节主要供 Site Agent 或本站系统作快速判断，不必全部暴露给 global agents。

全局层只需要回答两类问题：

- 这个 site 能否满足请求的 commitment？
- 当前 end-to-end workflow plan 是否仍然可行？

例如，全局 Compute Agent 不需要知道具体 GPU 在 `node17`，只需知道某型号 GPU 有多少、何时可用、预计能否按时完成。

#### 2. Local-to-global transformation

Site Telemetry Service 的 transformation 包括：

- 把 local job ID 关联到 `workflow_id / task_id`；
- 把 transfer / service ID 关联到 workflow transfer；
- 统一 IDs、units、timestamps 与 freshness；
- 将原始状态变成可比较的跨站摘要；
- 从 progress 推导 ETA、health 或 feasibility；
- 保留本地双向查询：由 task 找 local job / resource，也能由 local job 找回 workflow task。

Sourabha用 GPU 为例说明：各站点可以保留具体节点与本地格式，但向全局层只发布 GPU type、count、memory 和 available time window。

#### 3. KK 对 publish/subscribe 的质疑

Sourabha原本提出 Site Telemetry Service 根据规则发布 threshold events，Site Agent 与 global agents 订阅。KK认为这一设计可能过度：

- Site Agent 本来就负责本站状态；
- 本地 telemetry 发现问题后，应先交给 Site Agent；
- Site Agent 能本地修复就无需让所有 global agents 订阅；
- 不能本地处理时，再由 Site Agent 报告相应 global resource agent；
- global resource agent 仍无法维持 commitment 时，再升级给 Scheduling Agent。

因此不需要先设计通用 namespace 和复杂 pub/sub，除非以后确实出现多个独立消费者订阅同一事件的需求。

#### 4. Drill-down 目前只是候选能力

Sourabha提出 global agent 在必要时可 drill down，查询某个 site 的具体 nodes、competing jobs 或替代资源。KK认为这还属于推测：需要先有实现和具体例子，才能判断 drill-down 是否真正有用。

当前应先确定全局摘要的最小字段，不必提前设计所有细粒度查询。

### Slide 5：把 raw telemetry 关联到 workflow



#### 1. Compute attribution

Sourabha提出以下映射链：

```text
workflow run
  → task
  → local scheduler job ID
  → allocated nodes / GPUs
  → node and GPU telemetry
  → task-level utilization / ETA / health
```

映射需要支持双向查询：

- 给定 workflow task，找到它正在使用的 local jobs 和 resources；
- 给定 local job 或 node activity，找出它属于哪个 workflow / task。

这使 Site Agent 能判断某个本地故障影响哪个 task，并为 local recovery 查找满足相同要求的替代资源。

#### 2. Transfer attribution

Sourabha提出与 compute 对称的 transfer mapping：

```text
workflow
  → transfer task
  → transfer-tool record / transfer ID
  → network commitment or SENSE service
  → path / links / measured telemetry
```

目标是把 link utilization 或 link failure 对应到具体 workflow transfers，而不是只知道某条链路拥塞。

#### 3. KK 要求明确区分 local 与 central

KK指出 slide 没有清楚表示哪些 IDs 和 mappings 属于 central / global，哪些只存在于某个 site。修改时应对两类信息使用不同背景、边界或标签。

大致边界是：

- workflow DAG、global task / transfer IDs 属于 global；
- local scheduler job ID、具体 nodes / GPUs 和本地 transfer-tool record 属于 local；
- commitment / SENSE service 的归属与映射需要重新核对。

KK反复要求先在设计者脑中明确 global/local，再修改图，而不是只调整文字位置。

#### 4. 先讲 generic mapping，再给工具实例

Sourabha用 Rucio、FTS、Globus 和 SENSE 的已有工作作例子。KK认为 slide 应先解释一般问题：

> 一次 file transfer 有 transfer ID、source endpoint 和 destination endpoint；系统需要把该 transfer 与 workflow 和 network service 关联起来。

然后再说明具体实现中使用 FTS、Globus、Rucio–SENSE 或 DMM。不能直接写 `Globus ID` 而不解释它表示 transfer-tool record。

#### 5. Exact path / link mapping 尚未从 SENSE API 获得

Sourabha说明，当前 SENSE API 似乎没有直接提供某个 service 实际使用的完整 link sequence。Slide 中 `service → [L1, L2, L3]` 属于设计设想，不是已确认能力。

KK追问为何需要这项信息。Sourabha的理由是：只有知道 service 使用了哪些 links，链路故障时才能识别受影响的 transfers，并把利用率归因到 workflow。

会议没有决定一定扩展 SENSE API。需要先核实：

- 现有 SENSE / Site-RM 是否已有等价映射；
- link-level path 对恢复是否确实必要；
- 若缺失，是扩展 API，还是另外建立 mapping service。



### Slide 6：Alert 与局部恢复



#### 1. Sourabha 原来的 compute failure 示例

原 slide 用 compute node failure 说明：Site Agent 发现 `node17` 故障，定位受影响 task，尝试迁移或重启；如果新 ETA 仍满足 commitment，就报告 `repaired`；否则发送带原因、ETA、confidence 和 age 的 `at_risk`，由 global scheduler 重排。

该流程表达了 hierarchical escalation：

```text
detect locally
  → repair locally when possible
  → report repaired if commitment still holds
  → otherwise escalate at_risk
  → global replan
```



#### 2. KK 要求换成 network-link failure

KK认为 compute-node example 虽然简单，但会让项目看起来同时负责所有资源 agent 的具体实现。他要求团队逐渐明确“我们做什么、其他人做什么”，避免暗示本组会实现所有资源管理能力。

他建议把 Slide 6 改为 network-link failure：

- 某个 local network interface 或 link 失败；
- local network component / Site Agent 先判断能否切换接口或本地恢复；
- 如果恢复对中央 Network Agent 透明且原 commitment 仍成立，只报告 `repaired`；
- 如果本地无法恢复，再通知中央 Network Agent；
- 中央 Network Agent 根据 SENSE / NDT 能力重新 quote、hold 或 modify path；
- 若网络 commitment 仍无法满足，再由 Scheduling Agent 进行 workflow-level replan。

这个例子更符合团队当前以 network orchestration 为主要研究范围的定位。

#### 3. 本地与中央谁调用 SENSE 尚未确定

Sourabha追问：local network component 应直接调用 SENSE，还是先通知 central Network Agent，再由中央 Network Agent 调用 SENSE？KK认为现在还无法决定，必须先了解：

- SENSE 的实际 APIs；
- Site-RM 和 Orchestrator 的控制边界；
- 真实 network infrastructure 是否允许本站独立切换接口或路径；
- 哪些修复动作由 local node 完成，哪些必须由 central controller 完成。

暂时可采用的假设是：

> local component 先做能够保持原 commitment 的本地恢复；若无法恢复，再通知 central Network Agent。



#### 4. 不要让所有本地事件都上报中央

KK强调，并非每个 network event 都需要进入 central Network Agent。局部波动若已被 Site Agent 吸收，中央只需知道承诺仍成立，或者收到简化的 `repaired` 通知。只有影响 commitment 的事件才需要携带 impact 上报。

这一点与 slide 的标题 “escalate impact, not noise” 一致。

#### 5. 现阶段不要继续过度设计

KK在结尾指出，目前不少内容仍是 speculation。团队尚未充分了解 SENSE、ESnet 和 network digital twin 的真实接口，因此不应继续把所有细节设计到很深。

近期应使用现有架构和修改后的 network failure example，进一步确认：

- NDT / SENSE 能提供哪些状态和控制动作；
- local recovery 与 central recovery 的边界；
- 最小可运行的 telemetry-to-repair 闭环。



## 本次明确的修改清单


| Slide | 修改                                                                                                                                                                                         |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1     | 用外框标出 logically centralized global agent system；明确 global 与 participating sites；站点资源类型只是 examples；Site Agent 内补齐 compute scheduler、instrument controller、storage manager、network component |
| 1     | 不让 Telemetry Service 承载 offers；resource agents 直接与 Scheduling Agent 交换 offers 与运行语义事件                                                                                                      |
| 2     | Compute offer 增加 CPU / GPU / memory / environment / sharing mode；Instrument offer 增加 destination、total size、duration 与 streaming rate                                                      |
| 3     | 明确 DTN、network endpoint identity 和 capability；给 Site-RM 加 SENSE / network 说明；重写 counter-offer 语句；local recovery 加 `when possible`                                                          |
| 4     | 保留 local detail 与 normalized global summary 的层次；删除或弱化不必要的通用 pub/sub；由 Site Agent 先处理本地 alert，再逐层升级                                                                                         |
| 5     | 图上明确标出 local 与 central；先讲 generic transfer mapping，再给 Rucio / FTS / Globus / SENSE 实例；重新核对 commitment 和 exact-path mapping                                                                 |
| 6     | 将 compute-node failure 改成 network-link / interface failure；明确 local repair 成功与失败两条路径；避免暗示团队负责所有资源 agent                                                                                    |




## 后续动作

- Linxuan 按 KK 的意见修改第 1–3 页。
- Sourabha 修改第 4–6 页，重点重画 local/global boundary 和 network failure example。
- 核实 SENSE、Site-RM 与 Orchestrator 的真实接口，以及 service-to-path/link mapping 是否可获得。
- 核实 local network recovery 是否能透明完成，以及何时必须升级到 central Network Agent。
- 两人准备在次日上午 10:00 的会议上讲这六页。KK估计约 90% 可能会讲；若其他成员已有实质内容，则可先让其他人汇报。

