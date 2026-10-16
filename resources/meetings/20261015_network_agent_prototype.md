# 2026-10-15 Linxuan 与 KK 的 Network Agent 原型讨论

> **日期**：2026-10-15，用户称为“今天的会议”。
>
> **参会者**：Linxuan Zhong（用户）、KK。用户明确说明只有两人参会；下文提及的其他人均为讨论对象。
>
> **材料与可靠性**：用户提供的英文自动转写，无 speaker labels 和时间戳，存在大量术语与人名误识别。正文依据问答关系整理发言归属，未经回听确认；存疑名称单独标注。附录原样保留转写，供回查。
>
> **记录口径**：区分会上认可的近期行动、正在讨论的设计和仍未回答的研究问题。有关框架来源、许可证及外部系统部署的内容只记录会上说法。

## 核心摘要

两人同意以 Linxuan 展示的 **planning、runtime、learning 三张执行图为起点，开始写 Network Agent 原型，逐步补充功能**。KK 希望在下周二的 SciNet 会议展示部分代码，即使只完成几个组件，也不必等联合 hackathon 才开始。按本次会议日期推算，下周二为 **2026-10-20**。

贯穿讨论的问题是：**如果一连串函数已经能按规则完成容量查询、路径选择和接纳判断，agentic 的部分究竟在哪里，AI 增加了什么？** 日志和事件分析、根因调查、下一步 probe 的选择、动态寻找额外路径、观测刷新频率及历史校准被讨论为候选位置；本次没有确定这些位置采用 AI 相比规则的可测优势。

KK 强调运行期不能只处理硬故障，也要处理拥塞和逐渐变慢。一个具体场景是：现有路径无法满足新的带宽需求或 deadline，agent 寻找额外路径与容量，再通知 transport 增加 subflow；流量拆分与接收端如何组合仍需衔接。学习阶段则应积累 **已承诺资源与实际使用情况的历史**，并区分主机侧和网络侧原因，不能仅凭一次低利用率就认定下一次应减半分配。

KK 希望本组尽可能掌握 Network Agent 和 Telemetry Agent 的实现。Linxuan 提出自己做 Network Agent、另一位同学做 Telemetry Agent 的分工思路，KK 认为可行，但该同学姓名转写不清。两人也认可把工具及小 agent 写成可复用组件，供不同执行图调用。

## 一 规则与 LLM 各自负责什么

KK 开场将决策所需的信息分为：已知的 rules、尚不清楚而需要 agent 进一步获取的信息，以及其他已掌握的上下文。问题是怎样把这些信息组织起来，使 agent 能够作出决定。

Linxuan 用框架和容量检查示例介绍实现方法；KK 随后用一条端到端路径说明自己的疑问：给定拓扑，routing agent 找出从 A 到 Z 的 hops，再向沿途 link agents 查询容量，最后返回 accept。若每一步都是调用函数、应用规则并返回答案，这与传统 subroutines 有何区别？

Linxuan 解释，可以在执行图节点内调用一个 agent 或 LLM，由它分析信息、调用工具并返回判断。**这个解释说明了 LLM 可以放在哪里，但两人仍在探讨为什么某个决策需要它。** 后续多路径讨论再次回到这一问题：动态决策也可能用规则实现，AI 的边界尚待厘清。

## 二 LangChain 与 LangGraph 示例

### LangChain 的工具调用

Linxuan 展示容量查询工具：用函数读取链路总容量与已预留容量，返回可用容量；创建 agent 时配置模型、工具和 system prompt，再提交容量请求。System prompt 要求先调用容量工具，依据输出回答，不编造容量。工具也可以由 MCP server 提供；会上将其解释为类似远程函数或服务的接入方式。

KK 先问框架来自什么公司、是否涉及中国背景，理由是这是 DOE 项目，希望避免后续出现争议。Linxuan 回答框架代码公开、采用 MIT license，认为可以使用；KK 表示可以先推进。这是会上交流，并非完成了正式的许可证或来源审查。

### LangGraph 的状态与分支

Linxuan 介绍三个概念：state 是节点共享的数据，node 是执行一步操作的函数，edge 决定下一步执行哪个节点。示例读取 requested/available capacity，再通过条件分支进入 accept 或 reject。KK 将其理解为类似 state machine，并指出这里是在应用容量规则。

KK 特别追问：**accept 之后，容量在哪里被真正扣减或更新？** Linxuan 说明当前示例只是返回 accept，没有修改容量。随后讨论到实际实现中需要更新状态，并作用到数据库；本次没有给出该写回过程的完整实现。

