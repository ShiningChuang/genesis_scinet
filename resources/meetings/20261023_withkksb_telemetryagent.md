# 2026-10-23 与 KK、SB 的 Telemetry Agent 设计讨论

> **日期与参会者**：2026-10-23；Linxuan Zhong（用户）、KK、SB。日期依据用户“今天”的说明和指定文件名；参会者简称依据文件名及对话关系整理，不补全 SB 姓名。
>
> **材料与可靠性**：用户提供的英文自动转录，无时间戳及 speaker labels，术语、人名和部分句子有误识别。发言归属根据问答关系整理，未经回听确认。本文区分已明确的职责边界、获认可的能力方向与仍未定稿的接口细节；原文完整保留在附录 B。
>
> **关联记录**：本次继续审阅[前一天会后提出的 Telemetry Agent 设计](20261022_withsbafter.md)，并修正其中 WMS 注册上下文、workflow/transfer binding 等设想；Network Agent 背景见[前一天三人讨论](20261022_withkksb_networkagentv1.md)。旧记录保留其当时讨论口径。

## 核心摘要

KK 要求明确 Telemetry、Network 和 Scheduling Agents 的职责边界：**Telemetry Agent 不应维护 workflow、task、文件等应用级状态，也不应为了获取这些信息而直接连接 WMS。** 当前设计中，由 Network Agent 对接 telemetry；Network Agent 维护网络资源与传输的关联，Scheduling Agent 处理任务及 workflow 层的调度关系。

这不意味着 Telemetry Agent 只能返回未经处理的单链路数据。它可以保留测量历史，做单位标准化、平均和平滑，也应能提供 **end-to-end flow/path measurements**，例如延迟、RTT、flow completion time 和 throughput。Network Agent 可提供端点及所需的 flow 标识来请求跟踪；这与把整个 workflow/task 状态复制到 telemetry 不同。

告警与故障归因的分工尚未完全定下：可以让 telemetry 提供链路/类别指标及端到端 flow 指标，再由 Network Agent 推断问题；也可以利用 connection-oriented 网络已有的逐链路、逐 flow 信息，减少推断工作。KK 表示后一种路线可以采用，但未将其确定为唯一方案。

SB 表示将据此修改 Telemetry Agent 设计、移除 task facts 等应用层关联，再分享讨论。KK 还要求下次展示 Network Agent 的详细 slides，获取反馈后再决定向协作团队共享哪些材料。

## 一 当前由 Network Agent 对接 telemetry

SB 开始介绍包含四个组件的 Telemetry Agent 设计，讨论很快集中到 northbound API。转录没有完整列出另外三个组件，本文不补全组件清单。

KK 首先问：Scheduling Agent 是否需要直接访问 telemetry，还是所有查询和通知都通过 Network Agent？会上当前采用后者：Network Agent 获取链路等测量信息，再与 Scheduling Agent 交换 quote/offers，并报告故障或需要重调度的情况。

KK 表示将来可以再考虑其他访问需求，但目前不应无理由增加连接。这是**当前模块之间的接口安排**，并非已经规定所有未来调用方都永久只能通过 Network Agent。

## 二 移除 WMS → Telemetry 的 task facts / context 输入

### SB 原设计的理由

原设计让 WMS 调用 context registration，提供 workflow ID、transfer ID、计划数据量、起止站点和计划时间等信息。SB 希望 telemetry 由此建立 resource/link 与 transfers、workflows 的映射，支持按 transfer 或 workflow 查询状态、反查链路上的传输，也方便用户或管理员调查问题。

SB 解释，这些计划信息源自 WMS，因此原先考虑直接从源头接收。KK 认为“信息源自 WMS”本身不足以证明应建立这条接口。

### KK 的反对意见

KK 指出，WMS 的任务事实和 deadlines 应交给 Scheduling Agent，后者给出 execution plan；任务能否执行、如何执行取决于这一调度过程。Telemetry 不需要为了测量链路而理解完整任务和 workflow。

把 workflow/task 与网络资源的关联再放进 telemetry，会复制 Scheduling Agent、Network Agent 已经需要维护的状态。即使改成由 Scheduling Agent 向 telemetry 提交 task facts，也没有解决**为什么 telemetry 要拥有这份状态**的问题。

