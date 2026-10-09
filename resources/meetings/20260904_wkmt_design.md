# 2026-09-04 SciNet 组内会议：收敛 workflow / SENSE API 边界与 admission-control agent

> 材料来源：会议录音自动转写（无时间戳、无可靠 speaker diarization）。
>
> 参会者（依据称呼与上下文推断）：Kadangode K. Ramakrishnan（KK）、Linxuan Zhong、Sourabha Bharadwaj Bangalore Murali。
> 本次没有参会者截图；如实际另有参会者，需后续补充。
>
> 转写质量说明：人名与专有名词存在明显误识别。本文只在上下文足够明确时归属发言人；无法确认的内容标为 `[待核对]`。
> NIKA 相关术语另用项目官方 repository 核对。

## 一句话结论

本次组内会议把 9 月 1 日的宽泛讨论收敛成一条可实现主线：**workflow schema 表达 deadline、priority、endpoint 和 transfer demand；
SENSE 提供 topology、route、capacity 与实时 telemetry；先设计一个集中式 agent，对多个 workflow 做 proactive admission control 和 scheduling，
预测失误或发生拥塞后再 reactive reschedule。** 本组当前任务是把两侧 API 与 agent 所需信息定义清楚，并在 12 月前做出两个仿真科学实验并发运行的
具体演示；是否由本组承担完整 agent 实现，尚未决定。

## 一、承接 9 月 1 日会议：先决定扩展应放在哪一侧

KK 请 Linxuan 和 Sourabha 继续推进 workflow API，并要求暂时不要被 Harvey 上次会议中不断扩展的话题带偏。他首先澄清，眼下不是让学生
立即实现 adapter，而是先回答设计归属问题：

- 是扩展 SENSE API；
- 还是扩展 Rafael 的 WfFormat，再由另一层 adapter 转换成 SENSE API 调用。

KK 的初步判断是，应按信息的拥有者划分，而不是把所有内容放进同一份 schema。workflow 本身知道自己的 requirement；网络内部状态则必须由
network / SENSE 提供。

## 二、形成的 schema 边界：workflow 说“我要什么”，SENSE 说“网络现在有什么”



### 2.1 应由 workflow 一侧表达的信息

KK认为以下内容适合扩展到 Rafael 的 workflow format：

- application / workflow requirements；
- 整体 workflow deadline；
- individual task deadline；
- individual transfer deadline；
- priority，以及 hard / flexible deadline 等调度属性；
- 需要通信的 source endpoint 和 destination endpoint；
- 用于判断哪些 workflow 可以并发、何时执行的 traffic / workload demand。

这些都是 workflow 自己拥有的信息，也是 scheduler 判断能否在 deadline 前完成任务所需的输入。

### 2.2 应由 SENSE / network 一侧提供的信息

以下信息不应由用户或 workflow 静态指定：

- network topology；
- endpoint 之间可能经过的 route / path；
- 每条 link 的 capacity、latency、loss 等属性；
- 随时间变化的 available capacity 和其他 telemetry。

KK反复追问 `WfPlatform` 为什么要成为 workflow 的一部分。workflow 只需表达“我要从 endpoint A 通信到 endpoint B”，并不会要求底层网络必须 采用某种内部 topology。agent 对 topology 的理解应从 network 查询得到；否则还要不断用实时 SENSE 数据更新一份 workflow-side schema， 既重复又容易失效。【K】

学生回忆，SENSE 应有查询 network topology 的 API，但仅凭上次会议和现有文档还不能确认它是否提供 `WfPlatform` 草案需要的全部字段。
因此当前结论不是删除 `WfPlatform`，而是先逐项核对：哪些内容可直接向 SENSE 查询，哪些才是真正缺失。

### 2.3 用户不应提交 link-by-link 路径

学生一度提出，可以先把 base topology 展示给用户，再让用户给出逐链路 requirement，甚至指定希望使用的 path。KK立即纠正：用户不需要知道或 提交 link-by-link 信息。正确关系应是：【K】

1. workflow 给出 endpoint pair 和需求；
2. agent 从 network 获取 topology、link telemetry 与当前剩余容量；
3. agent 分析现有 route / multipath 能否承载该 workflow；
4. agent 决定 admission、path 使用与 schedule。

这项纠正进一步明确了接口边界：**用户描述目的，agent 和网络负责实现方式。**

## 三、KK 明确本组责任边界：先提供 agent 所需信息，不承诺包办整个项目

KK明确说，本组目前**没有被正式指定去实现完整 agent**。已经给自己确定的任务是【K】：

- 把 workflow requirement 和 deadline 放入合适的 API / schema；
- 提供足够信息，使未来的 agent 能进行 task scheduling；
- 确保被并发调度的任务总需求不超过系统 capacity；
- 结合 topology 和可能的多条 path，判断怎样并行使用网络资源。

