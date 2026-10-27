# 2026-10-22 与 SB 的会后讨论：Telemetry Agent 与协作接口

> **日期与参会者**：2026-10-22；Linxuan Zhong（用户）、SB。接在[与 KK、SB 的 Network Agent v1 讨论](20261022_withkksb_networkagentv1.md)之后，按转录中的告别和重新共享屏幕判断，KK 已离开。
>
> **材料与可靠性**：用户提供的英文自动转录，无时间戳及 speaker labels。发言归属按问答关系整理，未经回听确认。本文区分 SB 的设计设想、两人认可的近期简化方向及仍未确定的接口细节，不把设计当作已完成实现。
>
> **拆分位置**：从“should we discuss now or again, I can share quickly what I have worked on.”开始，直到转录结束。对应原文保留在附录 B。

## 核心摘要

SB 展示了 Telemetry Agent 的初步设计：northbound API 面向 Network Agent、WMS 和数据移动组件；southbound collector 从各站点的 Prometheus endpoints 采集指标；normalizer 将指标、单位、时间及工作流上下文整理到内部 state。

Linxuan 建议第一版先收敛到 **按 link ID 和时间范围查询所需容量信息，以及向 Network Agent 主动推送监测事件** 两条交互路径。复杂的 transfer/workflow 关联、历史学习和较细的图节点可以逐步补充。SB 表示会进一步简化设计，再与 KK 讨论。

两人倾向各自在独立目录开发 agent，统一接口并共享 topology、link ID 定义和 mock network。近期展示继续使用现有 Network Agent 与 mock telemetry，不要求 SB 赶在次日完成整合。真实网络或 digital twin 接入取决于合作方后续条件。

## 一 Telemetry Agent 的组成与数据来源

SB 将设计分为 northbound、southbound 和 normalizer 等部分，并用内部 state 存储采集结果及上下文。

| 部分 | 会上描述的职责 |
| --- | --- |
| Northbound | 向 Network Agent、workflow management system，以及实际执行数据移动的组件提供查询和上下文注册接口 |
| Southbound collector | 查询多个站点的 Prometheus endpoints，获取 NIC 吞吐、容量或计数器等指标 |
| Normalizer | 清理、转换和统一指标；校验并合并上下文，建立指标与 transfer/workflow 的关联 |
| State | 保存指标的时序记录和上下文绑定，支持按不同对象查询 |

Linxuan 问数据是否必须通过 site agent。SB 解释，按其当前设计，采集端可以直接从站点的 Prometheus endpoints 获取信息，不必经过 site agent；站点机器上可有 node exporter 提供指标。这是 SB 在会上描述的数据接入设想，未核对真实站点的部署方式。

站点数量尚未决定。设计考虑 ANL、ORNL 等多站点分别有 endpoints，collector 逐一采集；原型阶段也可以先用 mock endpoints。

## 二 两个 agent 的最小接口

Linxuan 明确目前 Network Agent 的直接需求：提供 link ID 以及开始、结束时间，Telemetry Agent 返回所需链路信息，当前最需要的是**可用容量**。这对应已有 mock telemetry 的 `link_samples` 思路。

除此之外，Telemetry Agent 应能主动把监测信息推送给 Network Agent，以便后者进行运行期监测。两人反复将其概括为两条路径：

- **查询 / pull**：Network Agent 给出链路及时间条件，Telemetry Agent 返回信息。
- **通知 / push**：Telemetry Agent 主动发出事件或状态变化信息，Network Agent 据此处理。

Linxuan 尚未仔细设计运行期推送所需字段，计划等实现故障修复、明确具体信息需求时再与 SB 商量。**本次没有定稿事件格式、通知机制或容量字段的计算方式。**

## 三 采集频率与 freshness

SB 设想 southbound 定期查询各 endpoints，并让采集间隔可配置。会上举例：若某个 endpoint 每 10 秒产生新数据，collector 没必要每秒重复查询。这只是说明频率匹配的例子，不是已经选定的默认值。