Linxuan 也认为目前不需要 WMS 直接向 telemetry 提供这些信息；SB 最终表示将修改设计，不再让 telemetry 维护 workflow/task 级映射。

**本次收敛的是取消这项职责，而不仅是把注册调用方从 WMS 换成另一个 agent。**

## 三 状态和关联应放在哪一层

KK 在讨论中表达的职责分层可整理如下；具体字段和数据库 schema 尚未定稿：

| 模块 | 本次讨论中的职责 |
| --- | --- |
| WMS | 提供 workflow/task 定义及输入需求，按调度结果执行；当前不直接向 telemetry 注册应用上下文 |
| Scheduling Agent | 处理任务序列、依赖和执行计划，维护任务与 workflow 的调度关系 |
| Network Agent | 关联传输与所用网络资源、路径/links，利用 telemetry 判断传输状态，处理局部修复或向 scheduler 报告风险 |
| Telemetry Agent | 获取和处理网络测量数据，提供链路、路径和端到端 flow 的观测及相应通知 |

KK 并未要求 telemetry 完全 stateless。它可以保留历史测量、计算平均值和平滑值，也可以为指定 flow 保存测量所需的跟踪状态；要求避免的是**将应用级 workflow/task 状态纳入 telemetry 的职责**。

## 四 链路指标之外，还需要端到端测量

### 标准化与聚合仍属于 telemetry 能力

SB 问，去掉应用级状态后是否只剩返回各链路原始数据。KK 澄清，telemetry 可以统一单位、平均、平滑，也可提供 site-level 或 path-level 的信息，前提是围绕实际测量对象，而不是逻辑任务结构。

### End-to-end latency 不能一般性地由逐链路平均值推出

Linxuan 说明，当前 Network Agent 主要按 link ID 查询，再在内部组合路径信息。KK 指出，这对某些指标可用，但不能一般性地把逐链路的延迟观测直接相加，就当作某次 flow 的真实端到端延迟。

KK 举例，希望测量一个包从 source 发出到 destination 收到的时间，也希望获得传输完成时间及吞吐。Network Agent 本身没有执行这些端到端测量，因而应向 Telemetry Agent 请求相应观测。

Linxuan 认可这一补充。**本次明确了测量需求，但未确定探测工具、观测方法、时钟要求或采样频率，也未验证现有实现已支持这些指标。**

### Network Agent 可请求跟踪指定 flow

KK 认可：Network Agent 可以告诉 telemetry“跟踪从 A 到 B 的这次传输，返回相关统计”。可以有某种 transfer/flow 标识，但该对象应处于网络传输层面，不要求 telemetry 理解文件名、应用 task 或整个 workflow。

这部分跟踪信息由 Network Agent 提供，而不是从 WMS 直接输入。只给 source/destination 是否足以区分并发 flows、最终使用何种 ID，本次未展开。

会上提到的目标观测包括：

- 端到端延迟、RTT 等时延信息。
- Flow completion time。
- Flow throughput。
- 链路层面的容量、利用率或状态等指标。

这些是讨论中的能力方向，尚未形成最终 response schema。

## 五 路径及 links 信息由谁提供

SB 问，telemetry 是否还应该返回 source 与 destination 之间使用的 links。

KK 的要求是：**实际 flow 所走路径及 links 的信息应能在 Network Agent 处获得**。可以由 Network Agent 可靠地从其他来源掌握，也可以从 telemetry 获得，具体选择留待实现时判断。

因此，本次没有规定 telemetry 必须负责路由发现，也没有确认“给定两个端点即可唯一确定路径”。需要区分计划使用的路径与实际 flow 所走的路径，最终接口尚未在会上定稿。

## 六 告警粒度与故障归因仍待细化

### SB 提出的问题

去掉 workflow/task 映射后，SB 问 telemetry 如何通知故障：是只报告 L2 这样的链路及阈值事件，还是必须指出哪次 transfer 受影响？Network Agent 是否应向 telemetry 注册阈值，例如某条链路可用容量低于指定值时通知？

KK 用不同流量类别得到不同服务的例子指出：链路整体状态变差，与某个 class / flow 的服务异常并不完全相同，需要考虑测量与告警粒度。

