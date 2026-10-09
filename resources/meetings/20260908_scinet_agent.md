# 2026-09-08 SciNet 全体会议：用统一 agent / digital-twin demo 对齐 Phase 1 gate metrics

> 材料来源：会议录音自动转写（无时间戳、无可靠 speaker diarization）、参会截图，以及会后补充的 proposal「Decision Gate Metrics」截图。
>
> 截图中可确认的远程参会者：Linxuan Zhong、Mariam Kiran、Sourabha Bharadwaj Bangalore Murali、Kadangode K. Ramakrishnan（KK）、Harvey Newman、Rafael Ferreira da Silva；另有一个会议室终端，画面中三人姓名无法由截图确认。Harvey's Notetaker Otter.ai 为转写机器人，不计作参会者。
>
> 转写质量说明：专有名词和人名存在明显误识别。本文只在上下文充分时归属发言人；无法由材料确认的内容标为 `[待核对]`。四项 decision-gate metrics 的正式定义已根据 proposal 截图补全。

## 一句话结论

团队决定不为四项 Phase 1 gate metrics 分别搭建四套演示，而是围绕 **HEP workflow 与 AI workflow 两个可管理、但仍具代表性的抽象 workflow**，在同一 digital twin 上建立 baseline，再用 scheduling agent、network agent 和扩展后的 workflow 描述做优化，统一展示 completion / utilization、并发公平性以及故障检测与恢复能力。Phase 1 仍以仿真为主，底层路由和负载均衡交给 SENSE 等外部网络系统；近期目标是先把 proposal 架构图分解成相互连接的任务与小组，并争取在 11 月 SC 相关展示中做出一个早期 agent demo。

## 一、项目行政状态与 go / no-go 时间

会上宣布合同已经签署，ORNL 已给出 green light，并正在处理向合作单位拨款；ORNL 一侧也已有 charge code，可以正式开始投入工作。

关于经费执行，会议口径是：合作单位收到的是按预算执行的 lump sum，不需要向 ORNL 逐小时汇报；但各单位仍受本机构审计约束，实际投入应与 budget justification 中的 salary rate 和 person-month 大致一致。

会议还提到，有 program manager 表示原本 12 月的 Phase 2 go / no-go decision 可能至少推迟到 1 月底，甚至希望安排到 2 月。**这是会上转述的信息，不是已经确认的新 deadline**；团队仍按需要尽快完成 demo 的节奏推进。

## 二、沿用“两层 agent”框架，但实现责任仍未确定

会议开头回顾了前一周学生关于 workflow 网络字段的工作，并提出在下一次汇报前先获得 Rafael 对 workflow API 现状和扩展方向的反馈。当前讨论中的总体框架包含两个相互协作的角色：

1. **Network agent**：从 workflow API 接收各 task 的连接需求，通过 SENSE API 建立 endpoint 间连接；理解 task dependency，并把 workflow / task deadline 转换为下层 data-transfer deadline，进行必要协商，使单个 workflow 按时完成。
2. **Scheduling agent**：跨多个并发 workflow，根据 priority、deadline 和 experiment requirement 做准入与调度；与 network agent 及上层请求方协商不可同时满足的要求。

会上再次强调：**谁来实现这些 agent 尚未确定**。当前更明确的工作是先把 workflow、agent 与 SENSE 之间的 API 信息和职责边界定义正确，再决定实现归属。

## 三、agent harness 是待研究方向，不是已经选定的技术方案

Mariam 提到 Harvey 此前建议关注 agent harness。她刚开始阅读近期材料，尚未形成实现方案。会上对这一方向形成的工作原则是：

- harness 不只是“构建 agent”，还包括限定 agent 可用工具、行为范围、规则和 guardrails，避免错误或 hallucination 在 agent 间传播；
- 多 agent 之间的交互即使单个 agent 看似正常，也可能产生系统级错误，因此交互边界需要显式设计；
- 不应把某一个 AI 对 SENSE 或 agent 架构给出的建议当作最终选择，应围绕 proposal 中已有的系统架构图系统化提问、比较多个模型，并用人工判断核验；
- 可以进一步让 coding agent 生成小段实现，观察其假设和代码行为，但不能以生成结果替代设计论证。

Mariam 计划继续调研，并在下周分享 agentic framework / harness 方面的材料；Harvey 表示如果需要，可以安排人员协助。