## 三 Network Agent 的三个阶段

Linxuan 展示的总体设计包括：

| 阶段 | 会上描述的职责 |
| --- | --- |
| Planning | 接收 Scheduling Agent 的请求，查询信息并生成 offers，进行临时预留与正式提交，向 SENSE 提交 service intent |
| Runtime | 监测传输偏离预期，检查路径和受影响的 commitments，判断能否局部修复；必要时报告 Scheduling Agent 重排 workflow |
| Learning | 将 commitments 与 telemetry 记录关联，比较承诺和实际表现，调查偏差原因，调整后续估计与资源策略 |

KK 同意这是一个可以开始实现的起点。两人采用边写边学、逐步修改和扩展的方式，没有要求一次完成所有功能。

## 四 Planning 的预留与提交

### Quote 与观测刷新

Linxuan 按执行图说明：收到 quote 请求后，校验请求，刷新数据库或 telemetry 中已经过时的信息，寻找 placement，估计完成时间并返回 offers。

观测刷新也被讨论为一个可能的 AI 决策位置。KK 将其概括为：变化多时更频繁地刷新，变化少时降低频率，在查询开销与信息过时之间作选择。

生成 offer 的候选方式是先用固定规则计算，再考虑 over-provisioning 等调整。讨论涉及是否分配了不必要的容量，但没有确定调整算法或额度。

### Reserve 与 commit

原图使用 `hold`，KK 建议称为 **reserve**：先预留但不正式提交，决定后再 commit；两人将其类比为两阶段过程。

Linxuan 描述了 pending 状态、本地 ledger 更新、向 SENSE 提交 service intent、读取成功或失败结果，以及失败时 rollback 等环节。这些属于拟实现的流程，状态与网络操作的具体衔接仍需在代码中落实。

### Circuit 的选择与建立

KK 追问图中 `place on circuit` 的含义。Linxuan 解释，一方面需要在本地判断复用已有 warm circuit 还是建立新 circuit，另一方面需向 SENSE 发送 service intent，取得配置结果。讨论没有把 circuit 选择与实际建立的接口完全定下来。

## 五 Runtime 应同时覆盖拥塞与故障

Linxuan 描述的流程是：检测偏离预期的事件，扫描路径，判断是否能及时局部修复；可以则修复并报告，否则向 Scheduling Agent 报告 `at_risk`，由其考虑重排 workflow。

KK 指出：**deviation 不一定由 failure 引起，也可能是 congestion，或逐渐变慢。** 因而沿路径检查时，应找出哪个 hop 拥塞，再考虑 reroute、降低某个实验的负载或 reschedule。修复机制需要覆盖这些情况。

扫描路径还涉及路径上的其他 commitments，包括不同 workflows 的传输。具体检查范围和触发方式仍在设计中。

两人也区分了“发现问题”与“找到原因”：发现传输赶不上 deadline，并不自动说明原因是什么。Linxuan 提出 LLM 可以分析 logs、configuration 和 events，形成原因判断，并选择接下来探测什么、如何探测，再据此提出解决方式。KK 将其中的 attribution 理解为 root-cause finding。

在本次讨论中，`at_risk` 表达的是 **Network Agent 无法靠自身局部修复及时满足原承诺，需要上层调度介入**，并不只对应链路硬故障。

## 六 多路径增容与 AI 的作用

KK 用以下场景解释希望支持的行为：

1. A 到 Z 的 path 1 已为一个实验分配 50 Mbps。
2. 实验随后需要 100 Mbps，但 path 1 无法单独提供。
3. 另有 path 2 可从 A 到 Z；希望结合两条路径满足新的容量需求。

Linxuan 追问：如果已有 multipath transport，它可以获取路径并根据各路径容量分配流量，为什么还需要 AI？KK 进一步解释，希望能够动态发现新路径，并在传输无法满足 deadline、需要更多带宽时，主动找到额外容量，通知 transport 建立另一个 subflow。两条路径容量不同时，流量也可以不均等地分配。

讨论中设想的 agent 流程是：发现 deadline 风险，向其他 agents 寻找额外路径，查询额外可用带宽，判断现有路径加新路径能否满足需求，再返回增补路径方案。Transport 如何使用这些 subflows，以及如何把传输的数据组合起来，需要进一步衔接。