### 讨论的两种分工

| 路线 | Telemetry 提供的信息 | Network Agent 的工作 |
| --- | --- | --- |
| 依赖链路/类别观测和端到端 flow 测量 | Link/class-level 指标及 end-to-end flow statistics | 结合自己掌握的路径与传输关联，推断哪些 links 导致某个 flow 性能下降 |
| 利用 connection-oriented 网络已有的逐 flow 信息 | 在底层支持时提供逐链路、逐 flow 观测 | 减少定位受影响 flow 和问题链路所需的推断 |

KK 认为可以选择后一种，因为他观察到团队其他人较多按 connection-oriented 网络思考；同时明确表达了个人保留意见。**这属于允许采用的路线，不代表本次已经选定实现或确认底层一定提供全部信息。**

SB 最后概括，Network Agent 可以订阅 telemetry alerts，再据此修复或通知 Scheduling Agent。订阅和推送方向获得继续推进的认可，但以下内容尚未确定：

- Alert 针对 link、class、flow 还是其中多种对象。
- Flow 标识、阈值与订阅条件如何表达。
- 由 telemetry 直接定位问题，还是由 Network Agent 进一步推断。
- 底层无法提供逐 flow 观测时如何处理。

## 七 设计修订、下次展示与共享边界

### Telemetry Agent 修订

SB 表示会移除 task facts 等应用层输入和 workflow/task 映射，重新整理设计，纳入本次讨论的端到端测量与告警需求，再分享给大家。转录没有给出具体完成日期，也未表示已在代码中落实。

### Network Agent slides

KK 问 Network Agent 的详细 slides 放在哪里。Linxuan 表示材料已在共享文件夹，但尚未向相关合作方展示。文件夹所属人名转写不清，本文不补全。

KK 要求**下次先展示这些 slides，获得反馈后，再决定具体共享哪些材料**。本次没有明确“下次”的日期或新的演示时长。

### 团队访问权限

KK 重申希望更系统地管理团队材料的访问范围。他提到自己已向 Mariam 等人表达意见，希望访问者属于 proposal 相关人员及其正式参与的学生或员工，而不是对所有临时加入者开放。

有关 Harvey 添加成员、个别学生参与及 John Graham 角色的内容均为 KK 在会上表达的观察或顾虑；本文不据此确认任何人的实际权限或项目身份，也不将其对 NRP 与 DOE 关系的口头判断当作外部事实。**本次没有执行权限调整或确定完整共享名单。**

## 八 行动项与待决事项

| 事项 | 负责人 / 状态 | 边界 |
| --- | --- | --- |
| 修改 Telemetry Agent 设计，移除 WMS → telemetry 的 task facts 输入和 workflow/task 映射 | SB 表示会修订并再次分享 | 不等于取消测量历史或网络 flow 跟踪状态 |
| 将端到端 flow/path 测量需求纳入设计 | SB 继续细化，与 Linxuan 对齐调用需求 | 包括 latency/RTT、completion time、throughput；尚未形成完整接口 |
| 明确告警、订阅及故障归因的粒度和分工 | 两个 agent 后续对齐 | 逐链路/类别推断与 connection-oriented 逐 flow 信息的路线未最终定案 |
| 下次展示 Network Agent 的详细 slides | Linxuan；KK 要求 | 获取反馈后再决定共享材料范围；具体日期未给出 |

待决重点是：网络 flow 的标识与注册方式；路径信息的可靠来源；端到端指标如何测得；底层逐 flow 数据的可用性；告警 schema 与归因职责。当前会议主要完成职责收敛，没有形成已验证的实验结论。

## 附录 A 转写存疑与术语口径