Linxuan 指出刷新频率存在取舍：过于频繁会带来额外流量和开销，过于稀疏则可能使用陈旧数据。不同指标可能需要不同的 freshness 要求，可以进一步考虑哪些指标应高频获取、哪些低频获取。

两人认为第一版不必把这件事做得很复杂，可以先保留可配置能力并说明已考虑该问题，后续再完善。会上没有确定自适应采样算法、具体阈值或由哪一方决定刷新间隔。

## 四 Normalizer、state 与上下文绑定

### 指标标准化

SB 提出统一不同来源的指标格式，包括 GB/s 与 Gbps 等单位转换，以及不同时间表示或时区的处理。标准化后的信息写入内部 state。

SB 将 state 解释为时序数据：既保存整理后的观测值，也保存与 workflow 和 transfer 的关联。未来可落到数据库；第一版可以先放在进程内，不必先建设数据库。

### 为什么需要 binding

SB 用例说明：若 transfer X1 在 10:00–11:00 使用 L1，那么在该时段采集到的 L1 指标应能关联到 X1，再关联到所属 workflow。查询方由此可以：

- 给出 transfer ID，查询其涉及链路及当前状态。
- 给出 link ID，查询在该链路上传输的 transfers。
- 在链路故障时，找到可能受影响的 transfers/workflows，通知 Network Agent 做 repair 或 risk report。

这是所提出的上下文映射功能。**时间与链路上的绑定本身不等于已经能从聚合计数器精确分解每条 transfer 的带宽**；会上未说明如何完成这种细粒度计量。

Normalizer 还要处理不同 endpoints 的字段到内部对象的映射，例如 NIC、资源或链路指标，并合并来自各调用方的上下文，支持双向查询。

## 五 Northbound API 的三类操作

SB 展示的操作名称整理为 `register_context`、`get_state`、`get_history`。这些是按转录含义统一的写法，尚未据代码核对最终命名。

### `get_state`：按对象查询，并在需要时刷新

SB 设想支持按 endpoint、resource/link 或 transfer ID 查询。

| 查询对象 | 设计中可能返回的信息 |
| --- | --- |
| 起止 endpoint / 节点 | NIC 或链路是否可用、容量或吞吐、观测时间、观测距今多久 |
| Transfer ID | 所属 workflow，SENSE commitment/service ID，数据移动 execution ID，运行状态，起止位置，当前 TX/RX，计划与已发送数据量，观测来源与时间 |
| Link ID 或 endpoint ID | 该对象关联的 transfers；具体字段后续与 Network Agent 对齐 |

处理流程是先识别查询类型，检查观测是否 stale；需要时通过 southbound 重新查询 Prometheus，再从 state 组装结果。SB 表示它与 Linxuan 的 `link_samples` 有相似功能，名称可以调整。**两者的功能有重叠，但本次未完成请求/响应 schema 的逐字段对齐。**

### `register_context`：由不同调用方补全同一传输的上下文

SB 设想三个来源都可使用该操作，但补充的信息不同：

| 调用方 | 会上描述的上下文 |
| --- | --- |
| WMS | Workflow ID、transfer ID、计划数据量、起止位置、计划时间窗口 |
| Network Agent | 同一 transfer ID，以及 SENSE commitment/service ID、实际计划窗口、预留速率或容量 |
| Data movement manager / executor | 作为第三类注册来源被提出；转录没有完整展开其具体字段 |

Linxuan 问当前是否还要实现 WMS 组件。两人明确近期不做 WMS，本阶段聚焦 Network Agent 和 Telemetry Agent，其他组件以后再看。支持一种调用方的接口设想不代表需要同时实现那个调用方。

### `get_history`：后续学习与校准

当前 Network Agent 暂未使用历史查询。两人讨论未来可能用历史数据改善 offer、估计传输时间、调整估计模型或辅助推断缺失信息，但本次不要求实现这些学习功能。

## 六 第一版应简化到可演示的基本功能

Linxuan 认为总体逻辑可以理解，但图中的节点较多，直接全部实现可能复杂。建议先做一个具备基本功能的框架，再逐步加入更复杂的部分，优先支撑两个 agent 之间的查询和推送路径。

