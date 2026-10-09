# 2026-09-28 组内讨论：SciNet agent 中 LLM 的职责边界

> **日期**：2026-09-28。用户在当天将其称为“今天的会议”。
>
> **材料**：用户提供的会议自动转写，分两段粘贴：第一段在 50,000 字符处截断，第二段从截断处续上。本文只截取会末 “why do we call this an agentic framework” 之后关于 LLM 职责的讨论，以及紧随其后的 SciNet 下一步与平台访问。会议前段（其他论文、其他项目、毕业安排）和会末 TA / 经费话题按用户要求不整理。
>
> **参会者**：KK、Linxuan Zhong，可能还有组内其他同学；名单不完整。
>
> **说话人可靠性**：自动转写没有 speaker label。提问、举例和给方向的一方按语气与上下文归为 KK；介绍 Scheduling Agent / Network Agent 现有设计、逐条列举 LLM 职责的一方归为 Linxuan。这些归属未经回听核对。
>
> **整理口径**：Linxuan 讲的 LLM 职责似乎在对照一份清单（转写中出现 “fourth part”“third part”），但序号前后不一致，本文按出现顺序排列，不采用原序号。外部平台名称只按转写和既有会议记录校正，没有核实访问状态。

## 核心摘要

KK 要求先回答一个问题：**这个框架为什么叫 agentic？agent 为什么要调用 LLM，调用它做什么？** 他把 agent 的决策依据分成三类：agent 自身掌握的 rules / 确定性算法、向 LLM 请求的 guidance，以及来自 operators 或做实验的 scientists 的指示。Operators 与 agent 之间的边界此前已经讨论过，就是 workload / workflow specification。现在要厘清的是 **agent 与 LLM 之间的接口**，即 agent 已经靠规则知道什么、还缺什么，以及缺的部分为什么要交给 LLM。

讨论采用的思路是先划出**不该交给 LLM 的部分**。Scheduling Agent 根据依赖计算 critical path、earliest start 和 latest finish；Network Agent 在 capacity ledger 上按带宽做扣减。这些都属于确定性算法。随后 Linxuan 逐条列出 LLM 的候选职责，KK 逐条追问和改述：


| 候选职责                            | 大意                                                               |
| ------------------------------- | ---------------------------------------------------------------- |
| 跨 workflow 任务交织                 | 多个 workflow 各自保持内部顺序，彼此之间怎么排没有规则                                 |
| Over-provisioning 程度            | 带宽分配不做硬切分，允许超额多少需从历史中学                                           |
| Utility curve                   | 把用户对完成时间的偏好转成价值曲线                                                |
| 推断缺失参数与约束                       | priority、数据量、带宽；站点 policy、instrument 手册中的约束                      |
| Input normalization             | 把用户或邮件中的自然语言转成 workflow schema                                   |
| 追要缺失信息                          | 缺必需参数时向 operators 追问                                             |
| 解释与反馈                           | 把 Network Agent 的 `at_risk`、local recovery 等状态转成 operators 能读懂的话 |
| Telemetry 采集频率 / probe planning | 各类测量多久采一次：太频繁干扰真实流量，太稀疏信息过时                                      |
| 异常响应                            | 网络出问题时查哪些信号、怎么修；Network Agent 局部修复，Scheduling Agent 重排 workflows |
| 搜索停止                            | 生成 offer 时搜索空间很大，由 LLM 设定“够好就停”的规则                               |


KK 提出的长期目标是让**确定性算法、reinforcement learning 和咨询 LLM 三种方式共存**。第一阶段先回答“有哪些最基础的事情需要问 LLM”，同时说明将来会用 RL 学习。他借业务部门的 agentic operating procedures 概括出一个分层模式：**能用 rules 处理的用 rules，rules 不知道的升级给 LLM，LLM 也处理不了的再升级给用户。**

下一步是把这份清单充实到能形成有意义的贡献，再去调研别人的 agent 如何、在什么地方调用 LLM（论文、white papers、代码）。KK 认为眼下整个项目对本组是开放的：其他组还在观望，而 SciNet 是获得加速的唯一一个 networking proposal，所以本组比较受关注。

KK 还表示，**明天的会不必讲这部分**。过去两三周基本只有本组在讲，接下来想先在组内把想法想透，暂时不再做新的汇报。

## 一、问题的提出：为什么叫 agentic framework

KK 问现在是否已经能回答“为什么把它叫作 agentic framework”。回答方表示此前已经被问过这个问题，并已在 chat 中作答。转写为 “I send to the to her child”，可能指发给了某位与会者，但对象无法确定。

KK 接着给出他的框架（转写中提到 “the responsibility of large language model”）：

