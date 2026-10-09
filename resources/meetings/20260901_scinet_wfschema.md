# 2026-09-01 SciNet 会议：workflow schema 与 SENSE 对接讨论

> 材料来源：会议录音自动转写（无时间戳、无可靠 speaker diarization）+ 用户提供的参会者截图 + 用户补充的会后 KK 观点。
>
> 参会者（据截图及用户补充）：Linxuan Zhong、Harvey Newman、Kadangode K. Ramakrishnan（KK）、Sourabha Bharadwaj Bangalore Murali、John Graham、Rafael Ferreira da Silva（中途离场，未出现在截图中）。
>
> 整理范围：不复述 PPT 本身的内容或汇报过程；只记录参会者针对 PPT 提出的观点、修改意见、质疑、纠正，以及脱离 PPT 的其他讨论与会后观点。
>
> 转写质量说明：自动转写中人名与专有名词误识别较多。后续仅在上下文足够明确时归属发言人；不确定归属、术语或解释将明确标注 `[待核对]` 或 `[推测]`，避免把推断写成事实。

## 会中材料

- Harvey 提供：[Coffea-Casa: Building composable analysis facilities for the HL-LHC](https://arxiv.org/html/2312.11485v1)。Harvey 在会议后半段建议重点看其中从用户群体角度描述 analysis facility 工作方式的 Figure 3；相关讨论将在后续章节记录。



## 一句话结论

会议认可了在 WfFormat 上增加 workflow-centric deadline、priority 和 transfer information 的方向，但没有确认应由本组维护完整 network
topology schema；更可靠的路线是先以 ServiceX、Rucio/FTS 等真实但缺乏 infrastructure awareness 的系统为 use case，核清 SENSE
现有能力，再让 agent 负责 workflow 需求与有限网络资源之间的查询、协商、监控和调整。KK 会后特别提醒，本组不应把会上所有设想都揽为自己的工作，
需要把广泛讨论与本组当前任务分开，保持聚焦。

## 一、开场即明确：workflow 提需求，网络判断并回应

在 KK 介绍本次汇报目标时，Harvey 首先纠正了一个容易混淆的表述：这里要描述的不是“workflow 对网络要求网络必须做什么”，而是
**workflow 自身需要什么**。网络侧服务收到这些需求后，还要综合 workflow 的优先级和其他属性判断能提供什么，再向 workflow 返回结果。
因此，workflow 与网络之间最终应是一次交互，而不是 workflow 单方面声明、网络照单执行。

KK 接受了这一纠正，并主动说明当前草案还只是**单向 API**。这版工作主要做了两件事：

- 找出现有 workflow 描述中缺少、但网络规划需要知道的信息；
- 增加 workflow deadline 等时间要求的表达。

KK 同时明确了尚未处理的部分：网络实际能力必须反馈回来，workflow 的要求与网络供给之间可能需要多轮协商；当多个 flow 竞争资源时，还需要算法决定怎样分配。未来可以由 agent 承担协商和分配责任，但 agent 具体怎样做、本轮并没有设计。【K-1】

## 二、对 WfCommons 背景部分的反馈：先分清“表示与生成”和“运行时管理”



### 2.1 不要把 Rafael 等人的既有工作说成自己的工作

在学生介绍 WfCommons / WfFormat 既有工具链时，KK 给出的第一个修改意见很具体：slide 和口头表述中的 **“we / us” 应改为
“they / them”**。这一部分是在复述 Rafael 及其合作者已经完成的工作，而不是本组的贡献。本组自己的扩展必须与既有工作明确分开。

KK 也提醒，这一段的目的不是向 Rafael 等作者“讲授”他们自己的系统，而只是快速核对本组对既有工作的理解；真正需要讨论的是后面的网络扩展。

### 2.2 Harvey 一开始不清楚 WfFormat 所处的抽象层

Harvey 追问，WfFormat 是否是在读取已经执行过的 workflow 日志，再从中抽取高层特征，以便生成具有相似数据特征的 synthetic workflow
或 benchmark。他之所以困惑，是因为科学团队在运行 workflow 之前通常已经知道：

- workflow graph 和执行步骤；
- 每一步涉及的数据量；
- 大致执行时间；必要时还可先运行 10 或 100 个 event 来估计给定 portfolio 的执行时间。

因此，从 Harvey 的角度看，项目真正需要外部系统帮助的不是重新告诉科学团队“workflow graph 是什么”，而是多个请求到来后怎样裁决、
怎样分配有限资源、怎样平衡不同请求。他一度要求先跳过若干背景页，等看到后面的抽象再回来讨论。

### 2.3 Rafael 澄清：统一表示是为了得到真正可缩放、可重复的 workflow benchmark

Rafael 解释，不同 workflow management system 各自用不同格式输出日志，跨系统比较时非常混乱；WfFormat 的作用是提供一种不依赖
Pegasus、Parsl 或其他具体系统的共同表示。它受到 Common Workflow Language（CWL）的启发，但目标不只是记录怎样执行任务。

他特别区分了“一个 workflow application 的一次 execution”与“benchmark”：只有一个固定实例不能算真正的 benchmark。WfCommons 从真实
workflow 提取结构规律并形成 recipe，再用 recipe 在保持原有结构特征的前提下扩大或缩小任务数和数据量。例如做 weak/strong scaling 时，
它不会简单随机生成更多任务，而是生成仍像原应用的 workflow。

Rafael 还补充了几点，以免大家把这套工具只理解成 simulator 输入：

- 生成的 workflow 可先以 WfFormat 这类描述形式存在，再转换到多个 workflow system；他在会上说当前约支持九种系统；
- 执行时可使用可控的 CPU、GPU、memory、I/O stressor，因此能够比较不同 workflow system、基础设施或硬件条件；
- 同一套表示既可供 simulator 使用，也可生成在实际系统上运行的 benchmark code。



### 2.4 Harvey 关心的则是运行时的 process-oriented 更新

Harvey 随后把问题拉回实时运行：初始 workflow 特征和 time-to-completion 只是估计；随着新请求进入，或执行进度显示系统状态与预期不同，
原来的估计会变旧，系统必须持续更新 time-to-completion。他把这种方式称为 **process-oriented approach**，并以早期 LHC computing
simulation 为例说明：启动任务、跟踪预计完成时间，再根据新事件修正预测。

这并不是对 Rafael 解释的直接否定，而是两人关注的层次不同：Rafael 说明的是怎样统一表示 workflow、生成可控 benchmark；Harvey 追问的是
这份表示进入真实运行后，系统怎样根据实时变化管理 workflow。Rafael 因而再次强调其框架的第二部分是 benchmark generation，
并不等同于完整的运行时资源管理系统。

### 2.5 对本项目的直接含义

KK 将这段讨论收敛为：WfFormat / WfCommons 的价值在于可以生成结构真实的 synthetic workflow，再把它送入 simulator 或实际执行后端；
即使本次暂时只讨论 API，这种能力以后可以成为 agent 可调用的工具。若目标 simulator 使用其他输入格式，也可以仿照已有工作增加 adapter，
将 WfFormat 转成后端需要的格式。转写中此处提到的具体 simulator 名称无法可靠辨认，标为 `[待核对]`。

在这一点基本澄清后，KK要求加快背景部分，尽快进入本组提出的 network-related extensions；他希望 Rafael 判断这些扩展对 WfFormat
是否有价值，也希望 Harvey 和 John 判断同类能力是否已经存在于 SENSE 中。

## 三、Harvey 对 network abstraction 的关键纠正：不要从底层拓扑重新推演网络

学生说明现有 WfFormat 没有记录文件经过哪些机器和链路、网络拓扑、链路容量及 SLA，因此设想增加这些信息。Harvey 随即指出，
这套设计必须先回答一个更根本的问题：**workflow 所需的网络抽象究竟是什么**。

Harvey 认为，SENSE 面向用户提供的是跨多个 network domain 的 virtual circuit。相对于 SENSE 而言，本项目的工具属于 user-side tool；
它不应该重新构建完整 network topology，也不应从最底层的 link、capacity 和连接关系开始自行推断网络行为。更合适的做法是：

- 以 virtual circuit 作为主要交互实体；
- 获取 virtual circuit 随时间变化的实际特性；
- 将它连接的 endpoint / infrastructure 作为必要输入；
- 研究怎样把 workflow 映射到不同的可用网络条件，而不是复制一套 network engineering 系统。

Harvey 特别提醒，一个 virtual circuit 可能跨越多个 link / segment，也可能存在 multipath；因此把网络简单还原成一串固定链路，
未必符合 SENSE 实际提供服务的方式。用户也不是“要求网络必须满足”，而是向 SENSE **提出请求**：SENSE 可能创建新的 virtual circuit，
也可能激活已经存在的结构；如果资源不够，它还可能拒绝或提供不同结果。

他的直接建议是：团队越来越需要与 SENSE 团队进行专门讨论，先弄清本项目工具与现有 network engineering 的职责边界。
John 表示可以展示 SENSE orchestrator 的 topology diagrams，帮助大家理解这一层抽象。

KK 回应说，团队已经花了相当多时间阅读 SENSE API，只是本次时间不一定够讲到相关 slides。当前目标正是把 WfFormat 扩展与 SENSE
已有表达“harmonize”：如果某些能力已经存在就复用；确有缺口时，才考虑谨慎扩展 SENSE API，而不是另造一套平行系统。

## 四、对两套新 schema 的核心讨论：Platform 表示供给，Campaign 表示一次运行的要求

学生提出两套新 schema，并扩展 WfFormat 的 specification / execution。会上真正受到关注的不是字段本身，而是它们能否建立
**workflow 需求与网络供给之间的协商关系**：

- `WfPlatform`：描述相对稳定的平台侧信息，如 domain、site、node、link、route，以及 link capacity / latency；
- `WfCampaign`：描述某一次 workflow run 的 SLA 和资源绑定，包括 submission、deadline、priority，以及抽象角色到实际资源的映射；
- WfFormat `specification.constraints`：描述应用固有、通常不随每次运行改变的时间约束；
- WfFormat `execution.transfers[]`：记录实际文件传输，包括实际 source / destination、开始结束时间、传输量、RTT 等观测值。

KK 后来把 `WfPlatform` 与 `WfCampaign` 的关系概括为：一边是网络及平台能提供什么，另一边是某次 workflow run 的 SLA；agent
在两者之间协商，形成可执行计划，再申请相应带宽。目标至少是使 campaign 中指定的最坏情形 deadline 得到满足。

不过，Harvey 对 `WfPlatform` 的边界仍持保留态度。团队希望避免描述完整物理 topology，只保留 source、destination、经过的 link 及其 capacity，从而同时兼容 virtual circuit 和 IP best-effort path；Harvey 的意见则是，既然 SENSE 已掌握网络和 virtual circuit， 就不应在 workflow schema 中重复构造一套过细的网络模型。【K-2】这里形成的是**待与 SENSE 团队核对的设计边界**，而不是已经定稿的 schema。

## 五、Deadline 不能只有一个数字：硬约束、弹性与多级时间要求

Harvey 在看到 `WfCampaign` 后立即提出，多用户环境中的任务至少存在不同服务类别：

- 有些任务具有不可错过的 hard deadline；
- 有些任务虽有 deadline，但允许在一个时间窗口内完成；
- 有弹性的请求更容易与其他任务共同安排，也更容易被网络接受；
- 即使任务有 hard deadline，也仍需讨论它是否天然拥有最高优先级；否则系统就必须拒绝请求或进入协商。

KK认为这正是本组相对于现有 WfFormat 要增加的关键信息：不仅表达整个 workflow 的 deadline，还要能逐层表达 task completion deadline
和单次 data transfer deadline。草案把时间要求分成两类：应用本身固有的约束放入 WfFormat `constraints`；某一次 run 特有的 deadline
和 priority 放入 `WfCampaign`。

Harvey 进一步强调，真实系统不是填完 deadline 就结束，而是完整的 **request → reply → adjudication → optimization** 过程。 系统要从最简单的 hard-deadline / priority 规则起步，逐步发展到根据复杂、多维的 success metric 在竞争请求之间作判断。 网络占用越高，协商越重要；当用户提出不可满足的请求，例如要求 10 Tb/s，服务不能假装可以完成，而要明确拒绝或返回可行范围。 用户也会依据实际结果学习什么请求是可满足的，并重新评价什么样的服务水平算成功。【K-3】

Harvey 因而提醒，这两套 schema 的产出不能被称为完整“solution”。更准确的定位是：它们是让系统逐步从简单表示走向更真实、
更能服务 science program 的**下一步**。未来若反复证明现有容量无法满足合理需求，结果甚至可能成为申请增加网络容量、修改 requirements document 的依据，但那是更后面的治理和资源决策。【K-4】

## 六、John 对 SENSE 现有能力的澄清

John 说明，SENSE API 已允许用户：

- 请求 endpoint 之间的 path 和一定数量的 bandwidth；
- 查询 path 的参数与各处 QoS 状态；
- 当某些 segment 容量不足时，尝试绕开瓶颈寻找能够满足带宽要求的路径；
- 对 path 做实时及周期性测试，观察 packet loss、congestion 等统计信息。

他同时强调 SENSE 是 **multi-domain orchestrator**。ESnet core 本身可能有很好的 QoS、几乎没有 loss，但流量一旦离开 ESnet core， 进入没有 QoS 的 best-effort domain，端到端保证就会改变。此时可能需要 host-level QoS 或 Linux traffic control throttling， 把发送速率控制在已知能够稳定工作的上限内。John认为 agent 可以承担这类根据跨域状态进行调整的职责，而不是让用户一开始就索取全部资源， 最终造成混乱。【K-5】

这段说明也澄清了 schema 与 SENSE 的互补关系：SENSE 已能提供 network-centric QoS / SLA、当前 path 状态和带宽服务；本组希望新增的是
workflow-centric 信息——多个 workflow 的整体 deadline、task deadline、transfer deadline 和 priority——再用这些信息在竞争 workflow
之间做仲裁。哪些字段应该留在 workflow 层、哪些由 SENSE 直接查询，仍需进一步对齐。

## 七、Bandwidth、latency 与观测值：不要混淆容量、需求和实际表现

围绕 bandwidth，会议实际区分出三类量：

1. 平台或路径能提供的 capacity / available bandwidth；
2. workflow 根据 file size 和 transfer time budget 推导出的 required bandwidth；
3. execution 中按实际 bytes 和 duration 计算出的 achieved throughput。

这一划分的价值在于，agent 可以比较“需要多少、网络能给多少、实际得到多少”，并据此协商或调整计划。Harvey和 John 同时提醒， 系统不必由 workflow 重新声明网络中已经存在的 link 及其 capacity；SENSE 可以提供当前状态，历史和实时观测则可帮助判断表现不佳来自 end system 还是 network degradation。【K-6】

谈到 latency 时，Harvey 追问是否确实存在以 round-trip time 为直接要求的 use case。他不赞成在本项目中重新推导已经成熟的 TCP throughput、RTT、packet loss / congestion 关系；这些标准网络行为应作为已有知识或测量输入，而不是重新建模成项目贡献。【K-7】

学生展示的 space/time demand distribution 得到了较积极的反馈：若能把每次 transfer 映射到 path、link 和 time bucket，就可以识别
哪个 link 在何时成为 bottleneck，并在 workflow 提交前检查 deadline 是否可能满足。KK认为这类表示可帮助 agent 调度不同 workflow、task
和 transfer，减少共享资源 oversubscription。但这仍只是提供调度所需输入，并没有在本次会议中定义实际 scheduling algorithm。

## 八、Rafael 的评价：方向有用，但应继续找相关专家核对

KK 在汇报末尾再次说明，本组并不执着于自行创造新 API：如果 SENSE 已有足够能力，就直接使用；只有现有接口不支持多 workflow planning
和 scheduling 所需的信息时，才谨慎补充。他请 Rafael 判断给 WfFormat 增加这些内容是否偏离方向。

Rafael 的反馈是这套扩展**看起来有用、方向没有 off base**。他还提到自己与 University of Hawaiʻi 的 Henri Casanova 合作密切，
可以与他讨论，并认为 Henri 可能愿意帮助。转写将名字识别成 “Harry Kazanova”，此处依据 WfCommons 语境校正为 Henri Casanova，
但是否会正式参与本项目尚未确定。

Harvey 随后再次把问题放回真实科学组织：每个 experiment 已有自己的 analysis architecture 和 production architecture，但这些系统通常几乎
没有 network awareness。项目要做的不是替代它们，而是增加 network / infrastructure awareness，使原本默认“提出请求就会被满足”的
workflow 请求，在有限容量的 network of networks 中变得更可满足、更现实。

## 九、下一步应直接邀请 SENSE 核心人员，而不是继续猜接口边界

John 建议安排一次有 **Mohammad Sada** 和 **Tom Lehman** 参加的讨论，让他们完整说明 SENSE 的现有能力。尤其需要了解 Mohammad 已做的
Kubernetes SENSE operator：据 John 介绍，它不只连接 SENSE，也能连接 FABRIC、FABFed、NRP 等 testbed / infrastructure，形成较统一的
资源池或控制入口。转写中部分 testbed 名称识别不清，具体支持清单需由 Mohammad 本人确认。

这项建议实际上延续了前面的职责边界问题：在决定 `WfPlatform` 应描述多少网络细节、是否需要扩展 SENSE API 之前，应先让 SENSE 开发者
展示 orchestrator topology、path request、监测及跨基础设施控制的完整流程。否则本组很可能重复实现已有能力。

## 十、Harvey 给出的第一个具体 use case：让 ServiceX 具备 infrastructure awareness

Harvey 认为，讨论最终必须落到“用户组织中的真实 workflow 怎样运作”，不能只停在通用 schema。他在 chat 中提供 Coffea-Casa 论文，
建议团队先看 Figure 3，从 analysis facility 和用户群体的角度理解现有架构。论文页面显示 Figure 3 是 Coffea-Casa Analysis Facility 的总体
schema，并展示了与 HTCondor 等外部计算资源的结合；但 Harvey 在会上真正想强调的是：**先理解一个已有系统，再寻找它缺失的
infrastructure awareness**。

他以 HEP analysis 为例说明：官方 event representation 为控制数据体量，只保留一组基础 quantities；不同 analysis——数量可能达到数百个——
还需要从更详细、更大的 event format 中补取各自需要的 quantities。`ServiceX` 负责按 analysis 需求生成和缓存这些 column / data component，
但 Harvey 指出它本身并不了解底层 infrastructure。

因此，Harvey提出一个可以具体化的项目 use case：

> 让 ServiceX 具备 infrastructure awareness，使其能与 SENSE 交互，在既有 analysis architecture 中更好地完成用户 workflow 或其中的任务。

这里的重点不是重写 ServiceX，而是在它已有角色上增加网络和基础设施信息，使 data delivery 决策不再默认所有资源都随叫随到。

Harvey还引用 Coffea-Casa 论文对 HL-LHC 数据增长的估计：论文写的是相对当前约增长 **100 倍**。他本人明确表示不确定这个数字最终是 10、30
还是 100 倍；可确定的只是未来需求会显著高于当前，有限容量下的 allocation、priority 和 deadline balancing 会越来越重要。

## 十一、第二个现实入口：Rucio / FTS Data Movement Manager 与实时监控

Harvey 随后提到一个已经做过部分整合的 data-movement application。转写将名称识别为近似 “XRootD–Rucio–FTS workflow”，
准确组件组合需 `[待核对]`。其中已有一个 **Data Movement Manager**，会与各组件通信，并根据项目可用时间和目标动态启动所需数量的 pods。

KK 追问这套系统是否表达 overall project deadline 和 individual task deadline。Harvey 的初步判断是当前更接近 task-level deadline，
具体机制应询问 **Diego** 与 **Ashay**（两个人名均按转写记录，完整姓名待核对），因为他们才是 Data Movement Manager 的专家。

Harvey 对 `Rucio` 的概括与对 ServiceX 的批评相同：作为高层 data-management tool，它不太了解 infrastructure，容易假定自己发出的需求会立即得到满足。 项目需要让来自 experiment 的 requirement 先交给了解 infrastructure 的 agent，再由 agent 与网络侧协商。如果请求无法满足，agent 应返回现实能力， 而不是让上层一直等待一个默认的“yes”【K-8】。

John 补充，现有 **Prometheus exporters** 会持续监控已经建立的 path 和正在进行的 transfer。系统可以查看 live transfer data，发现性能下降、
path 异常或 pod 行为失常，再发送新命令调整执行。这给 agent 提供了一个非常具体的闭环：

```text
观察 path / transfer / pod 指标
        ↓
判断当前计划是否偏离目标
        ↓
重新协商、调整 pod 或改用其他执行方式
```

会上认为，可以把 AI agent 接入现有 Data Movement Manager，而不是另起炉灶重建所有 data movement 逻辑。这只是一个 application-level
切入点，不代表会上已经决定最终 agent 架构。

## 十二、Harvey 要求把研究问题变成可观察的容量冲突

Harvey 反复强调，需要选择一个足够具体的现有系统，实际看清它“做了什么、没做什么”。以 Rucio 为例，应先观察它怎样提出请求，
再指出它怎样缺乏 infrastructure awareness、怎样默认请求会得到满足，最后研究如何让它面对一个**总需求超过 network-of-networks 有限容量**的真实环境【K-9】。

在这种环境中，本项目才会遇到有研究价值的问题：

- 哪些请求先得到资源；
- hard deadline 与 flexible deadline 怎样共存；
- 当容量不足时怎样协商或降级；
- 怎样根据执行期观测重新调整；
- 怎样定义并改善整体 success metric。

这也解释了 Harvey 为什么不满足于 schema 本身：schema 只是把需求带进系统；真正的问题是多个现实 workflow 同时到来时，系统如何用有限资源
做出可验证的决定。

## 十三、会议收尾与建议的后续动作

会议已经超过原定结束时间，因此没有继续讲准备好的 SENSE API slides。收尾时形成或提出了以下后续动作：


| 后续动作                                                                        | 来源与状态                       |
| --------------------------------------------------------------------------- | --------------------------- |
| 安排 Mohammad Sada、Tom Lehman 参加一次专门讨论，展示 SENSE 的完整能力和 Kubernetes operator    | John 建议；具体召集人和日期未定          |
| 展示 SENSE orchestrator topology diagrams                                     | John 表示可以提供；本次未展示           |
| 继续核对 WfFormat extensions 与 SENSE API 的重叠和缺口【K-10】                           | KK / 学生后续工作；本次没有得出接口定稿      |
| Rafael 与 Henri Casanova 讨论 schema / workflow benchmark 方向                   | Rafael 表示可以联系；是否落实待确认       |
| 阅读 Coffea-Casa Figure 3，并以 ServiceX 为一个 infrastructure-awareness use case   | Harvey 建议；拟在后续会议继续          |
| 了解 Rucio、FTS、Data Movement Manager 与 SENSE 的既有集成，并询问 Diego、Ashay            | Harvey 建议；具体系统名和联系人全名待核对    |
| 查找 2022 年由一位名为 Frank 的报告者所作的 Rucio / SENSE / FTS integration prototype talk | Harvey 会末现场找到；报告者全名及准确标题待核对 |
| 下次继续讨论 analysis facilities、ServiceX、Rucio / FTS 及其与 SENSE 的关系               | 会末口头约定                      |




## 十四、会后 KK 对本组范围与参会方式的提醒

KK 会后单独强调，与 Harvey Newman 和 John Graham 对接并不容易。会上会出现多种立场和不断扩展的设想，但**本组不是这个项目唯一负责干活的人，
也不应把所有工作都揽下来**。因此要有意识地区分：

- 这些会议上各方讨论了什么；
- 本组已经决定、正在实际推进什么。

KK要求本组继续聚焦当前工作，不要因为会上出现许多观点就不断扩大自己的任务边界。他也解释，这正是自己通常不喜欢让学生参加此类会议的原因：
多方观点并存、讨论方向频繁变化，可能让学生感到不安并分散注意力。

但 KK 并不是要求忽略会议反馈。他明确认为 **Rafael 的输入有用，后续应当记住并吸收**。因此他的完整立场是：保留 Rafael 对 workflow
表示与 benchmark 的专业意见，同时不要把 Harvey、John 或其他人提出的每一个方向都自动转化成本组的任务。

用户提供的 KK 英文原话如下：

> It is not easy to interface with Harvey Newman and John Graham. We are not the people responsible to do everything for this project as the sole people doing the work either. So, let us remain focused on what we are doing. Separate out what goes on in these meetings vs. what we are doing. That is why most of the time I don’t like including our students in these meetings because it can be a bit disconcerting and distracting to listen to the discussion with various points of view. Rafael’s input was useful and we should keep that in mind.



## 待核对项


| 项目                                | 当前记录                                    | 为什么待核对                          |
| --------------------------------- | --------------------------------------- | ------------------------------- |
| 前半段提到的目标 simulator                | 名称未记入正文                                 | 自动转写近似 “Astras”，无法可靠识别          |
| Kubernetes SENSE operator 支持的基础设施 | SENSE、FABRIC、FABFed、NRP 等               | 部分名称受自动转写影响，应由 Mohammad Sada 确认 |
| Data Movement Manager 所属的准确集成     | `[推测]` XRootD / Rucio / FTS 相关 workflow | 自动转写严重失真                        |
| Data Movement Manager 专家          | Diego、Ashay                             | 只听清名字近似音，需核对完整姓名                |
| 2022 integration prototype talk   | Rucio / SENSE / FTS 相关；报告者名为 Frank      | 标题和报告者全名均未听清                    |


---

# Rucio是啥

Rucio 是一个面向大型科研项目的**分布式数据管理系统**。可以把它理解成“科研数据的全球物流调度中心”：它知道有哪些数据、数据副本存在哪里，以及根据策略还应该把数据复制到哪里。它最初由 CERN 为高能物理实验开发，现在用于多个科研社区。[Rucio 官方介绍](https://rucio.cern.ch/)

一个典型过程是：

```
用户/科学 workflow
  “我要在 Caltech 使用数据集 X”
            ↓
Rucio
  查找 X 目前有哪些副本
  选择源存储和目标存储
  创建并跟踪复制请求
            ↓
FTS 等传输服务
  实际传送文件
            ↓
各站点存储系统 + 底层网络
```

Rucio 的核心概念包括：

- **DID（Data Identifier）**：文件、dataset 或 container 的逻辑名称。
- **RSE（Rucio Storage Element）**：一个存储 endpoint，例如某站点的磁盘或磁带系统。
- **Replica**：某份数据在具体 RSE 上的物理副本。
- **Replication rule**：用户声明期望状态，例如“在一级站点的磁盘上保留一份副本”。Rucio 负责设法实现并持续维护这个状态。[Rucio 客户端文档](https://rucio.github.io/documentation/user/using_the_client)

它不是：

- scientific workflow engine——不负责任务依赖和计算步骤；
- network controller——不直接控制 SENSE virtual circuit；
- network simulator；
- 单纯的文件复制命令。

这次会议关心 Rucio，是因为它目前更擅长表达：

> “把哪些数据放到哪个存储站点。”

而 SciNet 想补充的是：

> “这个数据传输必须什么时候完成？当前网络能否满足？多个 workflow 竞争时先服务谁？执行中性能下降后怎么重新协商？”

所以潜在关系是：

```
Workflow deadline / priority
            ↓
SciNet agent
  查询网络状态并与 SENSE 协商
            ↓
Rucio / Data Movement Manager
  安排和监控数据移动
            ↓
FTS + storage + network
```

Harvey 所说的“让 Rucio infrastructure-aware”，并不是说 Rucio 完全不知道存储基础设施；它显然知道 RSE、数据副本和传输状态。更准确地说，是让它的决策进一步感知**实时网络容量、跨域路径、SENSE 能提供的服务，以及整个 workflow 的 deadline**。这正好可以成为 SciNet agent 的一个具体切入点。

---