| 转写 / 项目 | 本文处理 |
| --- | --- |
| `work field`、`work floor`、`curflows` 等 | 按上下文整理为 workflow；`WS` 等在相关位置整理为 WMS |
| `task faxs`、`taskatch` 等 | 按图与对话语境整理为 task facts |
| `telemet`、`teletary` 等 | 整理为 Telemetry Agent |
| `interned`、`intent RTTT` 等 | 按指标讨论语境整理为 end-to-end、RTT 等；不恢复精确原句 |
| `part`、`pass` 等 | 网络路径语境整理为 path；无法辨明处不据此定义新字段 |
| `flow` 与 `transfer` | 保留网络测量对象的含义；不默认等同于应用文件、task 或 workflow |
| `connection only deadness` 等 | 按持续讨论的网络模式整理为 connection-oriented；未确定具体协议或底层服务 |
| `Marianne`、`Miriam` 等 | 结合已有项目背景整理为 Mariam，姓名仍以原始材料核对为准 |
| 共享文件夹相关人名 `Vitry` 等 | 无法确认，不补全 |

## 附录 B 原始转录

以下完整保留用户提供的转录，不改正术语、语法、数字或发言归属，包含末尾转录工具反馈提示。

<!-- BEGIN RAW TRANSCRIPT -->
Four components we can have.


So one is the northbound API and these northbound APIs are interacting with the WMS, the work field management system and the need to have any access to this at all to get any kind of information we thinking that all the telemetry will go through the network agent and notifications, all of that will only go through the network agent to the scheduler.


Yeah, I think for now it's uh okay for the network occasion to be the only one uh corresponding with the telemetry agent because the network agent needs the uh actual link status periodic and the network agent will then talk to the sched agent for any uh the code exchange, the offer exchange and also the failure the schedul needs to get any kind of information from telemetry Right now you don't have anything going.


Let's keep going.


Just let's keep that in mindful later.


I'll So, uh yeah, the northbound APIs will be those interacting with WS and the location.


So what is the interaction with the WMS?


Oh, yeah, so for the WMS the main interaction is this registration of context.


So what is context is telling is what is the workflow ID?


What is the transfer ID and what was the request or what is the amount of data that is planned to be exchanged ? It's it's don't.


Why is that something that goes to the telemet that is because telemet has toain a map.


So this map, basically.


So where it has to map the individual resources, let's say there is a for example, let's say if you take a compute, for example, or even if you take network, for example, or if that's say there is a link L to which we specify, then we can we have to determine in that link what all transfers are currently happening. If it's theone is that the workflow and theory why't that again going through, just like you said, nothing about the sched or talks to the teletry, why not the network agent do all this work or I do not see how you need the work for management.


If the scheduler doesn't talk to the telemetary, then the workflow management system I do not see, it needing to talk to the telemetry.


My thinking was we can have since this information that uh what are the two sides uh between which the transfer has to happen?


And when is the transfer supposed to happen?


This is the information which originates from the workflow management system. That should only be interacting with the sc schedule in the network agent.


Why should it talk to the integ of the itself is the source of that information?


I just wanted to keep it from that source directly. Uh so that just wanting to know keep it because you feel like it I do not see the reason.


Even if we don't want the work flow management system and if we want that, uh vog flow and the workflow management system, but not have anything to do with the telemetry unless there's a good reason.


Go back to the architecture.


No, where is where is link France slates?


Here So, you know, you' you had all this of the teletary talking to understand the workfl floor runtime dag and or or feeding into the work floor on time dag, okay?


Yeah.


I actually even task faxs why that needs to go from the work for management system to the delatory agent, I do not actually understand I can understand the task facts the task deadlines all going to the scheduling agent, but I don't know why ah you know, for the actions part, I understand that you need to talk to the physical network, but the telementary part I don't get this uh this is the best.


I do not get this and I actually think that this is relevant, but your dismissing it.


But I think this is not relevant but you are sticking it in.


And it seems upside down from my thinking.


So why are you thinking the opposite of what I'm thinking?


I don't get it. Um but let's say um we have the work so and then the set of tasks for that workflow.


And that is something the workflow management system already decides.


The scheduling is only trying to if the scheduler doesn't give you an execution plan, this guy doesn't know what to do with it.


It's not going to go and do the tasks because the scheduling agentity denies it, then you can't do it.


If he doesn't deny it, he gives you a execution plan and then you work with the physical network for that.


What the hell is this?


I think this part depends on the termentaging issue should the know or not know the the work flow information, like if there is happened on theater and the should the therment agent corresponds the rock for ID and the link id ? So link ID and association of the link ID with the workflow ID should be done between this guy, the network agent, and the scheduling agent.