## 四、四项 gate metrics 必须由同一个系统共同展示

Program manager 要求团队重新对齐 proposal 中的 decision-gate metrics，会议据此逐项讨论。Proposal 要求四项 quantitative gates 在 **Month 6** 于 network digital twin 上展示，并在 **Month 9** 纳入 programmable hardware。


| Gate metric              | 会上能确认的要求                                                                                                                                                       | 讨论后的实现口径                                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Rubin-class HEP workflow | alert-pipeline time-to-completion 至少降低 **25%**；nightly 20 TB ingest 保持至少 **100 Gbps**；接收端 GPU utilization 从 50–60% baseline 提升至至少 **80%**                      | 先对简化的 Rubin-class workflow 建立 baseline，再展示扩展 workflow 描述与 agent 优化后的对照                                 |
| Agentic AI workflow      | 使用 **512 V100 Summit GPUs**；distributed training 的 WAN overhead 不超过 **15%**；存在 background HEP traffic 时，INTERSECT agent coordination 达到 p50 < 200 ms、p99 < 1 s | 不声称故障后临时申请 512 张 GPU；在已有总资源分配的假设下构造可执行的抽象表示，并先测 baseline                                               |
| 多 flow 公平性               | 对 **N = 10–100** 个 concurrent science flows，Jain's fairness index ≥ **0.9**；最低优先级的竞争 flow 仍保留其 fair share 的至少 **30%**                                          | 会议认为仅看完成时间可能误用 Jain's index，需要明确 fair-share 的资源定义；可参考 proportional fairness 或 max-min fairness         |
| 故障检测与恢复                  | fault detection ≤ **5 秒**；workflow resumption ≤ **30 秒**；single-facility failure 下 campaign success ≥ **90%**                                                  | Phase 1 从 link failure 或性能退化开始；向 SENSE 团队核对既有 flow-redirection 案例，确认 detection 与 response 是否真实落入两个时间窗口 |


Proposal 将达到这些阈值定义为进入 Phase 2、与 ESnet 和 SNS 部署 INTERSECT workflows 的 pass criterion。

KK 指出，简单把 Jain's fairness index 套在两个 workflow 的完成时间上可能产生误导：例如让 A 独占执行、再让 B 独占执行，只要两者完成时间相同也可能显得“完全公平”，但并不满足并发共享资源的实际需求。因此公平性指标需要围绕多个 workflow **同时共存时获得的资源份额和完成表现**重新定义。

> 假设链路总带宽是 100 Gbps，有 10 条同时竞争的 flow。
>
> 如果它们同等重要，理想的 fair share 是每条 10 Gbps。
>
> - **Jain’s fairness index ≥ 0.9**：整体分配不能相差太悬殊。1 表示完全均匀，越接近 0 越不公平。
> - **最低优先级 flow ≥ 30% fair share**：即使它优先级最低，也至少应获得 `10 × 30% = 3 Gbps`，不能被完全饿死。
>
> 两个条件的作用不同：Jain index 看整体公平性，30% 是对最弱 flow 的保底。
>
> KK 的质疑是：**“公平”不能只看最终平均数或完成时间。** 例如先让 A 独占 100 Gbps，完成后再让 B 独占；两者最后获得的数据量或完成时间可能相同，Jain index 看起来很好，但它们并没有真正并发共享资源。
>
> KK 建议先明确公平性的含义：
>
> - **Max-min fairness**：优先保障当前分配最少的 flow，避免饿死。
> - **Proportional fairness**：允许高优先级 flow 获得更多，但增加它的资源时，不能给其他 flow 造成不成比例的损失。
>
> 核心问题是：proposal 里的 **fair share 到底是平均带宽、按优先级加权的带宽，还是 deadline 满足程度**，目前没有定义清楚。



## 五、先做 baseline，再在同一环境中展示优化前后

本次最重要的收敛是：**不能为四项 metric 做四个彼此分离的小实验。** 它们应来自同一套接近真实的系统、同一组 workflow 和同一个 digital twin。

会议形成的统一演示思路是：