如果这一方向对本组自身研究有价值，后续可以考虑实现 scheduling agent；但应由本组还是其他 partner 承担，目前没有决定。KK希望先把 agent 的
输入定义清楚，再讨论谁来实现。

KK也再次表达了对项目分工的担忧。他以明显带有玩笑和不满的口吻说，不清楚 Harvey 和 John 背后是否有学生实际做实现，也不知道 ORNL 是否有人
会构建 agent，HPE 侧具体由谁负责同样不清楚；他不会主动让本组替所有 partner 完成整个项目。这段话的实质是：**本组可以交付自己已承诺的
API / scheduling groundwork，但不能因为全体会议上有人提出更多设想，就默认全部落到本组。**

## 四、网络反馈分成两层：先 admission control，预测错了再 reactive correction

学生从 9 月 1 日讨论中提炼出“network feedback”要求：网络不可能保证所有用户请求都被满足，因此 user-side agent 和 network agent 之间可能需要
多轮 negotiation，根据 hard / flexible deadline 决定谁先获得资源。

KK 将这个想法收敛为两个不同阶段【K】。

### 4.1 Proactive admission control

在 workflow 开始执行前，agent 汇总所有 pending workflow，结合 topology 和 telemetry 判断：

- 哪些 workflow 当前可以接纳；
- 以什么顺序接纳；
- 哪些 task / transfer 在什么时间执行；
- 怎样根据 deadline 和 priority 仲裁；
- 当前 capacity 是否足以支持所选并发集合。

KK认为，当前讨论的 scheduler 本质上是在做 **admission control**，而不是等网络已经拥塞后才处理。

### 4.2 Reactive congestion control / rescheduling

即使 admission 时计算可行，预测也可能出错：容量估计可能不准，执行中也可能出现 congestion。此时 network feedback 应触发 correction，例如重新安排
某个 workflow 的 subtasks，使已经接纳的多个 workflow 在实际占用条件下仍尽可能满足 deadline。

因此 telemetry 既是 admission 前的初始输入，也是执行期闭环的持续反馈。会议没有定义具体 correction algorithm，只明确了这一步不能与 admission
control 混为一谈。

## 五、第一版先画成一个集中式 agent，长期很可能必须分布式

学生最初设想 user-side agent 与 network agent 多轮协商；KK则提出，概念设计的第一版可以先把它们看作**一个 overarching central agent【K】**：

- 接收全部 workflow 的需求；
- 查询 network topology 和 telemetry；
- 了解可用 route / multipath；
- 按 workflow、task、transfer 三层 deadline 评估可行性；
- 跨所有 pending workflow 按 deadline 和 priority 仲裁；
- 输出 admission 与 schedule。

KK明确承认，集中式设计很可能不是长期正确架构。真实环境跨许多 lab、experiment 和基础设施，不太可能永久由单个 controller 管理，最终可能需要
distributed decision-making。但现在还不知道怎样分布式化；为了先得到清楚、可运行的模型，可以像从一个 SDN controller 起步那样，先设计集中式版本。

这是一项**原型阶段的简化假设**，不是最终架构结论。

## 六、SENSE API 是否够用仍未知：先列缺口，再找真正懂接口的人

学生担心仅根据现有文档无法确认 SENSE API 是否足以提供所需信息。KK的处理方式是【K】：

1. 先尽可能用现有 SENSE API 表达完整流程；
2. 逐项列出 topology、telemetry、available capacity、route 等缺失能力；
3. 再找合适的 SENSE 人员确认，是文档没写清，还是接口确实没有。

KK不确定 Harvey 和 John 是否是回答所有 API 细节的最佳人选，因此不能只依赖全体会议里的口头说法。这里延续了 9 月 1 日的待办：需要找
Mohammad Sada、Tom Lehman 或其他直接维护 SENSE / operator 的人员做技术核对。

## 七、Digital twin 和真实系统应共享核心 API

学生问，当前设计是只针对 SENSE real system，还是还要为 digital twin 单独开发一套 API。KK的原则很明确：如果有人实现 digital twin，
它至少应该遵循与真实系统相同的 core API；不应为 digital twin 和 production network 分别设计两套不兼容接口。

但这也暴露了当前项目的现实问题：团队仍不知道最终会采用哪个 digital twin，也不知道谁负责构建它。因而眼下最可复用的工作是把
workflow-side requirement 与 network-side query / feedback 接口设计清楚，使它以后既能接 SENSE，也能接某个模拟或仿真后端。

## 八、12 月约束迫使团队停止循环争论，先做一个可演示闭环

KK直言，离 12 月只剩几个月，如果每周都重复同样的 debate，不可能按时拿出结果。他要求尽量做 concrete work，以支撑 Phase 2【K】：

- 把 API 设计具体化到可以说明字段和调用顺序；
- 展示增强后的 workflow 如何提供 deadline / demand；
- 展示怎样从 network 获取 topology / telemetry；
- 展示 agent 怎样基于两侧信息做 admission 与 scheduling；
- 最终至少让两个经过仿真的、相对真实的 scientific experiment / workflow 并发共存，并能说明调度没有超过 capacity、尽可能满足 deadline。