Why the link ID has to go to this guy because now you're spreading the same state the scheduling agent has to have and the network agent has to have about this particular work flow this particular sequence of tasks within the workflow all that is part of the scheduling in the network agent decision making.


Why do you want a pipe us and give it to this guy for what reason?


I think it's part of can be called.


You should not the data the information it should not come from the floging to work for management system to tedament agent. , but I can see this one and you all all of us can see this one.


I think some of this is probably needed for the scheduler to understand you know what is happening with the scheduled um sequence of tasks and so on so you can have relationships between the links that a task uses and so on if you want in the schedule or you can go entirely between the network agent and the scheduling agent.


I don't know if you want to restrict it because what happens is the network agent phase, then do we want the scheduling agent to also do something to say hey, I am killing the whole task so I need to go and work with the network to kill the all the resources for the task across all of those links.


Those kinds of things I I might be able to see, but this one I do not see Okay.


Yes, I think it's part coming called and we need to understand more about the ral management assistant and the to see if there are any information we need.


But currently, I think it's not necessary, yes.


Okay, so that means that taskatch, the come from the scheduling agent itself.


And then the telemet agent will maintain the state of mapping the task facts to the actual link of why why is that happening?


Help me understand how the task facts get mapped to the link ID and why that should not be maintained by these two guys, why does this guy have to maintain that please help me understand.


But that is because telemeary agent uh has to be the state uh it has to maintain the state of the uh of of a v transfer that is happening and where it is happening. Because uh so because um it can be the scheduling agent, which is querying uh, okay, for this transfer, where what is the current status of this transfer?


Or if let's say there is a workflow ID, then what are the uh different tasks of that workflow and and what different tasks are the ID is something that is between these two.


Why is it that the telementary has to know that?


Suppose the telemitation only has the linkwise information.


So at this link, what is the current uh used capacity, what is the remaining capacity?


Then uh, if let's say, I have a transfer ID, then how will I know uh where that transfer is happening?


Or if that's you mean the network agent will be maintaining that state?


I thought telemetry can maintain a state because then anyone even the user can then if it, query the teletry agent to get uh maybe some information about a transfer or if let's say there are some network admin or someone who can actually investigate some link failure because then there will no which transfer failed uh across in oper settling, because then telemetry will serve as the single source of truth for all any transfer that is happening in every uh uh link that was associated with that transfer, uh network agent, I think uh the main goal of network agent is to see what uh is the current status of a of a link and then uh status with the task and the scheduler that I will associate the task with the work flow ID, so I see that hierarchy, but I do not see what you are saying you seem to be throwing randomly things into the telemetry agent that I do not see the logic behind.


The the telemetry agent is not necess it's not necessary to be steadeful like that understanding work flows and tasks and so on.


It's supposed to measure and give you information of what is measured usually when we think about it like SNMP or Promitius or whatever, it can keep track of things for getting historical information, averaging those kinds of things, but why it has to have anything about the workflow or the tasks within the workflow, I do not see. , and if it has something to do between side to side, there is some aggregate communication going on or something.


If you want to have site level aggregation okay, you can have the teletry do that for you and give it to the application, but again, even that, why is it that the network network agent cannot do that aggregation itself, knowing the link interfaces from the sides and knowing how much is flowing in and out of that interface, I do not see the need for the telemetry to have work flow related state in the telemetry agent unless you said, let me throw our network agent.


Let me throw scheduling agent.


I will just have the workflow management system work with the network directly, which is what they do now and the schedulers and network agents are all sort of implicit with human beings . In that case I can see, you know, the workflow agent is doing all the work of talking to the telemetry like Prometheus and so on currently.


That's what we' trying to do away from and you're sort of sticking things in here and there really nilly without I do not see your logic.


You toating a s any about the workflow flow things.


It only know if the link status and net rock engine in the just give you give the tenementary agent the link ID was dark high and high and that you give me the information.


This is or theimentary agent like that you do there may be a reason for saying well I'm going to get level information that is stitch all the links or something that so there's a part level thing, but that's not a task level thing.


You have to say from source to destination.


Here's the part that is being used.


Here's the path level information about utilization, or, you know, latency or things like that at path level end to end, I can see that, but not logical task.


I see.