1. 选择两个 workload：一个 HEP workflow，一个 agentic-AI / AI workflow；
2. 为二者建立足够简单、能在 digital twin 中运行，同时又能让领域人员认可的抽象表示；
3. 先用当前 workflow framework、尚未加入新扩展的版本建立 baseline；
4. 再加入扩展后的 workflow 参数、scheduling agent 与 network agent；
5. 对比优化前后的 alert-pipeline completion time、sustained throughput、GPU utilization、WAN overhead、agent-coordination latency 和并发公平性；
6. 在同一场景中注入网络故障或性能下降，展示检测、重平衡与恢复。

> - **Alert-pipeline completion time**：从望远镜产生观测数据，到完成处理并发出科学告警所需的总时间。包括数据传输、计算和中间任务等待时间。
> - **Sustained throughput**：一段较长时间内能够持续维持的数据传输速率，不是瞬时峰值。例如整晚传输过程中持续达到 100 Gbps。
> - **WAN overhead**：使用广域网进行分布式训练带来的额外时间或性能损失。常见定义是：
>  \frac{\text{分布式训练时间}-\text{理想/本地训练时间}} {\text{理想/本地训练时间}} 
> “≤15%”表示 WAN 通信最多让训练时间增加约 15%。但 proposal 仍需确认它具体采用哪种计算方法。
> - **Agent-coordination latency**：多个 agent 交换状态、请求和决策所需的响应时间。`p50 < 200 ms` 表示一半请求在 200 ms 内完成；`p99 < 1 s` 表示 99% 请求在 1 秒内完成。

Proposal 已明确要求 Rubin-class HEP workflow 和 nightly 20 TB ingest；会上尚未确定其具体 workflow 实例及缩放方法。真实 HEP workflow 步骤很多，因此第一版应做可信的缩小表示，而不是原样复制全部生产复杂度。