SB 随后确认，Network Agent 当前主要需要“给定 link ID 返回容量”，复杂关联是否第一版就必需仍可再想。Linxuan 表示，随着故障处理代码发展，可能需要更多字段，到时再共同讨论。

这不是永久取消 context binding 或历史功能，而是先确定 demo 的最小范围。SB 表示会尝试简化，再与 KK 讨论后开始写代码。会上提到 11 月 workshop 和 12 月首个 deadline 带来的时间限制，但 workshop 名称与具体截止日转写不清，不据此补全。

## 七 独立开发、共享代码与模拟环境

### 次日展示不要求仓促整合

SB 问，为次日 demo 是否要立即替换现有 mock telemetry。Linxuan 表示可以先展示已有 Network Agent 的 slides 和代码，SB 后续独立实现 Telemetry Agent，再进行整合，无需为次日赶着合并。

### 仓库与共享定义

两人倾向在各自目录实现 agent，通过约定接口通信，同时考虑共用的库和依赖。可能共享的对象包括 topology、link ID 等定义，以及 mock network。

讨论中提出建立 GitHub 仓库，也可放置图、设计材料等便于共享。Linxuan 在结束前表示要创建仓库并分享代码，供 SB 查看可复用部分；**该转录未提供仓库地址，不能据此认定创建或同步已经完成。**

### Mock Prometheus 与真实网络的边界

SB 询问后续 demo 是否继续使用 mock network。Linxuan 表示先使用同一个模拟网络保持简单，能否扩展到其他环境取决于合作方工作和 KK 的意见。

SB 据此提出：复用同一 topology 和 mock network，为相应节点、链路设置 mock Prometheus endpoints，以相同 API 开发和测试 Telemetry Agent。真实网络、独立 digital twin 以及 endpoint 到真实资源的映射均留待后续，尚未在此次会后讨论中决定。

## 八 行动项与待对齐内容

| 事项 | 负责人 / 状态 | 近期范围 |
| --- | --- | --- |
| 进一步简化 Telemetry Agent 设计，再与 KK 讨论 | SB | 先做基本框架，不要求一次完成全部节点 |
| 分享现有代码，确认可复用部分 | Linxuan 提出 | 优先 topology、link ID 定义、mock network；仓库地址未在转录中给出 |
| 基于共享模拟环境开发、测试 telemetry | SB 的实施设想 | 可先设 mock Prometheus endpoints |
| 对齐链路查询与事件推送接口 | Linxuan、SB | 先满足容量查询；推送字段随运行期需求继续明确 |
| 展示已有 Network Agent slides 和代码 | Linxuan | “明天”按会议日期推算为 2026-10-23，不要求两个 agent 已整合 |

尚待明确：统一的链路标识与容量字段语义；查询结果的时间窗口和 freshness 表达；push 事件内容；第一版是否需要 transfer/workflow binding；共享目录、依赖与具体 schema。双方尚未把这些问题形成最终接口契约。

## 附录 A 转写存疑点与记录边界

| 原转写 / 项目 | 整理口径 |
| --- | --- |
| `teletry`、`teletter` 等 | 按语境整理为 Telemetry Agent |
| `north part`、`south pound` 等 | 整理为 northbound、southbound |
| `nick`、`stupid` 等 | 在网卡和指标语境分别理解为 NIC、throughput；不恢复精确原句 |
| `sense government ID` | 按前后文整理为 SENSE commitment ID，最终字段需核对 |
| `Mark's network`、`mark topology` 等 | 按整个讨论的模拟环境语境整理为 mock network/topology，不据此引入名为 Mark 的开发者 |
| 11 月 workshop、12 月 deadline | 只记录月份和时间压力，正式名称与具体日期待核对 |
| Colloquium 参加次数等末尾闲谈 | 原文保留，正文不作为项目行动项；数字不据转录确认 |

## 附录 B 原始转录（会后部分）