So then the telelemetry agent will only provide a raw information of every link that is present, it could process it so that it normalize that information, like into maybe standards of met units like maybe everything in GPPS or everything else.


That always is the case, but it could also do averaging.


It could do smoothing. And for latency, it might be much better to get paths and to end kind of information because it's hard to take the sum of link uh level information and say, okay, this is the part level information by just adding up, but because that is not quite right.


Okay.


I think in that case alone, okay, then the teletry agent need not maintain any uh state specific to the workflow or the transfer that is happening, it only aggregates of us are saying it must not have anything to do with workflow task.


I have, you know, can have something that relates to entering parts. Given to an okay it can then I think it will useulf and then it will try to get the uh maybe the capacity or the between the latency values between those two and then it can provide those information to the network agent, then the network agent can be then use that information to see if the transfer is happening as per the expected time and then if it can either repair or the data flow from the management system to the agent.


One of the information is the task information in this way, it regent can know which which file, which data, the source to the detmination and the termentage in the might can use this information to track the track the transfer?


No, but that's a file's you want to have transfers identified and say, okay, this transfer from source to destination B. I want to track its latency.


I want to track.


It's and to end bandwidth.


Those are things that you can ask the telemetry to also track.


Okay. But it's not on a file or I mean you want identify a transfer in some way, fine, you but it is still honor logical transfer not honor application level eh So the track of the trans also uh provided by network agent to tenement agent, not from the WMS.


That's what I think.


Yes, makes sense. Because in that case, even for file transferred, we know the starting an ending location transcript.


So that's so that the network agent can actually keep track of that.


Yeah.


Yes.


Yes.


Okay.


But the network agent cannot go and ask the telemetry me each link and then I will sum it up because that is not a way to be able to get the end to end, right so you actually need that end to end transfer measurement somehow, right?


The network agent is not able to do that measurement for you.


I want to say I sent a packet from here.


How long does it take for that packet to be received at the destination right from source to destination, not linked by link you from social destination you need to know, and you might need to know also the aggregate completion time so that you can find the true put and so on.


So these are all things that the network agent can ask the telemetry agent to keep track off on an ending basis.


But I will uh for this part you you mean the rem Agentuduk contain us status of and the work ag should only in the granrity of past no, the network agent can get that telemeary information from the telemeter agent, but it is not possible for the network network agent to go and do the aggregation based on just path of information that the telemetry gives it. So the network agent can tell the telemeary, hey, give me for this transfer from this source to this destination all the statistics.


Currently, the implementation of network agent is just just to ask the link ID and the liter agent who will aggregate the pass information inside into Lric agent.


Yeah, but those are good for certain metrics, right?


You cannot get the metrics for into and path latency information, especially by just summing up the link by link information.


Oh, you're right, yes.


Because, you know, you can have one link a packet, you say oh, average delay it so much, but parts is different.


Right, right, yes.


Makes sense.


Okay, so I think I'll then change the telemetry design that I had because I was maintaining that map for reverse to cupboard down.


Now the telemet agent need not know anything about uh curflows or tasks, but uh the only thing it will interact with is at least for now it's only with the network agent and the network agent will provide the source and destination, then telet agent can give the aggregatingo and maybe intent RTTT and can also give maybe the the list of you want not just entend RTity you want flow completion time, flow through those kinds of things also.


Okay. Okay.


And uh it can also give uh the list, the the the list of links between those two source and destination and that is is is that also something threetry should be providing. Or that in the network network know already, but either either way that information should be available at the network agent, right to say here are the links for the spath. That this flow is taking from source to destination.


You can figure out which way, whether the network agent can reliably get it or would you want to get it from the telemetry. . And also about the alerts. So the telemeary agent can be yeah, I had a question on the soup if the savior uh if we want telemetary agent to notify the network agent that uh what should it be based on if uh if if um it doesn't know the work floor, the uh transfer information?


Because uh if they say there is a link, uh maybe L2 in this example, then if what alert should should be set up for this L to link and um how would the telemit agent then notify network agent for which transfer that uh downtown is downtown is downtime is being abserved?