- agent 会向 LLM 询问下一步怎么做，但**不是完全照做**，还会结合自身 rules 和 LLM 的回复来决定；
- agent 与外界的交互不只限于 agent ↔ LLM，还包括 agent ↔ operators / scientists；
- **operators ↔ agent** 的边界已经讨论过，即 workload / workflow specification；
- **agent ↔ LLM** 这一侧是现在要弄清的：agent 为什么需要 LLM，问什么，已经靠规则知道什么。



## 二、不该交给 LLM 的部分：确定性算法

Linxuan 说明，目前 Scheduling Agent 和 Network Agent 内部各有一个 LLM，所以第一步要回答**哪些任务不应交给 LLM，而应由 agent 用确定性方法完成**。

举的例子是 Scheduling Agent 计算 critical path：根据 workflow 中的任务依赖，用算法求出每个任务的 earliest start 和 latest finish。依赖关系在 workflow 里已经写明，这一步不需要 LLM。

## 三、LLM 的第一个位置：跨 workflow 的任务交织

KK 指出，workflow 内部的依赖确定，**不代表 workflow 之间的关系也确定**。他举的例子是：

- workflow 1 先提交，deadline 很远；
- workflow 2 后提交，deadline 很紧。

两个 workflow 的任务之间如何交织，**没有规则可循**。这时可以把两组任务、各自的 deadline 和各自必须保持的内部顺序交给 LLM，请它在保持两边内部顺序的前提下给出交织方式。

KK 希望对外按下面的方式表述，并说明他和 Linxuan 讲的是同一件事，只是换成他更容易理解的说法：

> 有些信息由 workflow 指定，有些由 agent 已知的 rules 覆盖；剩下 agent 不知道的部分，agent 整理相关信息交给 LLM，由 LLM 根据它见过的情况判断合适的选择。



## 四、LLM 的第二个位置：Network Agent 的 over-provisioning



### 1. Ledger 扣减本身是确定性的

Linxuan 介绍，Network Agent 维护一份 network capacity ledger。为某条链路安排带宽时，直接在 ledger 上做扣减，这是确定性计算。讨论还涉及分配语义：是 circuit 式的独占，还是允许 multiplexing。

### 2. KK：这里的 circuit 不是严格的 circuit

KK 认为全按 circuit 做 provisioning 会很糟糕，而且这里的 circuit 本来就不是严格意义上的 circuit：

- 更像 ATM：ATM 承载 cells，这里承载 packets；
- 有 allocation，但**不是硬分配**；
- 例如链路容量为 10，不应只能分成 5 + 5 或 4 + 6，也应允许分成 6 + 6。

他把这称为 over-provisioning。按上下文，它指超额分配，也就是依赖统计复用的 overbooking / oversubscription，而不是分配冗余容量。术语待定。

### 3. 允许超额多少，要从历史中学

KK 指出，允许多大程度的超额分配**不是现成的 rule**，需要从历史中学。可以有三种做法：


| 方式                     | 说明                |
| ---------------------- | ----------------- |
| 确定性算法                  | 基于历史信息计算          |
| Reinforcement learning | 从运行结果中学习超额分配的程度   |
| 咨询 LLM                 | 请 LLM 给出 guidance |


KK 的长期目标是**让这三种方式共存**。第一阶段暂时不考虑 RL；转写为 “we might not want to think about the business”，按下文推断指 RL，未核对。第一阶段先回答“有哪些最基础的事情可以问 LLM”，但要写明将来会用 RL 帮助学习。

### 4. Offer 生成分两步

讨论中 KK 一度理解为 LLM 负责 offer 的协商或选择。Linxuan 澄清：Network Agent 给出 offers，Scheduling Agent 决定用哪一个；讨论的重点是 **offer 如何生成**，不是如何选择。

- KK 设想：Network Agent 基于已有 ledger，再结合“这类实验同时运行时，过去多少超额分配是可行的”这一经验来生成 offers，也就是用 AI 生成 offers；
- Linxuan 说明：在依赖、start time、deadline 和 ledger 都已知，而且按硬边界、不做 over-provisioning 分配时，offer 生成是**确定性的**；只有引入 over-provisioning 后才需要 LLM；
- 结论是 offer 生成分两步：**先按可用容量做严格分配，再由 LLM 协助处理 over-provisioning**。



## 五、LLM 的第三、第四个位置：utility curve 与缺失参数、约束推断



### 1. 构造 utility curve

Linxuan 提出的第二类 LLM 职责，是把问题建模成 utility curve。用户可能只说“这个任务 6 PM 前完成价值最高，过了 8 PM 就没用了”。

KK 把它展开成一条曲线：

- 5 PM 完成，与 6 PM 相比没有额外价值；
- 6 PM 前完成，得到全部价值；
- 7 PM 前完成，价值降低；
- 8 PM 前还没完成，就失败了（“I'm screwed”）。

Linxuan 认为这条曲线取决于具体任务，很难由 operators 完整给出，也很难用确定性算法得到，所以可以交给 AI 来构造。