以下保留用户提供转录的对应片段，不改正术语、语法或发言归属；包含末尾与项目无直接关系的闲谈及转录工具反馈提示。与前篇附录按顺序拼接可还原输入转录。

<!-- BEGIN RAW TRANSCRIPT -->
should we discuss now or again, I can share quickly what I have worked on.


Yeah.


My screen is vegetable, right?


Yes.


Okay.


So uh for the teletry agent, this is what I thought of initially.


So there will be like uh three main components in the perimetry agent, the northbound uh component, which is interfacing with the workow management system and maybe the data movie data movement managers or some uh components which actually move the data.


And then also the network agent.


So these two are the main entities which will communicate with the north bound component.


Yes.


And so here from the network agent, firstly is I give you the link ID. So we should which was a the same amount, the same mouth I have that also Yes and the start hand and you give me some some information the information is only the capacity and the list is the poor pace and the wish will also have a push pass and the you actively give me the some information to do the littleog monitor, but I didn't carefully think about that power, so now there should be two path, yes.


Correct uh yeah that is the northbound component and then we have the southbound component as well.


This is more of a collector and which will talk to the Prometheus and points on multiple uh sites for now we can just assume it there's one uh like a mock Prometheus endpoint, which is giving us certain metrics and specifically the nickbased uh throughput capacities or some counters and uh promises is collected information from each side or so it so it either will talk to the site agent or no?


Oh, no, I mean, uh, it's over here um each site would have its own site agent and uh the actual Prometheus has something called node exporter and this node exporter is something that is set up on the machines and uh this keeps exporting the uh individual metrics that we can set up uh for example uh uh so there are these metrics we can specify. Information to just get the information from the site this doesn't the agent so site this is independent and we can use uh these like Prometheus endpoints and we can fetch the query the information directly. Are going to write how many site to test I haven't thought of that um what do you mean by h how many such?


Because you need to create the information from different local side Okay, uh so you mean to say uh like when ANL site onNL site like that?


Yes okay okay got it okay I think uh okay for this case um uh each site will have a Prometheus theseomemitus end points set up.


So there be multiple such Prometheus moometheus that can have, and on the southound will query each of thoseometers mock . Okay, okay.


And then uh once we so the south bound uh a component will keep creating these uh metrics periodically and we can configure that uh interval, like how how frequently to carry these Prometheus end points.


And then uh it to desc send it to the the interval how to decide the interval I think that is something that can configure.


It depends on how frequented a Prometheus itself will generate the metrics For example, uh if this is um if if let's say this slashmetrics gives data every 10 seconds, then let's say for one, maybe the ANL site, this is giving data every 10 seconds. Then um this southpound collector should qu create every 10 seconds instead of every one second. It remains me, there is that fit off about the frequency because because if you uh port, like you ping too frequently, it will cause an itog traffic . But if you are not that if you ping it to not that frequently, maybe the data will be old, so it ass seems that there is the t door we need to think. The current idea is that for the near data for the let me think we should defy which part of data when the twoing we toate frequently under which part of which par of data we need to gate none that frequently.


And maybe this part can be defied by not to to defy the interval. Anyway, this is a part of the way can think Got it each data on network can have its own frequency of uh freshness like how freshly we can we it's kind ofation.


Maybe the first phase we did we only had to consider too much about this.


But we can tell them we have the considerance and no, we will do you in the in later. . Uh yeah this is one thing and um yeah I think one is the data let's say we've query from the uh Prometheus endpoints we also have to clean the data and store it in some normalized form . So maybe, for example, converting giga bites per second to gigabits per second and such type of uh changes will have to make uh and store it and maybe there will be times zone differences, we have to store all of those things and store it in the finally in the state . So normalizer un the normalizer will take care of converting those different metrics with different units into one state and the state is having two things.


One is the rawtrics that we are getting from here and the Prometheus endpoints uh which is actually the processed one so the I mean, once the rometrics are obtained, we normalize and we store those uh different metrics.


But also it will stored the association with uh different workflows.