这并不要求立即解决完整的分布式 agent 架构。会议希望先把一个 simple centralized agent 的行为讲清并做出 proof of concept，再讨论后续扩展。

## 九、对 NIKA 的初步判断：可借鉴 agent harness，但研究任务不同

KK要求学生继续查看 Harvey 和 John 此前分享的 network-agent 材料，弄清它们只是 design paper，还是已经部署使用的系统。Sourabha 汇报了对
**NIKA** 的初步阅读：它在 network emulation environment 中向 agent 提供 MCP 工具，例如查看或改变 link、在虚拟机器上运行命令；agent 接收
“为什么两台机器不通”一类自然语言问题后，调用工具排查原因。

转写把 emulation backend 识别为 “cat net”。根据 [NIKA 官方 repository](https://github.com/sands-lab/nika)，准确名称是 **Kathará**；
NIKA 也支持 **Containerlab**。官方定位是 *Network Incident Benchmark for AI Agents*：部署可复现网络故障、连接 agent 与实时网络工具及 telemetry，
评估 agent 的 troubleshooting 能力。

会上学生的概括是：NIKA 当前展示的重点是 diagnosis，至少他初步看到的流程没有替用户解决本项目关心的多-workflow scheduling。KK据此明确区分：

- NIKA：面向 network incident / connectivity troubleshooting；
- 本组设想的 agent：面向多个 workflow 的 admission control、deadline feasibility、priority arbitration 和 scheduling。

因此本项目不是直接复用 NIKA 的任务定义，但可以继续研究它怎样组织 agent、MCP tools、emulation backend 和 reasoning loop，选择性借鉴设计。

## 十、会议结束时形成的第一版 agent 设计草图

综合本次讨论，KK脑中的集中式原型可以整理为：

```text
多个 workflow
  ├─ workflow deadline / priority
  ├─ task deadlines
  ├─ transfer deadlines
  └─ endpoint pairs / data demand
                │
                ▼
     centralized admission-control agent
                ▲
                │
  SENSE / network API
  ├─ topology
  ├─ possible routes / multipaths
  ├─ link capacities
  └─ current telemetry / available capacity
                │
                ▼
  admission + ordering + path/resource schedule
                │
                ▼
  execution monitoring → prediction error/congestion → reschedule
```

agent 要逐层检查 individual transfer、task sequence 与整个 workflow 是否能在最终 deadline 前完成，并跨所有 pending workflow 按 deadline 与 priority
仲裁。会议没有进入算法、优化目标或实现语言，因此这些仍属于后续设计，而不是已经达成的技术结论。

## 十一、直接后续动作


| 后续动作                                                                 | 状态 / 边界                          |
| -------------------------------------------------------------------- | -------------------------------- |
| 将 schema 明确拆成 workflow-owned information 与 network-owned information | 本次已形成原则；具体字段仍需整理                 |
| 核查 SENSE 是否能查询 topology、route、link capacity 和实时 telemetry            | 学生下一步；不能只依赖现有文档的初步印象             |
| 列出 SENSE API 的确切缺口，再找接口维护者确认                                         | KK要求；不要未经核对就扩展 API               |
| 整理一份 coherent end-to-end design，说明 workflow、SENSE 与 agent 的数据流       | 本次最直接产出目标                        |
| 先按 centralized controller 设计 admission-control agent                 | 原型假设；长期 distributed design 未解决   |
| 深入阅读 NIKA，判断哪些 agent / MCP / emulation 机制可借鉴                         | 只借鉴机制，不把 troubleshooting 当成本项目问题 |
| 面向 12 月准备两个 emulated scientific workflows 并发运行的 demo                 | Phase 1 的具体化方向；实验和实现尚未启动         |




## 十二、会末的其他组内事项：下一个投稿节点

技术讨论结束后，KK把话题转到组内论文进度。他提到组内八人今年夏天已经提交两篇 workshop paper，暑期即将结束，并询问下一位有 deadline、
想汇报或推进投稿的人是谁。转写在有人准备回应时结束，因此没有记录到具体人选、论文或截止日期。

## 待核对项


| 项目                                   | 当前判断                | 说明                                 |
| ------------------------------------ | ------------------- | ---------------------------------- |
| 实际参会者                                | KK、Linxuan、Sourabha | 无参会截图，仅由称呼和发言推断                    |
| 此前分享的其他 “network agents”             | 未确认                 | 转写未给出名称；需检查 Harvey / John 两周前分享的材料 |
| SENSE topology / telemetry API 的准确能力 | 未确认                 | 本次只讨论了预期能力，没有现场调用或由接口维护者确认         |
| Digital twin 平台与负责人                  | 未确定                 | KK明确把这称为当前问题之一                     |