### 2. 推断 workflow 中缺失的参数

第三类是推断 workflow 没有写明的参数。例如用户给了任务和 deadline，却没有给 priority 或数据量。LLM 用来填补 operators 的指示与系统实际所需信息之间的差距。

KK 补充，用户往往**给不出**完整信息，例如“在这台 instrument 上，我没法告诉你会产生多少数据、需要多少带宽”。这类信息可以从别人以前在同一台 instrument、其他场景中做过的实验历史里得到。

Linxuan 补充，对这些用户没有提供的信息，LLM 还要结合当前网络状态，找到既能满足需求、**又不影响其他流量**的方案。

### 3. 把隐含约束 formalize

Linxuan 接着提到对约束的 formalization：某些设施有隐含约束，例如“样品不能过夜保存”，或者根据以往信息已知的某些 constraints。LLM 需要理解这类约束，来源可能是设施的 user guide 等文档。

KK 认为这更多是**站点层面**的事：

- 每个 site 可能有自己的 policies，需要开发 agent 去解析这些 constraints；
- 每台 instrument 的 user manual 里也会有大量此类约束；
- 网络一侧同样有类似规则，例如某类 burst 会被怎样处理。转写为 “the menu offer a birth lord horn yesnet”，可能指 ESnet 的相关规定，未核对。

KK 问这是否已包含在前面的清单中。结论是：凡是能从历史信息获取的部分，已经由上一条（推断 workflow 未写明的参数）覆盖。

## 六、LLM 的其余候选职责

以下各条都由 Linxuan 提出，KK 逐条追问或改述。

### 1. Input normalization

用户可能只用自然语言描述需求，需要把它转成 workflow schema，也就是本系统的 workflow format 和相应取值。

KK 质疑 “input normalization” 这个名称：它实质上是**把用户的自然语言信息翻译成 workflow**。双方补充，输入不一定直接来自用户，也可能来自 email 等其他自然语言来源。

### 2. Chasing missing information

KK 起初认为它与“推断缺失参数”是一回事。Linxuan 区分：inferring 是 LLM 自行推断；chasing 是**缺少必需参数时反复向 operators 追问**。

KK 建议直接这样描述：**系统需要以某种方式与 operators 交互，取得必需的参数。**

### 3. Explaining and negotiation

Network Agent 报告问题时，例如状态变成 `at_risk`，或已在本地恢复，需要把这些信息翻译给 operators。转写为 “using not even natural language”，按上下文应指用自然语言。

KK 的概括是：这是一种 **feedback**。

### 4. Refresh policy / probe planning

Linxuan 对这一条最不确定。Scheduling Agent 需要轮询 Network Agent，Network Agent 需要轮询物理网络的信息，问题在于是否用固定间隔。

KK 的改述是：**Telemetry agent 要决定各类信息的采集频率**，例如多久做一次测量：

- 太频繁，测量本身会干扰真实流量；
- 太稀疏，拿到的信息会过时。

所以这是为 telemetry 参数找更好的设定方式。KK 认为这也是 Linxuan 所说 **probe planner** 的一部分：规划 telemetry 需要用到的全部 probes。

### 5. Anomaly response

网络出问题时，Network Agent 要判断如何修复；这一步也许可以由 AI 决定，例如该测量哪个值、检查哪个信号。

这一条同时涉及两个 agent：**Network Agent 在本地修复，Scheduling Agent 设法 reschedule workflows。**

### 6. Search stopping

Network Agent 生成 offer 时，寻找好方案的搜索空间可能很大，需要找到一个 “good enough, stop” 的点。

KK 追问：是让 LLM 决定何时停下，还是让 agent 停止为 Scheduling Agent 寻找更好的 offer？Linxuan 澄清：**由 LLM 设定基于规则的停止策略**。原因是某些问题优化空间很大，而 agents 之间、operators 与 agents 之间都有 latency 要求。

## 七、KK 的方向：分层升级与调研



### 1. 借鉴 agentic operating procedures

KK 提到业务部门同事做 agentic customer service 的做法：把传统 SOPs 改写成 **AOPs（agentic operating procedures）**，用自然语言写明规则，并按客户类型（例如 medical）区分；此外还有一些基本的 metrics 类规则，以及何时升级处理的规定。

他认为这里的结构非常相似：

> 这些是 rules；这些是我不知道怎么处理、要升级给 LLM 的；LLM 也处理不了时，再升级给用户。

KK 希望先把 LLM 职责清单充实到能形成**有意义贡献**的程度，再向这些同事征求意见。

### 2. 调研别人的 agent 怎样调用 LLM

KK 指出，目前是本组自己在想。应该已有很多应用场景讨论过 agentic 系统如何构建、在哪些地方为什么调用 LLM，需要去找这方面的 papers；没有 papers 也可以看 white papers 或代码。

