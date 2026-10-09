# Network agent  怎么设计

> 对于一个网络agent来说，如果要做到良好的多科学workflow场景下的调度，包括考虑网络容量、deadline、时间预约... 这个agent应该需要哪些信息，做到哪些设计，实现哪些功能。

## 0. 先换一个框架：这个 agent 的本质困难是什么

会议草图把 agent 画成「输入 workflow 需求 + 网络状态 → 输出 admission 与 schedule」，这看起来是个装箱问题。但把你的 SENSE 能力边界表叠上去，真正的困难暴露出来了：

> **workflow 的 deadline 是关于 achievable throughput 的，而网络能给的只有 model-level reservable capacity。agent 要在这两者之间做出可兑现的承诺。**

`5.2.6` 那一节其实是整个项目最关键的一句话：SENSE 说这条路能预约 100 Gbps，不代表 workflow 能测到 100 Gbps。而 deadline 只认后者。所以 agent 不是一个调度器，是一个**在信息不完备、且信息种类系统性错配的情况下做承诺并兑现承诺的系统**。这个 framing 比「多 workflow 调度」更有研究价值，也更容易在 Phase 2 里讲成一个 systems contribution。

---



## 1. 先定输出：agent 的决策变量有哪些

信息需求是被决策变量倒推出来的。如果只把输出定义成 admit / reject，就只需要很少信息；输出越丰富，需要的信息越多。可能的决策维度：


| 维度       | 决策内容                                | 备注                                                                             |
| -------- | ----------------------------------- | ------------------------------------------------------------------------------ |
| **准入**   | 接纳 / 拒绝 / 有条件接纳                     | 最基础                                                                            |
| **时间**   | 什么时候起、预约窗口多长、是否推迟                   | SENSE 有 `schedule.start/end/duration`，天然支持                                     |
| **带宽**   | 预约多少 capacity、什么 QoS class          | `guaranteedCapped` / `softCapped` / `anyAvailable` / `bestEffort` 四档本身就是一个降级阶梯 |
| **路径**   | 走哪条、是否 multipath、include/exclude 约束 | SENSE 有 `path_tprofile`，但你无法读回完整有序 route（5.2.2）                                |
| **切分**   | 一次传完 / 分成 N 段错峰 / 分成 N 条并行流         | 大传输可以在时间轴上被"摊平"                                                                |
| **顺序**   | 多个 pending workflow 的仲裁次序           | deadline + priority                                                            |
| **搬运对象** | 搬数据 vs 搬计算 vs 用已有副本                 | Pegasus 的 Data Reuse 那一步说明副本信息是存在的                                             |
| **抢占**   | 是否打断/降级已接纳的 workflow                | 需要"承诺可撤销性"语义                                                                   |
| **不做**   | 明确告诉用户做不到、并给 counter-offer          | 我认为这是最被低估的一个输出                                                                 |


**关键设计取舍**：如果 agent 只能回答 yes/no，它就没有存在价值(一个阈值判断就够了)。它的价值在于回答 **"不行，但如果你能接受 T+2h 起、40 Gbps、走另一条路，就行"** ——即输出一组**可行的 counter-offer**。这决定了下面所有的信息需求。

---



## 2. 信息需求：六层，逐层标注 SENSE 给不给



### L1 · 拓扑与可达性（SENSE 部分给）

- domain / edge point / peer point ✓
- terminal URI、VLAN pool、IP pool ✓
- **内部 node-link graph ✗**，有序 route ✗（5.2.1、5.2.2）

→ 推论：agent 的世界模型只能是一张 **domain-level 抽象图**，每个 domain 是一个带入口出口的黑盒。这不一定是坏事——它反而逼出一个干净的抽象层次，而且和 KK 说的「用户不提交 link-by-link」是一致的。但它意味着 agent **无法自己算瓶颈在哪**，只能把可行性判断委托给 SENSE 的 `total-block-maximum-bandwidth` 查询。这是一个重要的架构约束，值得单列。

### L2 · 时间轴上的容量（这是最大的缺口，也是最大的机会）

agent 真正需要的不是"现在剩多少"，而是一条**未来可用容量曲线**：

```
capacity_available(src, dst, t) for t ∈ [now, now + horizon]

```

SENSE 给的是 `total-block-maximum-bandwidth(start, end-before)` —— **一个时间窗口的点查询**，不是曲线，也没有批量接口。要做 deadline 可行性判断和多 workflow 错峰，agent 必须自己把这条曲线**重建**出来。