For example, if there is a transfer or a link is measured, let's say at uh 10 am , then depending on which transfer was scheduled at that time, it will try to store that information that if this link has a current uh used capacity of maybe 10 GVPs, then of those t 10 GVPPS, uh what all transfers or are currently related to that 10 GVPS.


So that sort of uh fine grained data, this state will be holding.


Sorry, I didn't I didn't get the function with the state I nearly uh this uh state is nothing but uh you can say it's a time series data . Okay.


So because every time oh that'sation it's a yes yes and this is actually storeed in a database but uh we also uh I think for now we don't need to worry about database we can maybe store it in the processed and then uh in that , uh if uh for example, so that's said this transfer here or maybe X1 is the transfer ID and this transfer let's say happeningring between 10 a to 11 a pitches you and that is going through a link El one pitches you then here in the south bound when we query the link or when we create the link El one a metrics and if that timing is between 10 a to 11 a.m, then this state will hold that binding, so it will bind the current metric that we'll varied from the uhometheus endpoint to the actual work floor, the transfer ID that was happening for that time duration.


So the use of this is by the negrogation.


So the network agent can provide the transfer ID maybe X1 and it can know what uh is the current status or what is the current uh link capacity that the transfer is using?


Across the given sect of links that the transfer is using.


So that is the binding information we want to store as part of the state and this is inside the telemet agent.


And also, in case a link has some uh problem or like a failure, then we know because of the bindings, we know exactly which sect of transfers were affected, and because of that which se of workflows were affected, because that link was failed , and the teletter agent can notify the network agent about the link failure and those workflows and network agent can then do the repair or risk report so that is why the binding is important here forapping for you is a it's fine. And the yes and we just consider consider the specific specific details inside the node. And uh this does these things so we have this uh so the south bound is basically collecting from each Prometheus endp point from different sites So it has to resolve those different targets because each Prometheus end point will give different set of uh metrics and uh once uh and it also has to uh map or uh match the metric to the particular state that the um the metric is corresponding to.


So uh maybe uh one metric corresponds to uh nick uh properties, one metric corresponds to uh uh maybe the core utilization or something uh or or maybe the link uh capacity or such different mappings each fromages end point can give different uh fields.


So this has to resolve those different targets to uh each part of the state.


I'm not sure on the network uh it's so it's saying uh so let's say um okay actually let me let we come from the northbound it be audden be easier.


So, uh from the northbound uh ABI uh we can have three different things. Um One is the registered context and uh one is a get state and one is get history , uh this get state is similar to the link samples the Q had in your uh API. So I can rename this.


That's not a problem.


So uh get state is uh similar to link samples which you had.


So given the uh ID like, I can show this. Just one.


Here, so in getst state, actually you can use in three ways.


So in getstead, you can uh provide the end points.


So the start in the end locations the the node IDs and uh you can get uh some properties like this.


So if the endp points were ANL data transferode A and are the data transfer node P, then uh you can give you can get these uh data points uh so it will say that the neck is up and it can support uh On second.


Yeah, it can support so much of stupid.


It is the capacity of that link and uh of that in and uh what was the time at which it was observed and uh the time duration it has passed since observing it?


So this information is one way of querying the state, the other way is uh you can give the transfer ID, let's say x one, and you can get all the information correspond to that transfer . So, for example, uh here, if the transfer ID is expon, then it'll say that um the uh it belongs to this workflow and it has this sense commitment ID.


It has this sense service ID and it says this is the actual data movement execution ID and what is the current data, whether it is done, running or failed and uh then you can have the actual uh starting and ending locations and uh the same information. Like what was what is the current uh transfer rate like a TXit in our exit for these two sites?


And for the execution, how much of uh uh data has been uh I think this is how much of data was planned to send and how much of data is send and uh this are not short, but these uh you can get basically the current status of this transform from the telemeary agent um and also who which endpoint was used to derive this information and also the time the time when this was observed so the can is the kind of data frommentation.


Yes so this is what the network agent can get once it uh asks for this transfer right yeah similarly it can give a specific link like uh it can give a link ID or maybe a endpoint ID and it can get the uh transfers associated with that link if this is also one information I'm planning we can get okay that's the this the details of each field that we can we can discuss uh when I implement how to fix the failure and what information I need.