### 3. 暂不收窄到 Network Agent

Linxuan 问是否只需聚焦 Network Agent。KK 认为最终大概会落在那里，但**眼下整个项目对本组是开放的**，因为其他组都在观望。应先确定本组能贡献什么，其他人之后会跟上。他强调其他组并非不胜任，各自在自己领域都足够好，足以赢下 proposal。

KK 还提到，proposal 总数很多（转写数字不清），其中只有一个 networking proposal 获得加速，所以本组比较受关注，更需要做出东西。

## 八、实验平台访问

Linxuan 提到，按 John 的说法（转写为 “Northwake Jones”，按 [2026-09-22](20260922.md) 记录推断为 John），本组可以访问 **NRP（National Research Platform）**，平台内有一些接口，但具体情况尚不清楚。

KK 表示已难以追踪本组能访问的所有平台，他记得的有 CloudLab、Chameleon、FABRIC、Colosseum，另有一个平台没想起名字。他要求**查清 NRP 访问是怎么开通的**。

KK 起初把 NRP 和某个 copilot 类工具弄混了；经澄清，NRP 与 FABRIC 一样是 infrastructure。

## 九、会议安排

- KK 原本说不确定下周是否讨论这部分，随即更正为**明天**。
- 理由：过去两三周基本只有本组在讲。他希望先在组内做一些思考、把想法发展得更成熟，暂时不再做新的汇报。
- Linxuan 确认下一步要发展的内容，KK 的回答是：**弄清楚 agent 依赖 LLM 做什么**。



## 十、待办与开放问题


| #   | 事项                                                                    | 状态       |
| --- | --------------------------------------------------------------------- | -------- |
| 1   | 写清 agent 的三类决策依据：rules / 确定性算法、LLM guidance、operators / scientists 指示 | 待整理      |
| 2   | 列出**不交给 LLM** 的部分，如 critical path 和 ledger 扣减                         | 已有初步例子   |
| 3   | 充实 LLM 职责清单（见核心摘要表），统一命名并去重（如 inferring 与 chasing）                    | 已有候选，未定稿 |
| 4   | 按 “rules → LLM → 用户” 的分层升级结构组织清单                                      | KK 建议    |
| 5   | Offer 生成两步走：先严格分配，再由 LLM 处理 over-provisioning                         | 讨论中基本一致  |
| 6   | RL 作为未来方向写入，第一阶段不做                                                    | 待写入表述    |
| 7   | “over-provisioning” 的准确术语（overbooking / oversubscription）与分配语义        | 开放       |
| 8   | 调研 agent 调用 LLM 的已有工作（papers / white papers / 代码）                     | 待做       |
| 9   | 充实后向做 AOPs 的业务部门同事征求意见                                                | 之后       |
| 10  | 查清 NRP 的访问是怎么开通的，以及平台内有哪些接口                                           | 待查       |
| 11  | 明天的会不汇报这部分                                                            | 已定       |




## 附：转写存疑点


| 转写原文                                                  | 本文采用的理解                                   | 置信度 |
| ----------------------------------------------------- | ----------------------------------------- | --- |
| “why we call this an agenic framework”                | agentic framework                         | 高   |
| “I send to the to her child”                          | 回答已发到 chat，对象不明                           | 低   |
| “interface to NLM / ALM / LLF”                        | LLM                                       | 高   |
| “subtraction network … little network capacity later” | 在 network capacity ledger 上做扣减            | 中   |
| “over provision is circuits. Horrible”                | 全按 circuit 做 provisioning 很糟糕             | 中   |
| “think about the business”                            | 可能指 RL；第一阶段先不考虑                           | 低   |
| “RL4 helping to learn”                                | 用 RL 帮助学习                                 | 中   |
| “utinerary curves / utin curves”                      | utility curves                            | 高   |
| “some world fl Florida has some conserence”           | 某些设施有隐含约束                                 | 低   |
| “the menu offer a birth lord horn yesnet”             | 可能指 ESnet 对 burst 的处理规定                   | 低   |
| “input normalization … a schemer”                     | 把自然语言转成 workflow schema                   | 高   |
| “little work agent / little organation”               | Network Agent                             | 高   |
| “ar response”                                         | anomaly response                          | 中   |
| “wouldn't you start searching”                        | search stopping                           | 中   |
| “theOPs and then AOPs”                                | SOPs → AOPs（agentic operating procedures） | 中   |
| “Northwake Jones”                                     | John                                      | 中   |
| “an RP / NRB”                                         | NRP（National Research Platform）           | 高   |
| “Crimenian chemistry / Fabric, Colusium”              | Chameleon、FABRIC、Colosseum                | 中   |
| “just like Florida”                                   | 可能指 FABRIC                                | 低   |