KK 同时承认这些动作也可以通过 rules 实现。因此，**“动态发现并提供额外路径”是希望实现的能力；“由 AI 来做比规则更好”仍是开放问题。** 本次没有选定 transport 协议、流量拆分算法或验证场景。

## 七 Learning 应基于历史进行校准和归因

Linxuan 提出，将每次 commitment 与实际执行记录绑定，比较预留或承诺的容量与实际使用情况，再做 calibration、attribution 和后续 plan adjustments。

KK 通过追问明确，主要比较的是 **committed resources 与 telemetry 反映的 actual result**。对于“分配很多而实际使用较少”的情况，Linxuan 举出的可能原因包括主机处理速度或磁盘过慢，以及网络侧瓶颈；不同原因可能对应不同策略。

Linxuan 一度用“这次只用了一半，下次就给一半”的方式解释校准。KK 补充，应保留结果和使用情况的历史，学习是否持续存在 over-provisioning，或者某个请求方是否总是申请过多带宽。一次低使用量本身不足以确定后续分配。

后续调整的候选项包括更新校准模型、调整容量或利用率、选择其他 circuit、路径、计算资源或 host。会上没有确定各类调整的权限边界与实现方式。举例中的 Gbps/GB 等单位转写混乱，不作为量化配置记录。

## 八 先写代码并展示局部进展

KK 希望本组主动推进，不必等待其他人安排 hackathon：先自己写代码，再带着已完成的部分去讨论，让合作方给反馈。即使反馈有限，也能获得实现上的先手，并更主动地掌握研究方向、形成自己的论文工作。

近期展示目标是 **下周二，即按会议日期推算的 2026-10-20**，可以只 walkthrough 部分代码，无需完成全部设计。转写中先说 Monday，随后立即改为 Tuesday，故以修正后的 Tuesday 为准。

KK 还提到，周五若仍有工作，可以继续补充组件、参加 coding 活动；如不需要，也不必一直留满三四个小时。该处未明确具体日期，不能据此认定联合 hackathon 的正式时间已确认。

关于本组分工，KK 表示希望尽可能掌握 Network Agent 与 Telemetry Agent。Linxuan 提出自己负责前者，由另一位同学负责后者；KK 认为可行。另一位同学姓名在转写中为 `Arabic`，暂不补全，也不能将两人讨论视为该同学已确认接下任务。

## 九 组件复用与外部框架参考

### 工具和小 agent 的复用

KK 提到一位过去在 AT&T 共事的朋友，正在开发 failure root-cause analysis 的 agent 系统，主要基于 time series。KK 已通过 WhatsApp 给 Linxuan 发过该人的网页链接。其当前单位被转写为 `Xing`，名称待核对。

KK 希望借鉴的重点是：对方把分析、检测等工具和 agents 组织成库，可以据此创建或组合 agent。网页也有随 presentation 更新而自动生成的中英文视频，Linxuan 可以查看；time-series 分析本身不是这里的研究重点。

对应本组实现，KK 建议从一开始就让工具、小 agent 和子组件能被其他执行图调用，避免每张图重新实现一遍。Linxuan 表示认同。

### Remora 与 Academy 的讨论

Linxuan 还提到一篇相关 agent framework 论文，名称转写接近 **Remora**，并称其与 Johns Hopkins、Meta 多年部署有关。这些名称和部署说法均待核对，不据此确认论文身份。

另一个框架被转写为 `a cal` 等，结合已有框架讨论可能指 **Academy**，仍待确认。Linxuan 的理解是，它偏向分布式 agent middleware，与 LangGraph 的内部执行流程编排可以组合：先用 LangGraph 写 agent 内部功能，再考虑跨站点的分布式运行与协作。KK 将其理解为从单个集中环境扩展到不同站点 agents 的合作。

两人希望再了解合作方准备采用什么，以及他们对相关框架的看法。本次没有确定整个 SciNet 共用的分布式框架。

## 十 近期行动与待决问题

| 事项 | 负责人或状态 | 时间与边界 |
| --- | --- | --- |
| 从三张执行图开始写 Network Agent 代码，逐步扩展 | Linxuan；KK 认可这一实现起点 | 争取 2026-10-20 展示部分代码，不要求全部完成 |
| 把工具和小 agent 写成可复用组件，允许其他图调用 | Linxuan 在实现中落实 | 随代码推进 |
| 探讨 Network Agent 与 Telemetry Agent 的分工 | Linxuan 提出、KK 认为可行；另一位同学姓名待核对 | 尚需与该同学对齐 |
| 查看 KK 已通过 WhatsApp 分享的根因分析网页及组件库思路 | Linxuan | 未给出明确截止时间 |
| 继续了解相关论文、分布式框架与合作方选择 | Linxuan 提出继续了解 | 尚未形成共同选型 |