这里有一个非常具体、可测、可发论文的小系统问题：

> 用有限次点查询，重建/近似未来可用带宽曲线。查询多少次、在哪些时间点采样、如何在预约不断变化时增量更新、误差多大、代价多大。

我认为这是目前**最容易变成第一个可测假设**的东西（第 8 节会回到这一点）。

### L3 · 实时测量（SENSE 基本不给）

utilization、RTT、loss、jitter、queue —— 5.2.4 / 5.2.5 都是"尚未确认"。只有 SiteRM Debug API 的 `rapid-ping` / `traceroute` / `iperf` 这类**一次性主动探测**，且跨站点可访问性未知。

→ 推论：agent 需要一个 **probe planner**：主动测量是有成本的（占带宽、需要授权、有延迟），所以什么时候值得花一次探测去消除不确定性，本身是个决策问题。这是"agent"这个词真正有意义的地方之一。

### L4 · 端系统与可达吞吐（谁都没给，但决定成败）

DTN/GPU NIC 能力、PCIe/内存带宽、存储读写、TCP 拥塞控制、并行流数、MTU、host CPU。5.2.6 列全了。

→ 推论：agent 需要一个 **achievability model**：`achievable = f(reservable, path, src_host, dst_host, protocol, streams, RTT)`。这个 f 不可能从第一性原理写出来，只能**从历史传输里学**。这就要求 agent 有记忆——见 L6。

### L5 · workflow 侧（这是你们组正在定义的）

KK 已经圈定的：workflow/task/transfer 三层 deadline、priority、hard/flexible、endpoint pair、traffic demand。我想补几个**会议里还没提到、但调度器真正需要**的：

- **数据量的不确定性**：`size` 是精确值还是估计？估计的话方差多大？（很多 workflow 的中间产物大小是运行时才知道的）
- **可分性 / 可中断性**：这个 transfer 能不能被切成 chunk 错峰？中断后能不能续传？——决定了调度器的自由度，Pegasus 里完全没有
- **DAG 上的时间耦合**：transfer 的 deadline 不是独立的，它由下游 task 的启动时间决定。agent 拿到的应该是 DAG + 每个 task 的运行时估计，才能自己推导出 transfer 的 latest-start-time（关键路径）。**只给一堆扁平的 transfer deadline 会丢掉可调度性信息**
- **弹性 / 效用函数**：晚 10 分钟的损失，和晚 2 小时的损失，是一样的吗？binary deadline 会让调度器过度保守。一条 utility-vs-completion-time 曲线信息量大得多
- **替代方案**：这份数据在别的站点有副本吗？这个 task 能不能换个站点跑（把计算搬到数据边）？
- **重算 vs 重传的代价**：失败时的恢复选项
- **周期性 / 可预告性**：APS 这类光源设施的 beamtime 是提前排好的——**未来的需求是部分已知的**，这对 proactive admission control 是巨大的信息优势，值得作为一等公民字段



### L6 · 历史与自我记忆（完全没人提，但我认为是 agent 区别于 scheduler 的核心）

- 每次预约了多少 / 实际测到多少 → 校准 L4 的 f
- 每次承诺的完成时间 / 实际完成时间 → 校准自己的置信度
- SENSE 的 `reservable` 数字历史上有多准 → 学出一个 safety margin
- 哪些路径/站点对历史上表现不稳定 → 风险画像

**没有这一层，agent 每次都在犯同样的错误。**

---



## 3. 三个语义陷阱 → 世界模型必须带 provenance

你那份文档已经在手工做这件事了，我建议把它**形式化成 agent 的数据结构**。三个陷阱：

1. `reservable ≠ available ≠ achievable`（模型量 / 预约量 / 实测量）
2. `STABLE ≠ 性能达标`（配置状态 ≠ 数据面性能）
3. `拓扑可达 ≠ 服务可拼接`（VLAN/MTU/adaptation 不兼容）+ `逻辑独立 ≠ 物理独立`（SRLG 未知）

→ agent 内部每个数字都不应该是裸 float，而应该是：

```
Fact {
  value, unit,
  semantics: physical | reservable | allocated | measured | predicted,
  source: sense-discovery | sense-query | manifest | siterm-probe | history | assumption,
  timestamp, valid_until,
  confidence
}

```