Correct can we used at that time okay I say okay.


It's okay.


Yeah, but uh yeah uh I also have this registered context uh verb so this registered context is like a initialization.


So uh this is done in three ways again.


Yeah.


So the regist context can be done by the workflow management system.


So here workflow management system talks to telemetry agent.


Similarly, network agent can also use the register context , verb and it can talk to the telemetry agent, and also the data movement managers can also all the executor can talk to the teleter agent.


Now, each uses this registered context verb , but they do three different things.


So the verb for a management system will set up the context.


It says that um this is the workflu ID.


This is the uh transfer ID.


This is the amount of data planned to send and what is the location and what is the time window in which this is planned to be sent?


That's all. Uh but then the network agent will send the same transfer ID, but it will also send the sense government ID and the sense service indent id , and the actual time window where it is planned to be sent, and the rate of the capacity which is a reserved. For that first point, you the wri wrote from Should we implement the component of WMS currently?


Which is available.


I see.


It says like the registered context can be used by theMS, but we are not implement.


We are also not imprement in this.


I can songs, the network and the HPI forative agent..


It's we can it's we can't see in the later. Makes sense.


I think history you're not using now, right?


Uh to get the his historical don't use the history.


Maybe we can also bug and history is used for learning to make those uh offers, right?


Yes and uh let me see yes, yes.


Got it.


I think then it is fine.


I' not worry about this for now.


I can be used to make some inference to the musing field. But it's not a work on it location yes okay, yeah.


For workcation has to use use the theory to estimate the some data transfer time or fix the estimate model.


Yeah.


Okay.


Okay.


I see I think uh okay the get state is something I will uh implement and uh so it it will basically resolve the type.


So whether you're asking for a endpoint the current state or whether you're asking for a resource or whether you're asking for a transfer ID, depending on that it will fetch the relevant information from the state, but even before that, um to it also checks if it refreshes needed, whether the data is stale.


And if it is stale, then it uh uses the southbound APA to query the Prometheus and uh refresh the data.


And then uh it will assemble the response and provides the latest state in formmission on the latest information for that link or maybe for the transfer.


So this is how the get state will be will be running.


But uh, yeah, this is the north bound.


I think normalizer is nothing about different.


It's it's only about a bunch of uh validation of the context and the uh it's also trying to merg.


I think this is the key part of this normalizer.


So it tries to as I said, it tries to relate each uh metric to corresponding work floor transfer uh ID so that we can query them both the way so that given a link what transfers are happening and given a transfer ID, where is the transfer happening?


Both of these information we should be able to query so that is something the merged context findings helps us. And uh yeah we can store this context in the state finally.


My feeling that uh let me think for uh firstly, in the currentirgin, we can just make some basic functions. And the we can deviver power agent individually and uh in communicator with that interface.


I gave you the link ID and you gave me the information and of course, you push some the information actively to N agent.


So we can just focus on the two paths. And the other things we can just make it the uh simpler actes, but it depends on you a contrary. You can think which parlay is the important and and uh uh just like the demos demo style and which power which partly is the more complicated, we can movie that use the next phase .. Yes.


So then this association maybe let me think if the association is really needed the only thing you think uh you need is given the link ID, you want the kind of and and yes and you gave me some information but currently the information I need just to the vader capacity.


So, as I continued to uh implemented a cold and the medicator complicated and maybe we I need them more I need little work agents.


I need a more field and and we can discuss how to get hit.


Okay, okay.


That's fine then.


Yes.


So that means for for tomorrow's demo, uh is should I implement anything because I think you're already using the mo uh teletry and uh get uh uh is the get sample sorry, big samples that you're using is already using a mark.


But what what should I influment then for your code?


First from our I think it's I I can I can just to show some show the the car code.


It's okay. And uh later her, you can just implement uh some boatmentary agent and and the we can mer But if if we need to a very hurry to merge in our code, we can develop a betterate individually.