仍需澄清的问题包括：AI 相比规则在何处有可测收益；第一段代码具体展示哪个闭环；容量接纳后如何同步实际资源状态；deadline 风险触发额外路径后如何与 transport 衔接；历史校准如何区分主机瓶颈、网络瓶颈与持续超额申请。

## 附录 A 转写存疑点与相关背景

| 转写或讨论项 | 本文处理 |
| --- | --- |
| `Lung Chang`、`Long trail`、`long grap` 等 | 根据容量工具、state/node/edge 示例，分别整理为 LangChain、LangGraph |
| `MTP`、`MCP`；`sense`、`sentence` 等 | 工具服务处整理为 MCP，service intent 执行系统整理为 SENSE |
| `wrong high`、`running` 等 | 三阶段中的运行阶段整理为 runtime |
| `hold` | 保留为原设计用词，同时记录 KK 建议改称 reserve |
| `Arabic` | Telemetry Agent 分工中提到的同学，姓名待核对 |
| `Xing` | KK 前 AT&T 同事的现单位，待核对；网页链接未包含在本次材料中 |
| `remor`、`remoral`、`remorad` | 可能为 Remora；论文题名、作者、机构及部署情况待核对 |
| `a cal` 等 | 可能为 Academy；结合已有背景作候选辨认，不能据此确认 |
| 50/100 的多路径例子 | 对应转写中的 megabits，整理为 Mbps；学习部分混乱的 GB/Gbps 数字不作精确转述 |
| Tuesday 与 Friday | Tuesday 按自我修正及会议日期推算为 2026-10-20；Friday 的具体日期未定 |

相关背景材料：[10 月 13 日 SciNet 会议](20261013_scinet_agent_implementation.md)、[已有框架讨论](../20261013_agentframework.md)、[三阶段 Network Agent 图与说明](../20261014_networkagent.md)。这些链接用于理解前序设计，不替代本次转写。

## 附录 B 原始自动转写

以下原样保留用户提供的文本，包含误识别与末尾的转写应用提示。