Or is it that territory are all the links that transfer is using That's fine but uh if if if there telemeter agent has to uh provide some alerts to the network agent, in that scenario, then uh if the network agent has to set up some condition for a maybe the length capacity is going below some threshold or then maybe notify the network agent Should should those things be set up in the teletary agent?


Because then we need some um ID, which says, or which transfer this alert is going for.


Or is it if the link sufficient like saying that only for this link, if the capacity ever goes down between this below this?


GPS then notify the net location.


Does a link behave selectively for different flaws to say I'm going to screw one floor and not screw another floor.


So you might have if you have that, right you have let's say one class two classes and the link just screws class two and gives all of the bandwidth to class one and that is opposite of what was configured um do we want that kind of notification to say hey, I want honor and to enflow basis all of the telemetry and the thresholds to be maintained and then use that to give it to the network agent or is it that the telementary says hey, this link is performing badly and use that to then give it to the network agent and also we are all already measuring end to and flow statistics, correct?


Yeah.


So we can feed that to the network agent . Should we leave it to the network agent to derive which link is messing up to cause this flow to get lower bandwidth, or do we want the network to keep track of every single flow and on a link by link basis give telemetry to the network agent. Link by link flow by flow.


I mean, the stupid yes. All these connection oriented networks, right?


They can give you all of that information.


That is a flow by flow at each link.


It can give that information. Telemetery agent gets the or so let's say it reached the current available bandwidth on each link and it's say that information, it gives us the network metrics to network agent.


Then if since network agent is having the workfor transfer information, it can infer that what is the uh what what is the which is the trans which is going to suffer in that link the connection oriented thing can give you that information without having the network agent derive that.


That So I mean, I' magnostic somewhat of whether we tie ourselves to this connection only deadness of the network or we don't and then we have the network agent infer based on link by link, class level information and end to en flow level information the C which are the offending links that are impacting a particular flow.


And the network agent can go off and do that inference or we can tie ourselves to a connection oriented nature of the network and say, hey, we will have the t telemetry give you all of that information that the network agent doesn't have to do any more work. Or can reduce the amount of work it needs to do to infer what's wrong.


You can you can chim the latter because the rest of the team is all basically um thinking in terms of connection oriented networks.


You can go that way.


I don't like it, but that is how it is.


Okay.


Okay.


What?


No, I mean, uh I'm just thinking if so since the teletry agent are now interacts only with the network agent, like as of now design and it only provides the interned uh low properties and then it also has can also give the Burlingn flow information.


Then um that's when we can also set up alerts in the to limititation so that theation can subscribe to those alerts on the teleimmitory agent, and then based on those alerts then can um the network agent can do their self-rion or the uh it can notify the scheduling agent.


Okay. Uh let me let me refine this. Uh design then. Um and I'll I'll I'll use these in uh data points and then I'll actually share this again with uh yeah I'll remember the task files and I'll share this again with them you have some slides on the details of the network agent and all that.


Where is that?


You show me those, but are they in the slide set somewhere?


They are the are in the photo we have, but we didn't show you that you maria . Oh, it's in a shade folder that Vitry had.


Yes, yes.


All right.


That's presented next time and then after that feedback then we can figure out what all to share Yes, until they okay.


Yeah, I've been I've been sort of pushing back on um everybody especially Marianne, uh and saying, who all should have access to all the things that we are doing?


Because I don't want to have every single person have access to it.


Right?


Harvey is including lots and lots of people.


High school students, every, you know, last Tuesday or something when we had that meeting, there were lots of other people who were high school students. Some high school student also is there that wants to have access.


I I push back and so I think Miriam said, no, I'm not going to start giving access to anybody other than the people who are on the proposal and they're formally uh committed students of theirs or or members of their uh company's employees.


I would like some little bit of more systematic, uh management of the team.


I don't want anybody and everybody to have access.


Yeah makes sense.


Already John Graham is involved have been pushing back a little bit on that, but I think that will be a little hard. To fight that because this NRP is something that is very tied to DOE and so we may not be able to fight that.


Yeah, I see, I see.


Okay.


All right, guys.


Okay.


Okay.


Talk to you afterwards, okay?


Okay, okay.


Thank you.


Thank you, sir.


Bye bye.


Okay, bye. 




Was this transcription useful or not useful?
<!-- END RAW TRANSCRIPT -->