I think it's better. . And you can build your own uh folder and uh little agent the folder and thenrate in the folder, the the communication between the jo through the two paths and the issue with the two and the hm this should the house the same library, same dependency. Yeah I I think it's fine.


I think hard to me with can tell to better with the our folder individually. How do you think of that?


And uh communicate communicator with each other through the two paths through the interface and I do not too rely on something . But yes, we can have the shared library, like the topology, defin different, like something, like the topology, like the link ID, this will be the thing.


Yeah, I think those uh I think there are a few things which are overlap between teletry and network.


We can, we should design that.


So uh are you pushing code directly to this suppository?


Or are you using your own I think currently like the build our own we can also add another fer the resources and we can put our graph, our figure it our things into that to share.


Okay.


Okay.


That should be fine.


Do you have the report already created for No, I can phrase no.


Okay, okay fine.


Okay.


Okay. Uh that's actually that's all I had like I used your uh network agent example and tried to build these , but I will also try to refine this on maybe I'll discuss with KK and uh refine this.


Do you have any other like uh suggestion or a comment as to whether something is uh should be changed or theic it makes sense, but the same as I know the humanity.


So when you implement it, the code is very I think it might be some kind of complicated . Okay.


And so for the demo we can to either step past tape, like you can build a simple framework that has some basic functions and the next day tape you add some more complicated functionctions in to eat, and then cape improved.


So uh so I think currently you can just build a basic basic things. Let me think I'm not sure because the logic sound like uh sound sounded like clear and uh I think it's is fine.


But the note, I think seemed too too many.


I agree If you want to implement you want to build a graph for all or listen loads. For example, what other for less figure for all over all this nodes, there are two and two, three, four, five, six, seven, eight nine learn too many nodes, so you will the YouTube be more simpler. And uh I believe some functions are this a survey but you can add it in the future. Not in the not in the firstverging, I think.


Because because because I because uh they rely for the AC or shop is November and for the first landline is on the December, so we have limited high.


We can move some work to phase two.


Yes.


Okay.


Got it. Oh yeah let me so one final question I have is with uh the yeah, not here.


So these Prometheus end points and okay, no, no, no, my question is you are using a walk network and a mock um uh twin make a digital twin uh let's say for now you're using a mark network. Uh be using that for the demo or you'll be using something else for the time will you be using natural network later on?


It is depends on others if others can extend the way he has a good way and the KK think it's okay, we can extend it to So the idea about the currently we can just we can use the same mark network to make it simple and clear.


So then um okay, let me think.


Because then the further Prometheus also, I can set up mock Prometheus endpoints and then test my telete can use the same interface, same API But the underlying network can be just the mark.


Yeah.


I can share the same technology as you are using with the mock topology and I can see which Prometheus endpoints will provide me the metrics for those nodes and links, and then I can use that to build my telemit agent and test it. . Our yeah, I can use my other domain to.


But basically I'm saying like we can use uh Mark's network to simulate these things.


Yes, yes.


Okay, okay Let me I will share my code on you can check which part of the we can we can share your your two agents.


Yeah.


Firstly is the tropology and the second is uh marknet work and the we can see.


Okay, okay, sure.


Sure.


So then in for two tomorrow only you will be presenting the network agent slides in the core then Yes, actually do you know how many corses for the colloquier we have because I want to escape the tomorrow's kloquier.


I think it's to hurry.


They want us to do seven courses this time instead of six last time we had six courses this time with more pathod we have 10 or sessions be little careful I think this is not loading for some reason but yeah but yeah I remember there there were 10 s and uh I think so far three are done uh four are done four are done it so we need uh three more yeah I need to be careful Okay, it's fine.


I will sing.


Okay. Fine.


I'll discuss this same thing with KK.


I'll maybe simplify some things here and then I'll discuss with KK and uh then maybe I can uh also write the code for this. . Okay.


Let me create a kid hop.ory.


Okay, sure.


sure. , bye.


Thank you.


Good night.


Good night. Bye bye bye. 




Was this transcription useful or not useful?
<!-- END RAW TRANSCRIPT -->