Harvey、Rafael 和 Mariam（会上说“possibly I”）将讨论两个 workflow 的简单原型和 baseline。会议提到的 multi-workflow scheduling with fairness 论文是 Jiajian Yang 等人的 *[Fairness-Constrained Multiple-Workflow Scheduling Through Stochastic Ranking](https://ieeexplore.ieee.org/document/11043015)*（IEEE CEC 2025），可用于检查公平性定义与调度方法。【K】

## 六、故障场景从模糊的“facility failure”收敛到网络可控事件

Proposal 中写的“一个 facility 下线后将 workload 切到其他 facility”过于宽泛。会上认为，SciNet 是 networking 项目，Phase 1 应先选择清晰、可仿真的网络事件：

- link failure；
- packet loss 上升；
- 竞争流量增加导致 throughput 下降；
- 在已有 endpoint / site 资源范围内重新选路或把执行切换到另一地点。

相比“整个 facility 突然消失，再立即获得等量计算资源”，会议更倾向于把场景表述成 **throughput 退化后的 rebalance**。这样既连续、可测，也更符合真实资源获取方式：团队可以假设所需计算资源已在总 allocation 内，但不能假设发生故障后能够在 30 秒内新申请到数百张 GPU；真实大规模资源申请可能需要经过持续数月的委员会流程。

Mariam 将通过与 program manager 的定期会议确认这一口径。会上建议措辞应是“确认双方对 Phase 1 承诺的解释一致”，而不是未经确认就宣称改变了承诺。

另一个范围边界是：Phase 1 主要处理一组预先给定、需要共同调度和管理的 workflow；随着新 workflow 持续到达而不断自适应，可以作为 Phase 2 扩展。Phase 1 建立的框架应为这种扩展保留接口，但不必现在完成全部在线场景。

## 七、SENSE 恢复路径：长生命周期 L2 overlay 与较快 L3 flow management 分开

会上有人指出，SENSE 中创建 Layer-2 overlay 可能耗时较长，因此 overlay 通常会保持较长时间；故障后的快速处理更可能发生在 Layer 3，通过 flow redirection 完成。由此提出：

- 5 秒应主要对应 fault detection；
- 30 秒对应 response / recovery setup；
- 需要请 SENSE 团队展示或回顾已有 flow-redirection exercise，用实测案例验证两个时间目标是否建立在现实能力上。

这仍是会上提出的架构判断，**尚未由 SENSE 实测或接口维护者确认**。

> - **Layer-2 overlay（二层覆盖网络）**：在多个站点之间建立一条虚拟的“同一局域网”连接，例如跨站点 VLAN。它通常需要提前配置和预留，建立较慢，但可以保持较长时间。
> - **Layer 3（三层网络）**：基于 IP 地址和路由转发数据。网络出现拥塞或故障时，可以通过修改路由，把流量较快地切换到另一条路径。
>
> 在会议场景中：
>
> ```
> L2 overlay：先搭好站点间的长期虚拟连接
> L3 routing：连接内部出现问题时，快速改变流量路径
> ```
>
> 所以不必每次故障都重新建立 L2 overlay，可以保留它，只在 L3 做 flow redirection。

## 八、任务按 proposal 架构拆分，而不是按四个数字拆分

团队倾向于把人员分成多个小组，各自承担较小、相互连接的任务，并在每周会议中汇总进度。对此进一步建议：直接使用 proposal 中的整体架构图，把其中每个 component 展开成 subtask 和 working group，同时画清它们之间的依赖。

这一拆法有两个目的：

- 避免每个人都同时参与全部内容；
- 保证四项 gate metrics 最终来自同一个可运行系统，而不是四个互不相干的工作包。

Mariam 计划与 Rafael 一起将四项 gate metrics 映射到 proposal milestones，给出日期、任务和可能的 subteam，并在两三天内发给各 PI。

## 九、Phase 1 做控制与编排，底层 network engineering 交给外部系统

对于 programmable network infrastructure，会议明确 Phase 1 仍以 simulation / digital twin 为主。本组可以实现：

- workflow scheduling agent；
- network agent；
- 对接 digital twin（例如增强的 Mininet）的 API；
- 两个 workflow 在网络条件和 deadline 约束下的调度演示。

但本组不应自行承担底层 route computation 或 load balancing 的完整网络工程。正确边界是由上层 agent **触发、请求或协商**网络服务，再由 SENSE 及更广义的 American Science Cloud 相关基础设施执行。即使底层代码不是本组编写，团队也必须能解释请求最终如何由真实网络机制实现，并指向相应的既有系统工作。

前一周学生展示的 workflow-network 图得到肯定，并收到一项具体修改：**保持 source 与 destination 固定，让中间网络图可变。** task 不应声明必须经过某个中间站点；故障或性能变化发生时，由下层系统调整中间路径。

SENSE 支持 point-to-point 与 point-to-multipoint 等连接方式；会上也讨论了 ECMP。但 ECMP 假设 equal-cost paths，不能自动解决异构路径的负载分配问题。跨 ESnet 的主干路径可能近似同质，而接近 metro / peering / endpoint 的部分更可能不同，因此不能把所有 multipath 都视为等价。会议没有决定本组要实现新的 multipath 算法。

## 十、与 SENSE Data Movement Manager 对接，但保留 SciNet 自己的系统边界

会上提到，SENSE 正走向其所谓的 phase-one production，但负责决策的 **Data Movement Manager（DMM）**目前似乎实现较少 `[该判断需向 SENSE 团队确认]`。团队需要重新阅读此前分享的 DMM paper，并决定是否把它作为网络 agent 的一个核心底层组件。

形成的架构倾向是：

```text
SciNet workflow / scheduling manager
  ├─ 理解 workflow DAG、dependency、deadline 与 priority
  ├─ 跨 workflow 做 negotiation、admission 与 scheduling
  └─ 请求所需 bandwidth / connectivity
                         │
                         ▼
              network agent / SENSE DMM
                         │
                         ▼
              SENSE / digital twin / network
```

本组不希望自己的贡献完全“消失”在 DMM 中。更合适的定位是：SciNet 的 scheduling / workflow manager 作为更高层实体，包裹或调用 DMM，并能持续适配 SENSE 正在开发的组件。会上提到的名称类似 **SciNet Workflow Manager** 或 **SciNet Network Flow Manager**，尚未定名。

## 十一、争取在 11 月 SC 做一个早期 agent demo

会上报告一篇论文已被接收为 short paper，预计可在 11 月 15 日的某个 workshop 发言；workshop 名称在转写中近似 “INDEX”，需核对正式名称。随后讨论了把 SciNet 的早期成果放进 Harvey 在 SC 的 Network Research Exhibition（NRE）展示中。

建议的最小 demo 是：【K】

- 一个含多个 task 的小 workflow；
- agent 理解 task dependency 和 deadline；
- 按正确顺序安排 task；
- 为数据传输请求合适 bandwidth；
- 用一个简单 Python prototype 展示 agent 正在优化某个明确指标。

虽然正式 NRE submission deadline 已过，但会上认为实际 demonstration 有时仍能在截止后加入。团队计划先写一份一至两页说明，清楚解释 NRE 内容及 projected impact，并启动一个简单 GitHub project。11 月版本可以只是起点，用来迫使团队尽早产出具体系统，并为年末 Phase 1 demo 积累实现。

## 十二、直接后续动作


| 后续动作                                                        | 负责人 / 时间                        | 状态与边界                                               |
| ----------------------------------------------------------- | ------------------------------- | --------------------------------------------------- |
| 请 Rafael 核对现有 workflow API 与学生提出的网络字段扩展                     | Linxuan、Sourabha、Rafael；下次完整汇报前 | 本周暂不仓促做 slides，下周形成更完整版本                            |
| 将四项 gate metrics 映射到 proposal milestones、日期、任务和 subteam     | Mariam、Rafael；两三天内              | 应按总体架构 component 拆分，不按四个 metric 建四套孤立工作             |
| 为 HEP 与 AI workflow 建立可信的简化表示和 baseline                     | Harvey、Rafael、Mariam（possibly）  | baseline 先用当前 framework；workload 与规模仍需确定            |
| 重新定义并发 workflow 的 fairness metric                           | KK 提出，具体负责人未定                   | 检查 Jain's index，考虑 proportional / max-min fairness  |
| 用 program manager 会议确认 Phase 1 gate metrics 的解释             | Mariam                          | 特别核对 failure / rebalance、资源预分配和正式时间表                |
| 调研 agent harness / guardrails 并分享材料                         | Mariam；下周                       | 尚未选定 framework；Harvey 可协调额外帮助                       |
| 请 SENSE 团队提供 flow redirection 案例和时间数据                       | 负责人未定                           | 核对 5 秒 detection、30 秒 recovery 及 L2/L3 分层假设         |
| 重读 SENSE Data Movement Manager paper，定义与 SciNet manager 的边界 | 参与 agent 设计的成员                  | DMM 可作底层组件，但不替代本组的 workflow/scheduling contribution |
| 为 Harvey 的 NRE 准备一至两页说明                                     | Mariam                          | 说明 agent-managed network demo 及 projected impact    |
| 启动简单 Python / GitHub agent demo                             | 具体负责人未定；目标为 11 月 SC             | 先展示小 workflow 的依赖、deadline、调度和 bandwidth request    |
| 确认 digital twin / Mininet 支持人选                              | Mariam 与相关合作方                   | 有合作方口头表示可帮忙，但姓名在转写中不可靠 `[待核对]`                      |




## 十三、仍待核对的问题


| 项目                                         | 当前记录                                                                               | 需要的权威来源                                      |
| ------------------------------------------ | ---------------------------------------------------------------------------------- | -------------------------------------------- |
| Phase 2 go / no-go 是否推迟到 1 月底或 2 月         | 会上转述，未确认                                                                           | Program manager 的正式通知                        |
| HEP 与 AI workflow 的最终实例和缩放方式               | Gate 已指定 Rubin-class HEP、nightly 20 TB ingest 和 512 V100 Summit GPUs，但可运行的抽象实例尚未决定 | Harvey / Rafael 给出的 workload 描述与 baseline 设计 |
| Jain's fairness index 与“fair share”的具体资源定义 | Gate 已确认要求 Jain ≥ 0.9，且最低优先级 flow ≥ 30% fair share；但 fair share 的分母和测量窗口未写明        | Proposal 完整定义及 program manager 认可的解释         |
| SENSE 的 5 秒检测、30 秒恢复能力                     | 合理性判断，未验证                                                                          | SENSE flow-redirection exercise 与实测数据        |
| DMM 当前实现成熟度及 SciNet 可对接接口                  | 会上称实现较少，未经维护者确认                                                                    | DMM paper、代码及 SENSE 团队说明                     |
| 11 月 workshop 的正式名称、日期及 NRE 加入方式           | 转写近似 “INDEX”、11 月 15 日                                                             | 论文接收信与 SC / NRE 官方安排                         |
| 会议室中三位参会者及发言归属                             | 截图无法识别姓名                                                                           | 原会议邀请或人工补充                                   |