```text
What is in world and when we caught up an agent what can we do to say hey here are some rules that the agent can use to make its decisions?


Here are things that we don't know and we will ask the agent to find out additional information to be able to make the decision, right?


Yes.


Let me We'll give it all the other information to say, okay?


This is what I know so use all this information to make the decision right yes So what is the what how do we go about this?


Recently, I checked the Lung Chang and the Where does it come from?


I'm sure it's come the company not wrong academia.


It's it's a agent for free work, and a noise very palanar.


Now it's very popular?


Yes.


So you contain you where is this company?


I'm asking that because this is a department of energy project, right so we need to be the com publishes the public, the the code and its license is licensed by the MIT.


So I think it's fine.


Because the MIT.


And in the is is it from China?


No, no.


In the Chinese is missing with aide, it also the long grap this framework.


So I think it's fine.


Okay.


Okay. Good, let's safe.


I just want to not have these people complain about things.


I mean for our own research we can do whatever we want but yeah. . I think maybe we have firstly, we can use code based on this and it it can be changed.


We can talk too.


No, I don't redo something after having done some work already, but Long trail is a can of build your own agent.


It provides model integations, tools and a radio ag in a loop.


That means you can create agent and you can chorus of tools, you provide and a generate the answerers.


Harry here is the example for example, here is a chick capacity tool.


This is a tool, and we can write it into a function here What you do is here the records like link A, the capacity, and here is the capacity is 100 and the reserve is the eight hundred and the check, the either retire, the available, aability of this link. And then we use agent, we can use the agent that to create data.


Here is a model, we can shoot we can choose the model, and uh choose, we can add we can add the chick capacity, we write.


Of course, we can also use theP server , the tools prov provided by the MTP server.


Varas MCP serverCP server is a like the remote functions, like the remoter remote service.


And this service for getting some capacity?


Yes, yes, really.


Okay.


And we gave you the system prompt uh if the cor tool before answering capacityitch chains.


I mean course thebacity.


And the based on your answer on the are put and do not give the probity.


This is the system prompt , and so we can we can use the agent of we created and evocate and the past the mass ages.


We can ask can a accommodate an additional 300 MPP?


Answer.


So this is the workflow.


They see the before we create a single agent Okay, okay, you example of it provides lower level of the flow orchestration, allowing as to defy execution order, branches, loops, and estate.


There are three core concepts state, its the data share the cross, rotates, and the mode function that performance a west tape and age, it is determines which not excutes next so its aur is a graph such like a state machine?


Yeah.


Harry is an example.


We define the state here the requested the capacity and the book the capacity and the defeating this state This is a real capacity.


This is a node. Just a return, the state a bit of a variability with hasitated treat.


Every notick will have the state you can Aprilode and April age will get the state. And this sumption is choose next is a is an age. Do the conditional judgment. To if the request less than the availability, we can't return asape or just return the reject.


So this is applying a rule.


Yes, the rule being that if the requested capacity is less than available capacity.


Yes.


And state is like an ar . It has requested, it has available all a Like a message.ov because you you use a state that you change the data database.


Like you can't use a you can uh grew up a little bit.


The previous thing was the state or state is below.


No, below or up Where do you change the if you accept once you accept, how do you modify the capacity?


Herearing that here is not changes the capacory, just to accepted. . Okay.


But somehow I was wondering if state is a state variable that is being updated will be updated. And the I think the state will be modified under it will be applied to database to Okay.


Here is how should we build the graph created a graph and we addode.


First the grap and the aipp reject and between the pass and the ethegy, we add a we add an age here, we add an age conditional ages.


So if we give it a topology, yes, so yes.


A metotopology and then say, I want to provide capacity between no day and no Z. And there is something like a routing agent which says, okay, this is the set of hops to go fromord to nord z . And then that routing agent then calls uh link agent or something for each of the links in the part and then finds out what if the capacity is available and then comes back and says accept now, this is very much like what I would have thought of as a set of sub routines that are written. Sub routines a set of functions.


You didn't study for trend, so in fore trend we call themselves subr routines.


That was done, probably before your father was born.


I don't know.


But um you have a sequence of function calls, right?


Yes.


And ultimately each function applies some rule returns some answer, and in the process he build the final answer . What is the agentic about this?


Is it just that it's a bunch of functions?


Function function and a path you can add the other agent into the node that like here we create an agent, so we can invoke the agent, so we kindert this little loud call into a low node, so in our in the node we can core large language model And that lies language model can then come back and insert a agject.


Yes.


This is the whole, it works and uh another thing is this is a slide I did previously in the previous slide tonight.


I didn't I didn't Harry is I want to describe how to describe how to describe The . the process ofgation.


I divide it into three parts.


The stage the the high stage and the learning stage for the planning the me review let me record the the datawork agent we all gave the message from scheduling agent.


It includes a quote, "hold, commit a response, and the will send the service intent to send system and uh we need a monitor, there is a problem in the network, you know, we also we will repair by the sale, self repair, or or just the wrong high schedule failure and lead his scheduling agent to reschedule.


So this is the the interaction. Yeah.


So I divide into three parts first is planning.


It a case the code from the schedule agent and the fan room on the ager and with her offers. And then is a hold and a comet holdemporarily, and the commit to commit to the request to the sense system.


This is this and the wronging stage, it will it take to the deviation. The detect the metric problem, like wild short kids capacity and the props. Then we need to monitor when past there is therop in a single in the Swith bigger pass in the whe gang the whole past and the least every commitment on the pass, including ofart.


What do you mean by once?


That means a come is is, the Yes, but uh maybe it's not it's not currently it's not if not uh it's is Yes, yes. Then introd decided to repair or report.


If if you can fix it on.


So it just fixed it locally and soon repaired.


Yeah, but there is no failure if everything is working then uh the detecting of the deviation can be just because of congestion.


You mean the decting will cor consestion?


No. Detecting ofation, right?


That is our one in run time. Right?


Yes.


So the deviation may be detected because this is caused by congestion.


Yes, yes.


So you scan the pot Find out which hob in the path is congested.


Right?


Yes.


Then see if you can either read out or you reduce the load or some experiment or your reschedule, right't have to be failure.


Yes, yes, yes.


The be, yes.


It does not have to be failure.


It may be a slow cong.


We want to be able to handle that case also.


Yes, okay.


And if so can we, if we give these kinds of instructions,ilt LM write the agent code or being able to say I will deal with congestion.


I'll deal with failure.


I'll deal with the magion that does well all of that?


Yes, that's I want to I'll tell you what I want to say uh can be used to to analyze the logs or configuration or events or something and the gift to give the give the reason attribution to what is the problem.


And this is this is this is I can do.


And signally it can according to the problem, it do the plan like we like do the probe how, um probing what and uh, how to probe probe like this?


And the we can't gave the maybe does we can't give the A does. And uh signally and thirdly found out her the solutions.


I think this is the AI can do it's based on according to the he the information and the number from the history.


And thisraph of whatever can help us for writing up all those codes.


Yes.


Yes.


And uh the fourth party is to cover the defating from the scheduling. Scheduling agent, so you say the wrong high stage and further learning part the goal is to make the next promise more accurate next next plan. It appear reserved with a shade, it means either it will record the for the work floor, it a reserveved homarch capacity, and the it can learn if it allocated too much capacity.


It can learn yes, yes, inde, yeah.


Allocated to little capacity . Yes. Because, for example, you give two large capacity, like while hungryides, but it only used 20 gig you need to analyze the reason.


The reason may be from the host for example, for like the host proceeding speed or or for the disk, it choose low.


So you don't need to give the 100 gig.


You just gave it the twenty or twenty is the coming.


If the proper come from comes from the network, maybe you want to change the circuit or or something.


Choose an alternate but.


Yes.


Maybe this maybe this thing is also can be decided by AI.


I'm not sure. One of the things that we said was we want to also see how we can use multipad. . Yes.


And over provision yes more than one part.


If if there's one path that is limiting, but there's another path, then we will divide the traffic between the two parts. Right?


Yes.


And the agent can help to split the traffic and then we have to figure out how the transport will pull them together.


Can you explain this problem again?


Sorry?


I'm I'm not not understand.


So I made a reservation for 50 megab.


Yeah, yeah, yeah.


Okay.


Yeah.


And the capacity that is allocated on parts one is 50 meg for this experiment . Starting at ago to Z. Then the experiment says, hey, no, I want no hundred megab. ath one doesn't have hundred megabits.


But there is another part too, that can go from A to Z and what I want to do is combine part one in part two to get to give the hundred megaby capacity that the experiment needs no.


I see my oh, okay.


I see the multipass.


My my question you you' we don't have aI, how it a bit how it is decided we have a transport protocol that's okay I will ask the network layer and ask for all the possible parts to go from A to Z. And then I will take those list of parts and set up a multi path connection with one subflow going from A to Z on part one and another subflow going from here to z on parts two, and then the transfer protocol will then say, I am going to split the traffic between part one and parts two, depending on how much capacity there is in part one how much capacity there is in part two, and if it turns out, it is divided unequally, I will divide my traffic unequally between part one and part two.


So I see if we already have the truck protocol, while with why we neither EI here?


What is what is the advantage of AI here to do the dissaging?


I want to dynamically be able to find the path.


I want to dynamically tell the transport protocol.


Now here is another addition parts that is available.


You are not meeting your requirement for the deadline.


You need more bandwidth?


Here I amm giving you additional bandwidth and an additional part you can set up another sub floor, and then ere I can say okay, this is how you use both those subfl floors to send your traffic.


So yeah, you's used to provide more new information . Possibly.


Right.


I mean, this can all be done using rules.


Now, the question is, where is the line between AI that is asking an island to do this and making decisions by an agent that decides hey, you are not able to meet the deadline.


You need additional capacity and then the agent says okay, let me go find additional capacity . And it asks other agents to find an additional path to go from Italal Z. And finds out how much of additional bandwidth is available. And then, if that is enough comm meet there, deadline, using the existing part in this new part, then it returns saying hey, use this additional part.


Okay, I see.


I was saying this apart.


So if we can code up something like this, right, with this lang graph or whatever.


Yeah.


And we walk through the cold with these people on Monday.


I mean on Tuesday, even little pieces of it, not all of it.


You mean I the two write the codes, rather some store code to sh instead of sitting and waiting for the hackathon to do it, right?


We can we can write code ourselves, right?


Yes, yes.


And then say, this is what we've done.


What do you think?


H?


And they're not I do not know if they will give us any feedback, but that will give us a head start of saying here we have already done some of this good.


I see, yeah..


We don't have to sit and wait for them to schedule the hacketon to write the code. For the code when you prison next Tuesday?


We need to write on code to present you next of Tuesday, right.


On Tuesday.


Yeah.


Might be worth while if it is possible, even if it is some pieces of it even in which not all of it.


I'm I'm just saying that we can get ahead of this curve of sitting and waiting for them to tell us what to do.


Okay, I say. Okay so and then on Friday if the if there still stop to be done, we can flash out additional pieces and then we can we can do whatever we want for some time and if we wanted to drop off, we can drop off then.


We don't have to sit for three four hours with that. But this will get us the lavorated of s hey, we've got the lead you guys follow.


Okay.


Can I see the more we operate in that mode, the more we will be in control of what to do and the more we can then write our own paper.


Let's see, yes.


Okay.


Let me let me talking.


Okay.


Let me keep talking.


So this parizing could be a calibrator and the tribute to figure out the reason, you know, for short, why the the laws, the reason is from host or the network and the makes the different decisions, makes a different strategies.


According to the reasons and will apply apply to this as finding the root cause Yes, they calibrate and attribute it.


It's like finding the root cause.


Yes.


So this is this two stage planning wrong high and learning there is a graph for the different philosy state.


So I'm I'm planning to rather cold based on this figure.


This is uh no, it's non protocol but.


It's it's the execution graft for the planning stage.anning agent So we have a third hand and have an end and here is aar because we have because we need to receive different in the commands for scheduler.


They say the quote, you will receive quote for where you variadated variadated the the request and then we ref used theale, refre the information we have from the database from the IT or yes, yes, from tele have a culture for the telemetry should the way start to implement it I don't want to do everything all at the same time, but my belief is that different is possible we should be in control of the network agent and the telementary agent.


I see it.


I think this work can be divided.


Maybe I can do the naturalog agent and the Arabic can do the titament agent.


Yes, is durable.


I see.


Lets see the fresh you stale so for the fresh maybe it also can be controlled by AI to avoid a too frequently or the information are too old.


Decide how frequently we need to refresh the state.


Yes. We might refresh it more frequently if there's lots of changes, less frequently, if there's less few changes . Yes.


And then, where you find the placements, according to the current and itwork later?


And the we estimated the Finn high and responsed to return the offers.


Here also, maybe we need to consider the over provision.


Right.


We use the fixed rule, fixed rule that you to compute the author first, and then we use the AI to consider the over provisiongen and the modify the offers, maybe to say that it is unnecessary to allocate that much capacity.


Yes, right.


This is the cold and then we have hold also this is this is for a preliminary commit before you make the actual commit.


Yes.


It's like the two phase.


Yes.


Just like a So we call it reserve and commit rather than hold, we call it reserve, but not necessarily commit, and then after that, once you decide you commit. Yeah.


So here we are have the pending that status and uh keep the world colleg updated the local middle gager, and the way or the cynism and the c service intent to the sentence, and get the result of success or failure, substace, it will rarely change cover the changes. Euphenure it will grow back.


Yes.


And of this three things the mostly the and then we can eat we need to rethe the capacity and really place the answerring it What do you mean by play on circuit?


Just send a service intern to send andicate the result.


Oh, this this is request found the request to sends yes. To come to uh set up the circuit What does place on circuit mean?


Who you found the circuit so this part should be beside the locally maybe you want to reuse a warmer circuit or proagging a new one.


We're trying to find a circuit So the following the user then we have modified and uh.


So this is the planning stage and the for the wrong high stage, this is uh another execution graph . First, we create a classify event to dedict that the derivations.


Maybe it should be an agent. In the in the node.


It's finding root cause, right?


Yeah.


I mean classifying and then after that you want to basically find the root cause.


It's not enough any the course it's just found that the there is a problem but I don't know what happened.


What did happen?


Just or either can catch of the deadline or something.


When we sky the past and uh we make such uh judgment that canle could repair the daylight.


If the can't durable its it is if it is it a durable in locally , if so, we cannot prepare it in local, and if it is too late, we shall see is it is at risk.hedule agent must reschedule the the work flows and the repair.


It's a repaired or other risk and the report . At risk meaning, it's not possible to repair.


Yeah, for for the work for to work agent.


Failure recovery.


This is start failure recovery. Right?


Yes.


For the schedule agent, it received the at rates, so I so we all reschedule the rock of flow.


Reschedu So is the for the wrong tily this is the learning stage.


Firstly, theing recorded that means we combine, we banned the comedes and the records.


This part of this part of this is part of talking about the with just the compare achieved and the reserve the data.


Where right compare between achieved and reserve data, so you're saying that you want to compare between requested capacity and what was actually committed the way major, yes.


What you committed, right?


Commit is what is a request.


Oh, so the reserve is committed versus what was the actual result?


Yes, yes, okay, okay.


That comes from calimetry.


Yeah, yes.


What was e?


Okay.


So we calibrate carb remove carb means if you just like I said, if you I gave you 100 gt I thought you only use fifty gigabytes.


So next time I will give you the 50 gigabytes, just to just to times the collibrate rate.


Well it depends, I think you want to keep a history of what was the result and what was used?


So that you can learn whether there's always an over provisioning or over asking for too much right that's what you're trying to learn Oasking that is somebody is constantly asking for not more bandwidth than they need.


Okay, okay.


Yes.


So we found a found the look horse, if if there if he is too slow or or failure, just like to evaluate for this workflow.


After it finished it.


And then we will do the planet adjustment. To adjust like I see, maybe we can if if we have a calibate bottle, we need to update 8 and and use it.


Maybe we can change the utzation or or change change anotherroc or change another compode, another host, according to the reader.


Great, if the if it is not enough, you have to plan changes to.


Okay. We apply the adjustments.


So I illegially we can start from history graph and the began to write a code.


And then after that we become extended some other more complicated functions..


I I agree.


I I'm no, not knowing too much about this.


Uh, this seems like a good start for me.


Okay.


When we do it we learn.


Yes, we have cable changing on the and improving it.


Right.


I talked to a guy who I used to work with many years ago in AT&T. He's now uh in in uh Xing. And he is building agent systems for finding root cause for failures. And I sent you on uh WhatsApp a link to a webp page of his. Uh yeah, I see it.


And uh at the very bottom of the page is this overall architecture he thinks about.


Oh, and in there in the right bottom, the go to the in that right bottom over here, he has a bunch of libraries here, okay?


That he can use to generate agents automatically based on some tool sets that he has of how he can analyze, detect failures, and so on, so I just want you to it's you know, he's doing everything best on time series.


That is not our focus.


But he seems to have some way of creating agent Sacramatically so go back to the top he has a presentation and every time he updates the presentation , okay?


He has a agent that creates a automatic video. Of his presentation.


English and Chinese, so you can look at the video.


Yeah.


And as he keeps adding to his work in the presentation , the video is automatically generated, but, you know, that's minor, but the thing is he builds a library of these agents, so as we build these agents that you are talking about rights, we can put that those different little agents into a library so that later on we can utilize them in different graphs that we end up having as a core primitives, wherever it is appropriate to have a core primitive. Was the meaning of different literature agency in?


So these agents that you were looking to build rain, so go back earraph raph. Different execution graphs that you were talking you were showing.


Right?


Yeah.


So here, uh these execution graphs involved mayraw some tools and agents.


Yes.


So I'm saying you write all those tools and agents, okay?


But then you can then see when you need to reuse those tools and agents in other execution graphs.


Yeah, they can reuse.


They can be remove.


So for allowing that reuse it might be good to have it in a library.


Oh yes, Indian, yes. Like that I'm thinking.


Yeah.


You're write it first and then make sure you write it in such a way that subcomponents that you developed can actually be invoked and used by otherangraphs also. As you go along so that you don't have to redo everything each time.


Yes, yes.


Regent.


I see.


Two librian agent library.


Yeah, yeah.


Yes, I see.


And uh I know under paper, it's This paper is uh also ait occas in the freework. Deployed I think it also can be nerd.


They also use uh I'm a little forget.


I I remember that.


I also use eight in thatube kept asking users to uh two inference some promters and some of me.


So you have the account toify are these people?


They are from John Hopkins?


Yeah.land, they say this this remor agent firm remoral had already deployed for in meta for several years, two or three years.


I say, uh we can check what we can learn from from.


And uh and in the website of uh miss, the also mention that the agent of remorad . They say there is theitful and the distributed the agent across this is what this lady was asking us to also learn about Miriam.


Yes, and here it estate a cal is a is agent the middle, not a pear alternative to elaborate like like the femata, like a long graph.


So I think we compute fur to based on long graph and then we can use a cal to externate tube, distribute the agent.


This is what I thought.


They are not a conflict.


This is building on it going from a singles central environment or something that is distributed in cooperative across these agents in different sites.


I think so.


We can we have we can see what opinion of Korea.


What what a what a they are going to use the agent of remark.


Okay.


That's where I want to share.


Okay.


It helps me understand what all this technology is.


Yeah.


Okay.


Little by little, I am absorbing by osmosis.


I also I'm also learning.


Yeah.


Okay.


Good.


All right.


I will update you to.


Okay.


All right.


Thanks, okay.


Okay, bye.


Okay, talk to you later.


Okay, bye professor.


Okay, bye. 




Was this transcription useful or not useful?
```