**这个"带来源与语义标注的 network fact base"本身就可能是一个可交付的设计贡献**——因为你们的调研已经证明，混淆这些语义是这个领域的真实、普遍的错误来源。而且它天然回答 KK 的问题："哪些信息 SENSE 有、哪些是 assumption"——assumption 在数据结构里是显式的、可枚举的、可以拿去找 Tom Lehman 核对的。

---



## 4. 架构：八个模块

```
  workflow 侧 (WfFormat+)                    network 侧 (SENSE / digital twin)
         │                                              │
         ▼                                              ▼
  ┌─────────────┐                              ┌──────────────────┐
  │ Intent      │                              │ Network Fact     │◄─┐
  │ Normalizer  │                              │ Base (带 provenance)│  │
  └──────┬──────┘                              └────────┬─────────┘  │
         │  DAG + 三层 deadline + 弹性              时间轴容量曲线 │      │
         ▼                                              ▼          │
  ┌────────────────────────────────────────────────────────┐      │
  │  Feasibility Engine  (关键路径 → latest-start-time)      │      │
  │  Achievability Model (reservable → achievable，学习型)   │      │
  └──────────────────────────┬─────────────────────────────┘      │
                             ▼                                     │
  ┌────────────────────────────────────────────────────────┐      │
  │  Scheduler / Arbiter  (时间轴装箱 + 路径选择 + 优先级仲裁)  │      │
  │  输出: admit / defer / counter-offer / reject            │      │
  └──────────────────────────┬─────────────────────────────┘      │
                             ▼                                     │
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
  │ Intent       │    │ Probe        │    │ Commitment   │        │
  │ Compiler     │    │ Planner      │    │ Ledger       │        │
  │ →SENSE JSON  │    │ 成本感知主动测量│    │ 承诺 vs 兑现  │        │
  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘        │
         └───────────────────┴───────────────────┴────────────────┘
                             ▼
              Execution Monitor → 偏差检测 → reactive reschedule

```

八个模块，逐一说它为什么必须独立存在：

1. **Intent Normalizer** — 把 workflow 的多种表达（WfFormat、Pegasus DAX、用户口头）归一，并**推导**出网络请求。核心动作：从 DAG + task runtime 反推每个 transfer 的 latest-start-time 和 earliest-useful-time。
2. **Network Fact Base** — 第 3 节的带 provenance 世界模型 + 时间轴容量曲线。是 agent 的唯一网络真相来源，所有其他模块只读它。**Digital twin 和真实 SENSE 在这一层背后互换**（正好落实 KK 第七节「共享 core API」的要求）。
3. **Feasibility Engine** — 三层递归可行性：单个 transfer 能否在窗口内完成 → task 序列能否满足 → 整个 workflow 能否满足。输出不只是 bool，而是 **slack**（还剩多少余量）和 **binding constraint**（是哪一段卡住的）。
4. **Achievability Model** — reservable → achievable 的映射 + 不确定性区间。**冷启动时是保守常数（比如 0.6×），随历史数据校准**。这一层的存在与否，决定 agent 的承诺是不是空头支票。
5. **Scheduler / Arbiter** — 真正的优化核心。**注意：这里不该用 LLM**，见第 6 节。
6. **Intent Compiler** — 决策 → SENSE `ServiceIntent` JSON，处理 `propagate/commit` 两阶段（这对多资源协同调度很重要：可以先算不提交，全部可行才 commit），处理 `modify` 做在线调整。
7. **Probe Planner** — 决定何时花代价做主动测量。信息增益 vs 成本。
8. **Commitment Ledger** — 记录每一条承诺（谁、什么时候、多少带宽、承诺完成时间）与实际兑现。**这是 agent 唯一的自我评估依据，也是 demo 里最有说服力的图表来源。**

---



## 5. 功能清单：可以做成 demo 的

按"能不能在 12 月讲清楚"排序，我把想到的都列出来：

**核心闭环类**

- **Deadline 可行性判定**：给定新 workflow，回答能否在 deadline 前完成，并指出 binding constraint
- **Counter-offer 生成**：不行的话，给出最近的可行替代（延后多久 / 降到多少带宽 / 走哪条路）——这是我认为最能体现 agent 价值的功能
- **多 workflow 错峰**超容量时，在时间轴上自动错开，两个都不误 deadline。**这正好是 KK 要的 12 月 demo**
- **降级阶梯**：deadline 保不住时的自动降级序列（推迟 → 降带宽 → `guaranteedCapped` 降到 `softCapped` → best-effort → 换副本 → 搬计算不搬数据）
- **执行期偏差检测与重调度**：实测 throughput 低于预期 X% 时触发 `POST /instance/{uuid}/modify` 或重规划

**信息层类**

- **未来可用容量曲线重建**（用有限点查询）
- **主动探测规划**：什么时候值得跑一次 iperf
- **Achievability 校准**：从历史传输学 reservable → achievable

**决策解释类**

- **可解释性**："为什么我的 workflow 被推迟了 2 小时"——对科学家可读的因果链。这一条对 DOE 这种多机构环境非常重要，也是 LLM 唯一真正不可替代的地方
- **What-if / 反事实**："如果给这个 workflow 加 20 Gbps，谁会受影响"
- **假设审计**：列出当前所有决策依赖的 assumption（Fact Base 里 source=assumption 的项），直接产出一张可以拿去找 SENSE 团队核对的表

**韧性类**

- **保守独立性假设下的路径冗余**：SRLG 未知（5.2.3），agent 必须显式承认"我不知道这两条路是否物理独立"，并把它作为风险而非事实处理
- **故障后重规划**：链路失效后重新仲裁已接纳的集合

---



## 6. 一个我觉得容易被做错的设计点：LLM 该放在哪

KK 一直说 "agent"，但**多 workflow 时间轴装箱是一个组合优化问题，不该交给 LLM**。LLM 在这个系统里的正确位置我认为是三个：


| 该用 LLM                                       | 不该用 LLM                           |
| -------------------------------------------- | --------------------------------- |
| Intent 归一化（把异构 workflow 描述、甚至自然语言需求翻译成结构化请求） | 调度求解（用 MILP / 启发式 / 贪心，可验证、可复现、快） |
| 缺失信息的推断与追问（"你没给 task runtime，我按 X 假设，对吗"）    | 可行性判定（确定性计算）                      |
| 解释与协商对话（为什么被拒、counter-offer 的说明）             | 容量核算（绝不能让 LLM 算数字）                |
| 工具编排（决定调哪个 SENSE API、要不要探测）                  |                                   |


这条边界值得写进设计文档——它能防止一个常见失败模式：**用 LLM 做数值决策，然后 demo 里出现"调度总量超过 capacity"这种致命错误**，而这恰恰是 KK 在第三节点名要求保证的事（"确保被并发调度的任务总需求不超过系统 capacity"）。

---



## 7. 评估口径：demo 该量什么

如果 12 月要证明 agent 有用，需要一个 baseline 对照。我想到的度量：

- **deadline 满足率**（vs. network-blind 的 baseline——Pegasus 的 Site Selection 五个算法全部 network-blind，这是你们文档里已经指认的现成对照组，非常好用）
- **capacity 违约次数**（必须是 0，这是 correctness 而非 performance）
- **承诺兑现误差**：预测完成时间 vs 实际完成时间的分布 ← 来自 Commitment Ledger
- **counter-offer 接受率 / 被拒 workflow 的等待时间**
- **信息代价**：达成上述效果用了多少次 SENSE 查询、多少次主动探测
- **对信息缺失的敏感度**：把 telemetry 逐项拿掉（模拟 SENSE 真实给不了的情况），看性能退化多少 ← **这个实验直接把你们的能力边界调研变成了实验变量，我觉得是最漂亮的一个**

---



## 8. 收敛：如果只做一件事

上面发散了很多，但按 §7 只给一个建议。我认为最值得先做的是：

> **把"未来可用容量曲线"作为第一个可测的系统问题。**

理由：① 它是 deadline 调度的**必要前提**，没有它整个 agent 的时间维度就是假的；② 你们的 SENSE 调研已经**证明**这是一个真实缺口（只有点查询，没有曲线，没有批量接口）——这是 KK 要的"确切缺口"里最硬的一条；③ 它可测（查询次数 vs 重建误差），可以在 digital twin 或纯模拟上先做，不依赖真实 SENSE 部署授权；④ 它同时喂给三件事：admission control、错峰装箱、找 Tom Lehman 核对时的具体技术问题。

具体到下一步：先不写代码，先把「agent 需要什么信息 / SENSE 给什么 / 缺口在哪」做成第 2 节那张六层表，**每一行标注 SENSE 证据链接和缺口性质**——这既是 KK 第六节要的缺口清单，也是 Exp2 的 S4 crosswalk 的自然延伸。