# Overview

> 所以整个overview其实就只有四个块：workflow->scheduling agent->network agent->sense-o，对吗

主链对，但**这四块是数据通路，不是系统全貌**。有三样东西不在这条链上——而它们恰好是我们这套设计的贡献所在。

## 不在链上的三样

**① 人**

Tier 2 的解释与协商接口是从 scheduling agent **横着出去**的，不在四块串联里。11 月 demo 里"能问为什么"的那个面就挂在这儿。

**② 三条回路**

链是单向箭头，但我们设计的每一处关键机制都是反向的：


|     | 路径                                            | 时间尺度  |
| --- | --------------------------------------------- | ----- |
| 快回路 | network agent 内部：偏差检测 → 自修                    | ≤30 s |
| 慢回路 | `at_risk` → scheduler 重新仲裁                    | 分钟    |
| 长回路 | 执行事实回流（**两条源**）→ 估计与 achievability 校准 → 下一次规划 | 跨 run |


**这三条回路才是 "agent" 的实质。** 只画那条四块的链，任何一个 network-aware workflow 系统都能画出同样的图，看不出我们做了什么。链是骨架，回路是肌肉。

**③ schema 不是链上的一站**

WfFormat / WfPlatform / WfCampaign 是**旁挂在第一格上的数据模型**，不是流程的一步。

而且 WfPlatform 有个位置上的尴尬：**它描述的是网络，却挂在 workflow 侧**，和 network agent 的 capacity ledger 撞车。这个可以干净地切开：

- **WfPlatform = 静态拓扑快照**（它自带 `measuredAt` / `measurementMethod`，本质就是快照）→ 作为 ledger 的**初始化输入**
- **capacity ledger = 动态时间轴 + own 层**（谁在什么时段占了多少）→ 必须在 network agent 内部，外部 schema 表达不了

两者不重复，是 seed 和 state 的关系。这也正好把 0907 那个悬置的问题（WfPlatform 到底该不该存在）落定了：**静态那半留在 schema，动态那半进 agent。**

## 建议的 overview 画法

```
                            人（科学家 / 运维）
                                   ▲
                        解释 / 协商 │ Tier 2，自然语言
                                   │
Workflow 系统 ──submit/refine──▶ Scheduling ──quote/hold/commit──▶ Network ──ServiceIntent──▶ SENSE-O
 WfFormat      ◀───执行计划─────    Agent    ◀──repaired/at_risk──  Agent   ◀──state/telemetry──  或 twin
 WfPlatform                          │                               │        （③b 主动拉：刷新 + probe）
 WfCampaign                          │                          ① 快回路
      │                              │                               │
      └──③a report───────────────────┴──转发网络部分──────────────────┘
         task 时间、文件落点                                    在此配对
         实测字节数 / 耗时 / 并行流数                    reserved vs achieved
                                                                ↓
                                                ③ 长回路：校准 achievability + estimates
                                     ② 慢回路：at_risk 上行，Scheduling 重新仲裁
```

四站 + 一个人机侧接口 + 三条回路（其中长回路有两条源）。

## 三条回路



### **快回路：自修的手段，按代价从低到高**

前提：修完后 `predicted_finish` 仍 ≤ `latest_finish`，否则不叫修好。


| 手段           | 碰 SENSE 吗    | 适用                       |
| ------------ | ------------ | ------------------------ |
| 加并行流 / 调传输参数 | 否            | 差距在端系统（TCP 跑不满），根本不是网络问题 |
| 提速补量         | `modify` 改带宽 | 账本上后续时隙还有余量，把落后的量赶回来     |
| 往后挪，吃 slack  | 账本本地操作       | 当前时段拥塞，但 deadline 还宽裕    |
| 换电路          | 电路池里现成的      | 到同一目的地有另一条保温电路           |
| 重新 provision | 慢，可能超 30 s   | 前面都不行才用                  |


**共同点：全部只动这一条 commitment 自己。**

### **慢回路：动别人**

`at_risk` 上来之后，scheduling agent 能做而 network agent 做不了的事——因为每一样都要影响**其他 workflow 或上游系统**：

- **降级自己**：接受更晚的完成时间（utility 曲线允许的话），改 SLA
- **抢占别人**：让低优先级 workflow 让出容量
- **重排下游**：这条传输晚了，把下游 task 的计划启动时间整体后移，通知 workflow 系统
- **换副本源**：从另一个副本重传，走另一条路
- **放弃**：告诉用户赶不上了，给 counter-offer

> 一句话区分：**快回路只动自己，慢回路要动别人。** 所以权限必须在 scheduling agent——只有它有跨 workflow 的视图和仲裁权。



### **长回路：跨 run 校准，改的是下一次的输入**

执行事实**分两条源回流，不是一条**：


|        | 内容                                                              | 谁知道                                              | 路径                                                           |
| ------ | --------------------------------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| **③a** | task `readyAt` / `startedAt` / runtime、文件落点；实际传了多少字节、用了多久、几条并行流 | **只有 WMS**（后半来自 Globus / GridFTP / Rucio 这类搬运工具） | WMS ──`report`──▶ Scheduling agent ──转发网络部分──▶ Network agent |
| **③b** | 链路状态、利用率、丢包、实际路径                                                | **SENSE / twin**                                 | Network agent **主动拉**（observed 层的周期刷新 + probe）               |


**为什么③a 要多转一跳**：achievability model 在 network agent 那儿，而它要学的是一对数——

```
reserved   预约了多少   ← Network agent 自己的账本（own 层）
achieved   实际跑到多少 ← ③a 报上来的 duration / bytesTransferred，或 ③b 的探测
```

这一对分别来自不同的源，**必须在 network agent 里配对**。Scheduling agent 自己留着那半没用，模型不在它那里。

**顺带分清两份** `execution`：`WfFormat.execution` 那份文档**归 WMS**——它是 workflow 的运行记录，给外部看的产物，我们只贡献其中的网络字段（`transfers[]`、RTT、并行流数），不拥有它。我们内部长回路用的是同一批事实的另一个副本，存在 Commitment Ledger 里，服务于校准而非归档。

拿这些校准两样东西：

- **achievability model**：`achievable = f(reservable, 路径, 主机, 协议, 流数, RTT)` 的参数。冷启动用保守常数（0.6×），积累后按站点对、按时段收紧。决定 `predicted_finish` 是真承诺还是空头支票。
- **estimates**：task runtime、文件大小、已有副本——即第 12 页那格 `WfCampaign.estimates`，由 Tier 2.5 从历史 execution 推出来。

时间尺度是**跨 run** 的：它不影响当前这次执行，只让下一次的规划更准。这就是为什么它是第三条回路，不是第三种自修手段。

#### 为什么schedule agent需要执行回写的信息

因为**两个 agent 各有一个学习对象，各自需要自己的历史**——这是对称的：


|                      | 学什么                       | 需要的历史                       |
| -------------------- | ------------------------- | --------------------------- |
| Network agent        | `reservable → achievable` | 预约了多少 vs 实测跑到多少             |
| **Scheduling agent** | `估计 → 实际`                 | **估的 runtime / 数据量 vs 实际的** |


具体四个用途：

**1. 产出** `WfCampaign.estimates` **的训练数据。**

那一格（task runtime、预计启动时间、文件大小、已有副本）是 Tier 2.5 从历史 execution 推出来的。而 Tier 2.5 挂在 Scheduling agent 这一侧——**估计模型在它那儿，就像 achievability model 在 network agent 那儿**。没有历史，估计只能靠先验瞎猜。

**2. 校准它自己计划的现实性。**

它发出去的执行计划里有 `taskSchedule`（建议启动时间）。WMS 实际几点起的？如果**系统性偏晚**，说明它的计划没考虑 GPU 排队之类的现实，下次得留余量。这是对**它自己**的校准，跟网络无关。

**3. 判断 WMS 听不听话。**

计划是建议不是命令。如果某个 WMS 长期不遵守 `taskSchedule`，Scheduling agent 应该降低对它的预期——比如不再基于建议启动时间做紧凑规划，改用更保守的窗口。**这个判断只有收到回报才做得出来。**

**4. 承诺兑现与 fairness 的记账。**

每个 workflow 实际拿到了多少 slot·bandwidth 面积、承诺的完成时间兑现了没有。这是 Commitment Ledger 在 workflow 侧的对应物，也是 demo 里最有说服力的那张图（承诺 vs 兑现的分布）的数据来源。

### PS：refine - refine有啥用？

**核心：workflow 是渐进展开的，提交时的估计到中途已经不对了。**

没有 refine，agent 拿着一堆过期猜测把整个 DAG 规划到底，等发现不对时 slack 已经用光。

#### 被 refine 的四类事实


| 事实               | 触发时机         | 后果                                    |
| ---------------- | ------------ | ------------------------------------- |
| 中间产物的**实际大小**    | 上游 task 写完文件 | `is_estimate` 那个字段的真值来了               |
| task 的**实际完成时间** | task 结束      | 所有下游 transfer 的 `earliest_start` 整体平移 |
| 副本**实际落点**       | 文件落盘         | 后续传输的 `src` 变了                        |
| 分支**实际走向**       | 条件判定         | 某些 transfer 根本不需要了                    |




#### 它能换来什么

**1. 释放超估的容量。** 估 20 TB 实际 5 TB —— 预约的时段可以退回去给别人。没有 refine，多占的容量白占到底，别的 workflow 排不进来。

**2. 提前预警。** 估 5 TB 实际 20 TB —— **现在**就知道赶不上，还有时间重排或协商。不 refine 就要等传输跑到超时才发现，那时候什么都来不及了。

**3. 平移下游。** 最常见的一种：上游 task 因为 GPU 排队晚了 40 分钟，所有下游 transfer 的窗口整体后移。不平移的话，电路按原计划开了，数据还没产出——**预约的容量空转，而这正是我们要消灭的浪费**。

**4. 改变传输本身。** 分支走向定了、副本落点变了，S0 的拆解结果就变了，有些 transfer 消失、有些换了源。

#### 和 report 的区别

两个动词看起来重复，其实方向相反：

- `refine` **是前瞻的**——改变**尚未执行**的计划
- `report` **是回顾的**——记录**已经发生**的，喂给长回路做校准

同一个事实往往两边都要走一遍：task 完成时间既让下游重排（refine），又进 execution 记录训练估计模型（report）。

#### 一处必须设阈值

不能每个 task 一完成就触发全量重规划——开销受不了，而且计划反复抖动，WMS 那边跟不上。

所以要有个**容差**：偏差在阈值内就只更新账本、不重规划；超过阈值才重新 quote。这个阈值定多少、要不要随 slack 剩余量自适应，是 Tier 3 的一个 policy 点——**先用规则（固定百分比），做成可替换接口**。

## Achievability model 的作用

它是一个学习型映射，不是一张历史数值表：achievable_rate = f(reservable, 路径, 两端主机, 协议, 并行流数, RTT, 文件大小)，并带一个不确定性区间。参数从历次 execution.transfers[] 回归得到，冷启动用保守常数（如 0.6×），积累后按站点对、按时段收紧。

为什么需要它：SENSE 说这条路能预约 100 Gbps，实测可能只有 60，而 deadline 只认后者。这个差距多数不来自网络过载——网络那 100 是真的留住了，跑不满是因为端系统：NIC、PCIe、磁盘读写、TCP 单流在长肥管道上的行为、MTU。

### 四个作用

第一，算出可兑现的完成时间。调度真正要回答的是"如果给它 X Gbps，它什么时候完成"，X 是我们的决策变量，历史记录里的那个 duration 只是这条曲线上的一个点。按 reservable 算完成时间会系统性地承诺过早，下游 task 跟着排错位置，整个 DAG 顺延。

第二，让预约贴合实际。如果稳定只能跑 60，申请 100 就是把 40 锁死不让别人用。校准的结果往往是申请更少而不是更多，它减轻而非加剧网络压力。

第三，给出不确定性区间。这决定 safety margin 留多少、offer 里 confidence 填什么。留多了浪费容量，留少了违约。

第四，归因诊断。同样是"约 100 跑到 60"，成因不同修法完全不同：差距在端系统时，换路径也一样慢、差距稳定，应对是调并行流数或换 DTN，并把预约按实际下调；差距在网络侧时，差距会波动、和时段相关，应对是换路径、发 at_risk、标记该路径不可靠。没有归因，快回路就不知道该调参数还是该换路径。

**总结**：reservable（SENSE 给的）和 achievable（deadline 认的）之间隔着一层，achievability model 就是那一层。没有它，predicted_finish 是空头支票。

# Agent的切法

**按"面向谁说话"切**

- **scheduling agent** 讲 *workflow 语言*：DAG、依赖、task deadline、priority。它做的是从 DAG 反推每个 transfer 的 latest-start-time（关键路径），以及跨 workflow 的时间轴装箱与仲裁。
- **network agent** 讲 *网络语言*：它是唯一碰 SENSE 的模块，持有 network fact base（容量曲线、provenance、achievability 校准），对外只暴露一个 **quote 接口**：`能否在 [t1,t2] 给 A→B 的 X Gbps?` → `yes / no / counter-offer(t', X', 置信度)`。

> **1. 容量曲线**
>
> 未来每个时隙还剩多少可用带宽，按 (src, dst) 建账。SENSE 只给点查询（问一个时间窗答一个数），曲线要我们自己用有限次查询拼出来并增量维护。没有它就只能回答"现在能不能"，回答不了"什么时候能"。【Q：多久查一次？或者说有什么触发条件吗？】
>
> **2. provenance（来源与语义标注）**
>
> 账本里每个数字都不是裸 float，而是带标签的：
>
> ```
> Fact { value, 
>        semantics: physical | reservable | allocated | measured | predicted,
>        source:    sense-query | manifest | probe | history | assumption,
>        timestamp, valid_until, confidence }
>
> ```
>
> 存在的理由：`reservable ≠ available ≠ achievable`，这三个数混用是这个领域最常见的错误来源。标注之后，"哪些是 SENSE 给的、哪些是我们假设的"可以直接枚举出来——正好是 KK 要的那张缺口表。
>
> **3. achievability 校准**
>
> SENSE 说这条路能预约 100 Gbps，实际传输测到的可能只有 60。deadline 只认后者。
>
> 所以需要一个映射 `achievable = f(reservable, 路径, 两端主机, 协议, 并行流数, RTT)`。这个 f 写不出解析式，只能**从历史传输里学**：每次预约了多少、实际测到多少，回归出比例和误差带。冷启动用保守常数（比如 0.6×），跑多了逐渐收紧。
>
> 它决定 `predicted_finish` 是真承诺还是空头支票——三者的关系是：**曲线给时间维度，provenance 给可信度，校准给兑现率。**



## 关于achievability的校准

> 我没懂的是，既然申请了100只给了60，不是说明网络有问题吗，比如过载。为什么要学习，比如申请150使得给我100，这不会加剧网络状况吗

你的担心是对的——**申请 150 拿 100 是绝对不能做的事**，那是把 50 的容量锁死不让别人用，而且大概率还是拿不到 100。学习不是为了这个。

**先纠正一个前提：60 这个差距，多数不是网络过载。**

SENSE 确实在路径每条链路上把 100 给你留住了，那 100 是真的空在那儿。跑不满是因为瓶颈在**网络之外**：

- DTN 的 NIC / PCIe / 内存带宽 / 磁盘读写
- 单条 TCP 流在高 RTT 长肥管道上本来就跑不满，要靠多流
- MTU、协议开销、主机 CPU

所以申请 150 无济于事——**端系统是 60，网络给再多也是 60**，只是多浪费了 50。

**那学它干什么？为了改承诺，不是改申请。**

知道这对站点的 achievable ≈ 0.6 × reservable 之后，5 TB 的完成时间要按 60 Gbps 算，不能按 100 算。否则：

```
按 100 承诺 → 说 11 点完成 → scheduler 把下游 task 排在 11 点
实际 60     → 13 点才完成 → 下游 GPU 空转 2 小时，整个 DAG 顺延

```

**错的不是传输，是承诺。** 校准修的是这个。

**而且学习的结果往往是申请更少，不是更多**。如果稳定只能跑 60，那申请 100 本身就是浪费——应该只申请 65，把 35 让给别人。这跟你担心的方向正好相反：**校准让预约更贴合实际，是在减轻网络压力，不是加剧。**

**最后，两种成因要分开，处理方式完全不同：**


| 差距来源                   | 怎么判断         | 应对                       |
| ---------------------- | ------------ | ------------------------ |
| 端系统                    | 换路径也一样慢；差距稳定 | 调并行流数 / 换 DTN；预约按实际能力下调  |
| 网络侧（丢包、SENSE 看不见的竞争流量） | 差距波动、和时段相关   | 换路径、发 `at_risk`、标记该路径不可靠 |


区分这两者正是 achievability model 和 probe planner 存在的理由——**没有它，你连"该改主机还是该改路径"都不知道。**

---



# Scheduling到Network Agent的通信协议：Scheduling怎么问



## 一条原则先立住

**scheduling agent 发的是"需求"，不是"方案"。**

它不该说"给我 40 Gbps"——那已经是个答案了。它该说"这 5 TB 要在 t1 之后开始、t2 之前到"。带宽 × 时长的分配是 network agent 的决策变量。理由：`bytes / deadline` 是欠定的，同一份需求有无数 (rate, window) 解，只有 network agent 看得见容量曲线，才知道哪个解不撞车。

> **欠定（underdetermined）:** 约束比未知数少，解不唯一。5 TB 要在 10 小时内传完 → 满足的方案有无数个：10 Gbps 传 4 小时（早传完）、4 Gbps 传 10 小时（刚好卡点）、前 2 小时 20 Gbps 后面停……`bytes` 和 `deadline` 只框定了"面积"，没定"形状"。

如果反过来（scheduler 指定带宽、network agent 只答 yes/no），network agent 退化成一个 SENSE 转发器，没有存在价值，错峰也无从做起。

## 五个动词，不是一个

```
quote(bundle)        → 只读、不占资源、"你能给我什么"
hold(offer, ttl)     → 试探性预留，对应 SENSE propagate
commit(hold_id)      → 落实，对应 SENSE commit
modify / release     → 在线调整、释放
[异步上行] at_risk   → network agent 主动上报承诺有风险

```

> **bundle:** 一次 quote 里打包的**一组** TransferRequest，通常就是一个 workflow 里所有需要过网的传输。之所以要打包而不是一条条问：workflow admission 是全有全无的——某个 workflow 的 5 个传输里有 1 个排不进去，整个 workflow 就不该被接纳，前 4 个也不该占着资源。一条条问就表达不了这个语义。
>
> **propagate:** SENSE 的 `PUT /instance/{siUUID}/propagate`。它把 intent 算完、把资源**预留下来但不真正下发网络配置**。相当于"占位，先别通电"。
>
> **SENSE 两阶段接口:** `propagate → commit`，替代一次性的 `provision`（见 [20260904_senseinfo.md:977](vscode-webview://1phmkifadvafmq050o9ejvc05u02om7lg4v1kj41q46aeaishk3h/resources/20260904_senseinfo.md#L977)）。你的笔记里原文写的用途正是"**更适合多个网络和计算资源的协同调度**"——先 propagate 一批占住，全都成功再逐个 commit 下发；有任何一个失败就 `rollback`/`release`，不会留下半个配好的 workflow。相关动词全集：`provision / cancel / reprovision / propagate / release / reinstate / commit / rollback / verify`。注意这是 SENSE 已有的能力，不是我们要造的——我们的 hold/commit 只是把它向上转发一层。
>
> **五个动词里前四个是 scheduling → network 的下行调用:** `quote / hold / commit / modify / release` = scheduling agent 调 network agent。 `at_risk` 是**上行**的，network agent 主动推给 scheduling agent（因为只有 network 侧在做实时测量，而重排决策权在 scheduling 侧）。所以这个接口是**非对称双向**的：下行请求-响应，上行事件推送。这一点值得在 slides 里画清楚，否则容易被误解成单向 API。

`hold` **是这份协议里最重要的一个。** 没有它，scheduler 在 quote 和 commit 之间世界已经变了，它手上的计划是过期的。有了它，scheduler 可以把一整个 workflow 的所有 transfer 先 quote 一圈、全部 hold 住、确认都可行才原子 commit——这正是 workflow admission 的正确实现方式，而且 SENSE 的两阶段接口白送了这个能力。

最后那条**异步上行**要现在就写进协议：偏差检测发生在 network 侧（只有它在测），重排决策发生在 scheduling 侧。所以这不是纯 request/response，有一条向上的事件通道。0908 要的 5 秒检测 / 30 秒恢复，就落在这条通道上。

## 例子

```
quote(bundle = [T1, T2, T3])
   → T1: offers [a1, a2, a3]      ← 同一个 transfer 的三种方案，互斥
     T2: offers [b1, b2]
     T3: offers [c1, c2, c3]

scheduler 在本地组合搜索，选出一套：a2, b1, c3

hold([a2, b1, c3], ttl) → hold_id     ← 整个 bundle 一个 hold_id
commit(hold_id)                        ← 原子提交
```

其中T1:

```
TransferRequest T1: 50 TB, window [09:00, 15:00]

账本状态：09:00–12:00 只剩 40 Gbps（别人占着）
          12:00 之后有 100 Gbps 空

offers:
  a1  09:00 起 @ 40 Gbps  → 13:47 完成    立刻开始，慢，占 40G 近五小时
  a2  12:00 起 @ 100 Gbps → 13:07 完成    晚起但更早完成，只占一小时
  a3  09:00 起 @ 20 Gbps  → 14:34 完成    最小占用，slack 几乎用尽
```

**三个都可行，没有一个绝对最优**——它们是可行前沿（Pareto front）上的点：

- a1 早开始，出问题还有时间重试，但**霸占早上的容量五小时**
- a2 完成最早、占用最短，但**12 点前完全没有缓冲**，一旦延误就没救
- a3 最省容量，代价是几乎不留 slack

**选哪个取决于别的 workflow 需要什么**——而那是 scheduling agent 才知道的信息，network agent 不知道。所以它不替你选，只把可行的都摆出来。

## 消息形状（第一版）

```
TransferRequest:
  id, workflow_id, priority
  src, dst
  bytes            + is_estimate: bool     ← 中间产物大小常常只是估计
  window: [earliest_start, latest_finish]
  divisible: bool                          ← 能否切成 chunk 错峰
  min_useful_rate                          ← 低于这个速率不如不传

QuoteRequest:
  bundle: [TransferRequest]
  mode: all_or_nothing | best_subset       ← workflow admission 用前者

QuoteResponse (per transfer):
  status: feasible | infeasible
  offers: [ { start, rate_profile, predicted_finish,
              confidence, qos_class } ]    ← 给 1~k 个备选，不是一个
  binding: { when, blocked_by: own_commitment(id) | foreign_traffic }

```

两处刻意的设计：

`offers` **是复数。** 这就是 counter-offer 的载体，而且是**结构化**的、能直接进 scheduler 优化器的，不是给人看的一句话。infeasible 时也要给 offers——"最早能到的是 t'，或者你接受 X' 速率就能赶上 t2"。

`blocked_by` **只需两个值。** 我原本想让 network agent 报"被哪个 workflow 挡住"，但想了一下不必要：scheduler 自己就知道它做过哪些承诺。真正有信息量的区分是 `own_commitment`**（我可以抢占/让路）** vs `foreign_traffic`**（不归我管，只能绕）**——后者就是 0908 里那个 background HEP traffic 场景。这条区分一给，priority 仲裁就从盲目试错变成有向搜索。

`predicted_finish` 带 `confidence`，是 achievability model（reservable ≠ achievable）在协议层的第一次露面——network agent 承诺的是**实测能到的完成时间**，不是 SENSE 说的预约容量。这条也是你 0907 笔记里那个"承诺与兑现"的落点。

## 字段解释

**1.** `bytes` **+** `is_estimate`

数据量，加一个布尔标记它是精确值还是估计。中间产物的大小往往运行时才知道。

影响两件事：估计值让 network agent 在 `predicted_finish` 上留余量、把 confidence 打折；后续 `refine` 把它换成真值时触发增量重规划。（更完整的做法是带方差，v1 用布尔够了。）

**2.** `divisible`

这个传输能不能被切成时间上不连续的几段、中断后能否续传。

- 可分 → 调度器可以在时间轴上"摊平"，见缝插针，自由度大
- 不可分 → 必须一次连续传完，只能整块找位置

例子：支持断点续传的大文件传输可分；要求连续的流式管道不可分。这是"切分"那个决策维度的入口。

**3.** `min_useful_rate`

低于这个速率就不如不传。两个理由：下游 task 等不及，或协议层会超时。

更实际的一条：**占着 5 Gbps 传三天，不如等有 100 Gbps 时一小时传完**——低速传输既长期占资源又不产出价值。这个字段给 network agent 一个下界，避免它返回"技术可行但无意义"的 offer。

**4.** `all_or_nothing` **|** `best_subset`


| mode             | 语义                          | 用途                                                |
| ---------------- | --------------------------- | ------------------------------------------------- |
| `all_or_nothing` | 全部排得下才算成功，一个不行整批 infeasible | **workflow admission**——默认模式                      |
| `best_subset`    | 尽量排，排不下的告诉我是哪些              | 探索性 quote（想知道瓶颈在哪）；或 workflow 本身允许部分降级（比如可选的预览输出） |


**5.** `status`**：建议三档**


| 值             | 含义                                              | scheduler 怎么反应          |
| ------------- | ----------------------------------------------- | ----------------------- |
| `feasible`    | 窗口内有可行放置                                        | 从 offers 里选             |
| `infeasible`  | 窗口内排不下，**但仍返回 offers**（最近的可行替代 = counter-offer） | 重排、协商、降级                |
| `unreachable` | 结构性不可能——端点不可达、拓扑上没路、VLAN/MTU 不兼容                | **这不是调度问题，是配置问题**，只能报给人 |


前两档是调度问题，第三档是配置问题，应对方式完全不同，所以值得分开。

**6.** `confidence`**：不建议做成离散档位**

它是 achievability model 输出的不确定性，本质连续。而且 scheduler 真正要做的决策是"**留多少 slack**"——一个 0.8 的分数没法直接算 slack。

**更好的形式是让** `predicted_finish` **带区间**：`{p50: 11:20, p95: 12:40}`。这样：

- p95 超出 `latest_finish` 的 offer 直接排除
- slack 按 p95 算，不按 p50 算
- 长回路里对照 p95 承诺 vs 实际，检验模型是不是系统性乐观

如果给人看（slides / 解释界面）需要一个标签，按**来源**分三档才有意义：`high`（这对站点有充分历史）/ `medium`（有历史但条件不同：时段、文件大小不匹配）/ `low`（冷启动，用保守常数）。这对应 provenance，不是拍脑袋的分数。

**7.** `binding`**：这个 quote 为什么不能更好**

它是 binding constraint（约束瓶颈）的简写，回答"是什么卡住了"。

- `when`：时间轴上哪一段卡住了——哪几个时隙容量不足。这是 counter-offer 的依据，也是解释"你为什么被推后两小时"的原始素材。
- `blocked_by`：这个障碍归谁。


| 值                 | 含义                                        | scheduler 能做什么                        |
| ----------------- | ----------------------------------------- | ------------------------------------- |
| `own_commitment`  | 被我们自己已做出的承诺占着                             | **可以动**——去查是哪个 workflow、比优先级，决定抢占还是让路 |
| `foreign_traffic` | 被我们控制不了的流量占着（别的机构、background HEP traffic） | **动不了**——别浪费时间试，直接考虑别的时段或别的路径         |


**为什么只需要两个值**：scheduler 自己就知道它做过哪些承诺，不需要 network agent 告诉它是"哪个"workflow 挡的。真正有信息量的区分只有一个——**这个障碍我能不能动**。

这一条把优先级仲裁从盲目试错变成有向搜索。而且 `feasible` 时 `binding` 同样有用：它说明"为什么不能更早、不能更快"，是 counter-offer 和人机解释的素材来源。

## 需要你定的一件事

`rate_profile` 是**常数速率**，还是**允许分段时变**？

- **常数**：一个 transfer = 一条 SENSE virtual circuit = 一个带宽值。干净、直接对应 primitive、实现最省事。
- **分段**：`[(t0,t1,40G), (t1,t2,10G), ...]`。要靠多条 circuit 或反复 `modify` 拼出来。

这不是实现细节——**它决定 demo 能不能展示统计复用**。KK 在 0907 明确批评 DMM"每个 flow 拿一次性固定分配、flow 之间不复用"，如果我们也用常数速率，我们做的就是同一件事，只是多了个 agent 壳。但分段会把 network agent 的复杂度抬高一档。

我倾向**先常数、但协议字段留成 list**：第一版 demo 只填一段，错峰靠"在时间轴上错开起始时间"来体现（这已经足够展示两个 workflow 都不误 deadline），而字段形状不用改就能升级到时变。

你怎么看？同意

## 上行之三：`transfer_outcome`（执行回写的网络部分）

只转 network 部分，但贴上 Network agent 自己拿不到的那个 id：

```jsonc
{
  "commitmentRef": "cmt-7f3a91",     // 这一跳存在的全部理由
  "fileId": "input.txt",
  "source": "aps-beamline-8id", "destination": "anl-n01",
  "startedAt": "…08:31:12Z",
  "durationSeconds": 1720.0, "bytesTransferred": 5.0e11,
  "path": ["APS-LCRC"],
  "rttMs": { "p50": 3.1, "p95": 4.4, "p99": 9.8 },
  "parallelStreams": 8, "protocol": "globus-gridftp",
  "concurrentTransfers": 2,
  "status": "completed"
}
```

Network agent 手上已有、不必传的另一半：`reservedRateGbps`、`predicted_finish{p50, p95}`、`circuit_id`、账本上占的时隙。**配对就发生在这里。**

> 若 WMS 愿意直接把 `commitmentRef` 回带并同时上报给 Network agent，这一跳可以省掉——代价是 WMS 要认识两个 agent、实现两套上报。现在不这么做，是为了保住分层和降低接入成本；将来若转发成为负担，这是现成的退路。

---



# Scheduling到Network Agent的通信协议：network agent 怎么答



### 先排除一个选项：无状态

"每次 quote 就现问 SENSE"行不通，四个理由：

1. SENSE 只有**点查询**——`total-block-maximum-bandwidth(start, end-before)`，一次一个窗口，没有曲线、没有批量接口。
2. 要回答"最早什么时候能开始"，得在时间轴上二分搜索，一次 quote 打几十个 SENSE 请求。
3. 0908 的 gate 要求 agent coordination **p50 < 200 ms**，网络往返几十次直接出局。
4. 最致命的：一个 bundle 里的 5 个 transfer 会**互相占用**同一段容量。逐个查 SENSE，每次查询都不知道同 bundle 里另外 4 个刚被安排掉了——错峰根本无从谈起，还会 overcommit。

所以 network agent 必须持有状态。我叫它 **capacity ledger（容量账本）**。

### 账本是两层，信任等级不同

```
observed 层  ← 来自 SENSE / digital twin：这条路"外界"还剩多少
             语义 = reservable，含非 SciNet 流量的影响
             性质：会过期、有误差、要主动刷新

own 层       ← 我们自己 hold / commit 出去的每一笔
             语义 = allocated，我们自己写的
             性质：精确、即时、无需查询

```

**可用量 = observed(t) − Σ own(t)**

这条减法必须**在本地做**，不能靠重新查 SENSE。原因：我们刚 commit 的预约，SENSE 的可用量视图可能还没反映出来；如果依赖它反映，我们就会把同一段容量卖两次。**KK 在 0907 点名要求保证的"并发调度总需求不超过 capacity"，就是靠这条减法保证的，不是靠 SENSE。**

这也顺带解决了那个悬置问题：**WfPlatform 的正确落点就是这里**——不是 workflow schema 的一部分，而是 network agent 的内部状态（你 0907 主张的"一致快照 + 历史"，正好对应 own 层 + 校准历史）。KK 没否决它，只是说 enhancement；现在它是被架构推出来的必需品，不是外挂。

### 一个必须诚实承认的不健全之处

SENSE 不暴露内部 node-link graph（你笔记里的 L1 缺口）。所以账本**只能按 (src, dst) 路径对建账，不能按 link 建账**。

后果：A→B 和 C→D 可能共用一条我们看不见的瓶颈链路。账本上两笔都算得开，实际会撞车。

这不是能修的 bug，是信息边界。处理方式三条，都已经在协议里有位置了：

- observed 层打 **safety margin**（初期保守常数，后期由历史校准）
- commit 前对 SENSE 做一次**核对**（两阶段的 propagate 天然是这个核对点）
- 撞了就靠运行时 `at_risk` **上行事件**兜底

**而这个"隐藏耦合"恰好可以做成实验变量**——digital twin 里我们知道真实拓扑，可以量化"账本盲区导致多少次误判"，这是把信息边界变成可测结论的机会。

### 三个待定参数（不急着现在定，但要留在 config 里）

- **horizon**：账本往未来看多远（跟 workflow deadline 的典型跨度挂钩）
- **时间分辨率**：见下
- **刷新策略**：observed 层多久、在哪些时间点重新采样——这就是你 0907 说的"用有限次点查询重建容量曲线"，它现在有了确切的家



## 需要你定的一件事

账本的**时间表示**：

- **离散时隙**（比如 5 分钟一格）：装箱变成干净的离散优化问题，MILP/贪心都好写，容易画进 demo。代价是量化误差——3 分钟的传输占满一格，deadline 卡在格子边界上会误判。
- **连续区间**（分段常值 + 区间树）：精确、无量化误差，但装箱和合并逻辑复杂一档。

我倾向**离散时隙，slot 大小进 config**。理由：第一版要的是"两个 workflow 错峰、都不误 deadline"这张图，时隙足够；而 slot 大小做成参数后，"时隙粒度 vs 调度质量"本身就是一个现成的、能跑的小实验。

你怎么看？暂定**离散时隙。**

---



# scheduling agent 拿到 offers 之后干什么

network agent 那半边定了。现在是对称的另一半——也是"agent 到底聪明在哪"真正落地的地方。

### 它有四个功能，其中一个是它独有的

1. **DAG → transfer 时间窗推导** ← 只有它能做，下面细说
2. bundle 组装 + 从 offers 里选
3. 跨 workflow 仲裁
4. 响应 `at_risk`，决定重排还是降级

第 1 条是整个 B 切法成立的理由。workflow 给的是 **task** 的 deadline，network agent 要的是 **transfer** 的时间窗，两者之间隔着一次关键路径推导：

```
前向：从 DAG 起点推每个 transfer 的 earliest_start（上游 task 何时产出数据）
后向：从 workflow deadline 倒推每个 transfer 的 latest_finish（下游 task 何时必须启动）
差值 = slack ← 这才是调度自由度的来源
```

```
[earliest_start, latest_finish]   ← 率无关的信封，scheduling agent 算
        └─ offer: (start, rate) ─┘  ← 率相关的放置，network agent 填
```

**slack 是这个 agent 全部价值的燃料。** 没有它，每个 transfer 都是"必须马上传"，错峰无从做起，counter-offer 也没得谈。KK 在 0907 说的"能否利用 deadline 内的 slack"，具体就是这一步算出来的东西。

> Q: 关于scheduling agent 拿到 offers 之后干什么，我理解能拿到一个slack值，作为调度的自由度。但是我有些模糊的是，从offres里选一个，到底是在优化啥？保证所有workflow都能完成吗，但是network agent本身返回的offer就已经保证了该offer能够完成？所以是要选一个offer能保证不影响别的workflow？同时还能保证系统能容纳的workflow最大？整体的完成时间最短？
>
> A: 核心一句：**offer 保证的是"你这条能完成"，没保证"选了之后别人还能完成"。选择优化的是机会成本，不是自身可行性。**
>
> **1. offer 的可行性是相对于当前账本的**
>
> network agent 给的每个 offer 单独看都成立，但选中任何一个都会**改变账本**——占掉那段时隙的容量。所以选择的真正后果在别处：它决定了后面的 transfer 还剩什么位置。
>
> 如果整批只有一个 workflow，选哪个 offer 几乎无所谓。**offer 选择的全部价值来自竞争。**
>
> **2. 早 vs 晚是一个真实的权衡**
>
>
> | 选早完成的 offer             | 选晚完成的 offer            |
> | ----------------------- | ---------------------- |
> | 留下大 slack → 故障时快回路有预算自修 | slack 用光 → 一出事就得升级到慢回路 |
> | 但占住了早期容量，可能挡死后面更紧急的     | 让出早期容量给别人              |
>
>
> 所以不是"越早越好"。slack 既是调度自由度，也是**抗故障的储备**——这两个用途在抢同一个额度。
>
> **3. 优化目标本身还没定**
>
> 你列的三个（都能完成 / 容纳最多 / 总完成时间最短）是三个**不同**的目标，会选出不同的 offer 组合。这正是我们上一步暴露、但还没定的那个问题——proposal 里 gate 1（completion time −25%）和 gate 3（fairness）互相打架，就是这个没定造成的。
>
> 我当时的倾向是：
>
> ```
> 硬约束：容量不超（correctness，非目标）
> 硬约束：每个 workflow ≥ 30% fair share
> 目标  ：最大化加权 deadline 满足（权重由 Tier 2.5 推导）
> ```
>
> 这样"能不能完成"由约束保证，offer 选择只在满足约束的解里挑权重最优的——三个目标不用打架。
>
> **一句话**：offer 是 network agent 给的**可行解集合**，scheduling agent 在这些解的**笛卡尔积**里挑一组，使得全局目标最优且约束不破。可行性归 network agent，取舍归 scheduling agent——这就是接缝 B 的分工在这一步的体现。



#### 目标：最大化加权Deadline满足的解释

**"deadline 满足"** = 这个 workflow 有没有在 deadline 前完成。**"加权"** = 不同 workflow 满足了值多少分——分数来自 Tier 2.5 推导的 utility，不是人填的 priority。

更准确的写法其实是：

```
最大化   Σ  utility_i(completion_time_i)
        i
```

"加权 deadline 满足"是它的粗糙版（把 utility 简化成一个阶跃）。真正用的是曲线。

##### 1. 为什么这比按 priority 排序强

举个 priority 会做错的例子：

```
W_A  训练任务       priority 高    deadline 18:00，缓慢衰减
W_B  Rubin alert   priority 低    10:00 断崖，过点归零
容量只够一个先跑
```


| 方案             | A 完成  | A utility | B 完成  | B utility   | 合计      |
| -------------- | ----- | --------- | ----- | ----------- | ------- |
| 按 priority，A 先 | 11:00 | 90        | 12:00 | **0**（错过断崖） | **90**  |
| 让 B 先          | 12:00 | 85        | 09:50 | 80          | **165** |


**让高优先级的 A 晚一小时，只损失 5 分；让 B 错过断崖，损失 80 分。**

按 priority 排序永远选不到第二个方案，因为 priority 是个静态次序，它不知道"晚一点各自亏多少"。utility 曲线让调度器能做**跨 workflow 的时间换取**——这就是目标函数存在的意义。

#### 2. utility是怎么被决定的，比如A的utility是85，B的utility是80，怎么理解？A的任务比B重要？从哪得到的？

这是整个设计里**最弱的一环**，值得讲清楚。"85"其实混了两个不同的东西：

- **形状 vs 高度**

**形状**（同一条曲线内部）：A 从 09:50 完成变成 12:00 完成，utility 从 90 掉到 85——这说的是"**A 自己晚一点亏多少**"。

**高度**（两条曲线之间）：A 的曲线整体在 90 这个水平，B 在 80——这说的是"**A 和 B 谁更重要**"。

**形状可以从 workflow 里读出来，高度不行。** 你的疑问正好命中了后者。

- **形状：有客观来源**

这部分 Tier 2.5 确实能推，因为它是事实：

- Rubin alert pipeline：观测窗口 10:00 关闭 → **断崖位置是客观的**
- 训练任务：gate 要求 WAN overhead ≤ 15% → 超过就作废，也是断崖，只是位置不同
- 下游有 512 张 GPU 在等 → 每晚一分钟就是 512 卡·分钟的空转，**可以真的算出来**

这些写在 workflow 描述、gate 定义、或领域惯例里，是可核对的。

- **高度：目前没有客观来源**

跨机构、跨学科比较"Rubin 的一次告警"和"一次分布式训练"哪个更值钱——**这个问题没有技术答案**。可能的代理都不干净：消耗的 GPU-hour / beam time、机构配额、人工标定一次再类推。

- **所以我建议改一处：用相对损失，不用绝对分数**

把每条 utility 曲线按**它自己的最大值归一化**到 [0,1]，比较的是各自损失了自己的百分之多少：


|            | 绝对分数（需要共同尺子） | 相对损失（不需要）   |
| ---------- | ------------ | ----------- |
| A 晚到 12:00 | 90 → 85      | 损失 **5%**   |
| B 错过断崖     | 80 → 0       | 损失 **100%** |


结论完全一样（让 B 先），但**不需要断言 A 和 B 的绝对价值可比**——只需要"让一个 workflow 损失 100% 去换另一个损失 5%，是坏交易"。这个判断本身就是 max-min fairness 的思路，和 0908 里 KK 建议的方向一致。

`priority` 作为一个乘数加在上面，负责"谁的百分之一更值钱"这一层——它本来就是干这个的，而且不需要精确，只需要分层。

**分工变成**：utility 曲线管**时间维度**（什么时候亏、亏多快），priority 管**跨 workflow 分层**（谁的损失更要紧）。两者正交，各自解决自己擅长的部分。这也回答了你早先那个问题——不是 utility 取代 priority，是它补上 priority 表达不了的那一维。

- **最后一条：它是可审的假设，不是黑箱**

不管怎么定，utility 曲线是个**小的、人能一眼看懂的结构化对象**。可以打印出来给科学家确认"你的 workflow 是不是这样"，也可以做消融（LLM 推导 vs 手调 vs 全部均匀），用实验证明它到底有没有用。

**这一点比数字本身重要**：我们不需要 utility 是"正确"的，只需要它是**显式的、可检验的、可修改的**——而现状（人人填 priority=1）三样都不是。

### Phase 1 是批量调度，不是在线到达

这条不用我们定，0908 已经定了：*"Phase 1 主要处理一组预先给定、需要共同调度和管理的 workflow；随着新 workflow 持续到达而不断自适应，可以作为 Phase 2 扩展。"*

这个约束帮了大忙——批量意味着可以全局规划，跨 workflow 仲裁才有意义。在线到达式只能"先到先得 + 抢占"，做不出好看的对照实验。

### 一个 B 切法自带的张力，必须现在处理

scheduler 要做仲裁，就要反复试："如果把 A 推后两小时，B 能不能进来？"**但每次试放都是一次跨 agent 往返。** 搜索空间一大，p50 < 200 ms 就没了。

三种解法，我选第三种：


| 解法                      | 问题              |
| ----------------------- | --------------- |
| scheduler 自己也建一份网络模型来搜索 | 账本重复两份，B 切法作废   |
| 把搜索整个挪进 network agent   | 仲裁权跟着过去，B 切法也作废 |
| **一次往返带回足够多信息，搜索在本地做**  | ✓               |


这正是 `offers` 设计成**复数**的真正原因——它返回的不是一个答案，是那个 transfer 的**可行前沿**（最早能到 / 降速能到 / 推后能到）。scheduler 在这些前沿点上做本地组合搜索，不需要网络模型，也不需要反复问。

跨 bundle 的试探则用 `hold` **+ TTL 当搜索原语**：先把 A 的方案 hold 住，quote B，若组合更优就 release A 重放。TTL 保证试探失败不会留下垃圾预留。

**v1 就做优先级序贪心、不回溯**——按某个键排序，逐个 workflow 放进去，放不下就取 counter-offer 或拒绝。够跑出 demo，且升级到回溯/MILP 时协议不用改。

### 顺手解决 0908 留下的一个坑

KK 在 0908 质疑：把 Jain's index 套在完成时间上是误用，而 proposal 里 **fair share 的分母根本没定义**。

我们的架构自带一个干净的分母：**账本上分给每个 workflow 的 slot·bandwidth 面积**。这是真正的"并发共享资源份额"，不是完成时间的代理指标，而且能直接区分 KK 举的那个反例——A 独占完再 B 独占，两者面积可能相同，但**时间轴上不重叠**，一眼可查。

这可以作为我们对那个待办的实质回答，不只是"我们也觉得该重新定义"。

## 需要你定的一件事（这条会直接变成给 Rafael 的具体要求）

**transfer 的时间窗，是 scheduling agent 推导出来的，还是 workflow 直接声明的？**

- **推导**：workflow 只给 DAG + workflow 级 deadline，我们做前后向推导。**但这要求每个 task 带一个 compute runtime 估计**——没有它，后向推导无从下手。
- **声明**：workflow 直接给每个 transfer 一个 deadline，省事。但你 0907 笔记里那句话我认为是对的：*"只给一堆扁平的 transfer deadline 会丢掉可调度性信息。"* 声明进来的 deadline 是别人已经拍好的，slack 被提前吃掉了，我们看不见还能挪多少。

我倾向**推导**，并且这恰好把 0908 那条"请 Rafael 核对 workflow API 扩展"的行动项变成一个**有架构论证的具体请求**：不是"我们想多要几个字段"，而是——

> 没有 task runtime 估计 → 后向推导不成立 → transfer 时间窗无法导出 → slack 无法计算 → 整个时间维度是假的，agent 退化成一个 SENSE 转发器。

这个论证链条比列字段清单有说服力得多，也正好答了 KK 在 0907 §7 排的第三步"确定 agent 需要哪些输入信息"。

你倾向哪个？暂不确定。

---



# LLM 到底放在哪

这是 0907 §7 的第二步（"逐项判定每个功能该由 AI 做、还是规则式算法"），也是 0908 里 Mariam 那条 harness 调研的落点。两个 agent 的模块都列出来了，可以正面回答。

先把"AI vs 规则"这个二分法换掉——它不够用。**按工作性质分四类，这不是层次，是四种不同的活。**


| 这类工作     | 具体是什么                                | 用 LLM？            |
| -------- | ------------------------------------ | ----------------- |
| **算数字**  | 关键路径推导、账本减法、quote 求解、容量核算            | **绝不**            |
| **构造问题** | utility 曲线、缺失参数推断、约束形式化              | **是**，杠杆最大        |
| **对人说话** | 入口归一化、缺失信息追问、解释与协商                   | **是**             |
| **做取舍**  | 刷新策略、probe planner、`at_risk` 响应、搜索停止 | **v1 不用**，做成可替换接口 |


---



## 一、算数字：绝不给 LLM


|          | 做什么                                                   | 精确算法                                                                                                         | 复杂度              |
| -------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------- |
| 关键路径推导   | DAG 上算每个 transfer 的 `[earliest_start, latest_finish]` | 拓扑排序 + 两次线性扫描（CPM/PERT）：前向 `earliest(v)=max(finish(前驱))`，后向 `latest(v)=min(latest_start(后继))`                | O(V+E)           |
| 账本减法     | `可用(t) = observed(t) − Σ own(t)`，逐时隙                  | 数组减法；区间更新用差分数组                                                                                               | O(时隙数)，更新 O(1)   |
| quote 求解 | 在账本上为 bundle 找可行放置                                    | 单条恒定速率：对每个候选起始时隙，速率上界 = 该跨度内 `min(可用(t))`，跨度又依赖速率 → 在 (start, rate) 上一维扫描 + 二分。bundle 内多条：v1 贪心（按 slack 升序放） | O(时隙数 × log)     |
| 容量核算     | 验证放置方案每个时隙都不超容                                        | 逐时隙求和比较                                                                                                      | O(时隙 × transfer) |


理由不是"LLM 算不准"，是**代价不对称**：这些都有精确算法，毫秒级、可复现；LLM 做只会更慢更贵，而一旦算错，后果是 demo 里出现 overcommit——**正是 KK 在 0907 点名要求保证的那条底线**。

---



## 二、构造问题：LLM 杠杆最大的地方

求解器需要一个目标函数。**但目标函数从哪来？**

0908 那一整段已经暴露了答案：这个团队连 fairness 都定义不出来，KK 直接质疑 proposal 里 fair share 的分母是什么。这不是个别疏忽——**真实调度系统失败，很少是因为求解器不好，绝大多数是因为没人写得出目标函数。**

"这个 workflow 晚 10 分钟和晚 2 小时，损失是不是一样的"是个**语义问题**：Rubin 的 alert pipeline 晚了，下游 GPU 空转、科学价值陡降；分布式训练晚一点无所谓，但 WAN overhead 超过 15% 就废了。这些知识写在 workflow 描述里、写在领域惯例里，不在任何数据表里。

### utility 曲线怎么推

**输出形状**：分段线性，几个控制点，归一化到 [0,1]。

```
Rubin alert:  [(now, 1.0), (10:00, 1.0), (10:00+ε, 0)]                平台 + 断崖
训练任务:      [(now, 1.0), (12:00, 1.0), (18:00, 0.3), (24:00, 0.1)]   缓降
```

**LLM 读什么**：workflow 描述的自然语言、`constraints` 字段（如 `periodicDeadline`）、gate/SLA 里的硬指标（WAN overhead ≤ 15%）、下游资源规模（多少 GPU 在等）、领域惯例。

**四步推导**（可以直接写成 prompt 的结构）：

1. **找断崖**——有没有一个时刻之后价值归零？观测窗口关闭、下一批数据覆盖当前批、gate 阈值被突破
2. **找衰减段**——断崖之前晚一点亏什么？尽量量化（512 卡空转 N 分钟）
3. **找无损段**——更早完成没有额外价值的区间（多数 workflow 都有）
4. **归一化**到 [0,1]



### 形状可以推，高度不能

"85 vs 80"其实混了两个东西：**形状**（同一条曲线内部，晚一点亏多少）和**高度**（两条曲线之间，谁更重要）。

形状有客观来源——观测窗口何时关闭、gate 阈值在哪、多少 GPU 在等，都是可核对的事实。**高度没有**：跨机构比较"一次 Rubin 告警"和"一次分布式训练"哪个更值钱，没有技术答案。

**所以用相对损失，不用绝对分数**：每条曲线按自己的最大值归一化，比较各自损失了百分之多少。


|            | 绝对分数（需要共同尺子） | 相对损失（不需要）   |
| ---------- | ------------ | ----------- |
| A 晚到 12:00 | 90 → 85      | 损失 **5%**   |
| B 错过断崖     | 80 → 0       | 损失 **100%** |


结论一样（让 B 先），但不需要断言 A 和 B 的绝对价值可比——只需要"让一个 workflow 损失 100% 去换另一个损失 5% 是坏交易"。这和 0908 里 KK 建议的 max-min fairness 方向一致。

`priority` 作为乘数加在上面，负责"谁的百分之一更值钱"这一层。**分工是：utility 曲线管时间维度，priority 管跨 workflow 分层**，两者正交。

### 这一类里的另外两项

- **缺失参数推断**：task runtime、数据量估计、弹性——从 workflow 结构 + 历史类比推出来，填进 `WfCampaign.estimates`。没有它，后向推导不成立，整个时间维度是假的
- **约束形式化**：把"deadline 是 hard 还是 soft"变成可求解的形式

**共同特征**：LLM 的输出是一个**小的、人类可审的结构化对象**，然后被确定性组件消费。既有杠杆，又没破坏 guardrail——因为审计点是那个中间对象。而且可做消融（LLM 推导 vs 手调 vs 均匀），是个干净的实验。

## 三、对人说话：LLM 真正不可替代

- **入口归一化**：Pegasus DAX / CWL / Snakemake / 一个 Slurm 脚本 / 一封邮件里的一段话 → 结构化 IR。**这不是文书工作**——从这些东西里构造出良定义的调度实例，是大多数真实系统死掉的地方
- **缺失信息的追问**："你没给 task runtime，我按 X 假设，对吗"
- **解释与协商**：为什么被推后两小时、counter-offer 在权衡什么

这三处没有精确算法，因为问题本身没有良定义的输入。**这是 DOE 多机构环境里最有实际价值的一块**——科学家要的不是一个调度结果，是一个能问"为什么"的系统。

补一条：**协商是决策过程，不是输出格式**。agent 之间不走自然语言这条我坚持，但人机之间不同——科学家的偏好是在来回中被揭示的，不是一次性声明的。

## 四、做取舍：先用规则，做成可替换接口


|                   | 决策什么                                           | v1 规则                                                                | 可调参数   |
| ----------------- | ---------------------------------------------- | -------------------------------------------------------------------- | ------ |
| **刷新策略**          | 何时重查 SENSE，更新 observed 层的**容量曲线**              | 固定周期（如 5 min）刷新 horizon 内时隙，**近期密、远期疏**；外加事件触发（commit 前、`at_risk` 后） | 周期、密疏比 |
| **probe planner** | 何时花代价主动测量**实际吞吐 / RTT / 丢包**（iperf、rapid-ping） | 只在两种情况探测：①该站点对无历史（冷启动）②上次 achievable 偏差超阈值。加每小时次数上限                  | 阈值、预算  |
| **at_risk 响应**    | 收到升级后 scheduling agent 怎么办                     | 固定降级阶梯：吃自己的 slack 推后 → 降速 → 抢占更低优先级 → 都不行则通知人并给 counter-offer        | 各级阈值   |
| **搜索停止**          | 组合搜索什么时候收手                                     | 三个上限任一触发即停：试探轮次、时间预算（对上 p50 < 200 ms）、连续 N 轮无改进                      | 三个上限值  |


共同结构是**在信息成本、收益和不确定性之间做判断**——不是算数，也不是解释。这才是"agent"一词在本项目唯一有技术含量的落点。

**但不要一上来就往这里塞 LLM。** 正确顺序是把每个 meta-decision 点显式抽成**同签名的 policy 接口**，v1 全部填规则式实现，系统先跑通。然后才有资格问"这个位置换成 LLM 比规则好吗"，而且**能量化地回答**，因为接口两侧的输入输出都固定。

这个叙事比"我们用了 LLM 所以是 agentic"强得多，也正好接住 0908 §三 那条原则：*"不应把某一个 AI 给出的建议当作最终选择，应系统化提问、比较多个模型，并用人工判断核验。"*

## **probe planner 探什么**

探账本里**查不到**的东西。SENSE 只给 `reservable`（模型量），给不了 `measured`（实测量）——这个缺口只能靠主动测量填：


| 探什么           | 工具                 | 用来干什么                                                 |
| ------------- | ------------------ | ----------------------------------------------------- |
| 实际吞吐          | `iperf`            | 校准 achievability model 的 `reservable → achievable` 比例 |
| RTT / 丢包 / 抖动 | `rapid-ping`、owamp | ①判断差距在网络侧还是端系统侧 ②RTT 本身就是 achievability 的输入变量         |
| 实际路径          | `traceroute`       | SENSE 读不回完整有序 route（0904 §5.2.2），只能自己看                |


工具就是你 0904 调研里 SiteRM Debug API 的那几个。

**为什么是个决策而不是常开**：探测有真实代价——`iperf` 会**真的打流占带宽**，可能干扰正在跑的传输；跨站点还需要授权；结果也不是立刻返回。所以"花一次探测去消除多少不确定性"值不值，本身就是个判断题。

**v1 规则里那两个触发条件的含义**：冷启动（该站点对没历史，模型只能用保守常数 0.6×，探一次能立刻收紧）；偏差超阈（上次实测偏离预测太多，需要判断是一次性抖动还是系统性变化）。

## **搜索在搜什么**

搜的是**放置组合**，两层：

**bundle 内**：每个 transfer 拿回 k 个 offer，n 个 transfer 就是 k^n 种组合。要挑一组使目标最优、且每个时隙都不超容。

**跨 workflow**：workflow 之间的放置顺序，以及要不要**回头重放**已经放好的——"把 A 推后两小时，B 能不能进来"。这一层用 speculative `hold` / `release` 试探，**每一轮试探都是一次跨 agent 往返**，有实打实的时间代价。

v1 是贪心不回溯，空间很小，几乎不会撞到上限；但一旦允许回溯（规模上来或 Phase 2），组合就爆炸了，必须有停止规则。

**"停止"停的不是"算出正确答案"，而是"再搜下去不划算"**：

- **时间预算**——p50 < 200 ms 是硬约束，超了就交当前最好解
- **边际收益**——连续 N 轮目标函数没改进，说明陷在局部最优
- **轮次上限**——兜底



## harness 三条

0908 说 harness = 限定 agent 的工具、行为范围与 guardrails，但当时还是个待调研方向。我们的架构可以直接给出三条具体的：

1. **LLM 永远不能直接写账本，也不能直接产出数字承诺。** 只能通过 policy 接口和归一化/解释接口作用于系统——"算数字"那一类就是 guardrail 的边界定义。
2. **解释是渲染，不是推理。** 生成解释时只允许读 Commitment Ledger 和 `binding`，不允许重新推导数字。否则会出现"解释听起来合理、但和实际决策不一致"——最难被发现、也最伤信任的一类失败。
3. **两个 agent 之间只走类型化协议，不走自然语言。**

第 3 条直接消灭了 0908 警告的那类风险（*"多 agent 之间的交互即使单个 agent 看似正常，也可能产生系统级错误"*）：

> **自然语言只出现在系统边界（对人），不出现在系统内部（agent 之间）。**

这也能给 Mariam 一个现在就能对接的东西，不必等她的框架调研出结果。

## 已定：11 月 demo 带 LLM，但只在两端

0908 建议的最小 demo 是纯确定性的。**决议是加上"对人说话"那一类的两端**（入口归一化 + 解释输出），"做取舍"那一类全用规则。

理由：增量成本很小（两个 LLM 调用点，不碰核心逻辑），但 demo 立刻有了"能问为什么"的交互面，而且**演示的恰恰是 guardrail 本身**——LLM 在两端，数字在中间，边界清晰可讲。

叙事也强一档：不是"LLM 帮你解释调度结果"，而是"**LLM 读懂了两个科学 workflow 各自在乎什么，据此排出了一个人工权重排不出的调度**"。

## FAQ：为什么 priority 不够，非要 utility 曲线

**1. priority 是标量，utility 是曲线——信息量不是一个量级**

两个 workflow 都填 priority=3。一个是 Rubin alert pipeline，deadline 前无所谓、过线**断崖**；另一个是训练任务，晚多久都能用，只是慢慢贬值。标量表达不出这个差别，调度器只能一视同仁。

**priority 回答"谁先"，utility 回答"晚多久开始亏、亏多快"**——后者才是做权衡需要的：让 A 晚 5 分钟换 B 早 1 小时，值不值？只有 priority 时这个问题无法计算。

举个 priority 一定会做错的例子：

```
W_A  训练任务       priority 高    deadline 18:00，缓慢衰减
W_B  Rubin alert   priority 低    10:00 断崖，过点归零
容量只够一个先跑
```


| 方案             | A 完成  | A 损失 | B 完成  | B 损失           | 结果    |
| -------------- | ----- | ---- | ----- | -------------- | ----- |
| 按 priority，A 先 | 11:00 | 5%   | 12:00 | **100%**（错过断崖） | 差     |
| 让 B 先          | 12:00 | 10%  | 09:50 | 3%             | **好** |


按 priority 排序永远选不到第二个方案，因为静态次序不知道"晚一点各自亏多少"。

**2. schema 里已经有 priority 了**

`WfCampaign.submissions[].sla.priority` 就在那儿。所以"设置好不就行了"= 现状。而 KK 在 0907 批评 DMM 的原话正是：*"能给每个 flow 指定 priority，据此在 flow 之间分配容量"*，并判定这**不构成本项目要解决的问题**。如果我们的答案也是 priority，我们做的就是 DMM 加一个 agent 外壳。

**3. priority 是自我声明，utility 是可检验的事实**

谁填 priority？提交者自己。结果所有人都填最高——排队系统众所周知的失效模式，因为声明重要性没有代价。

而 utility 曲线不是"我有多重要"，是"**我的科学产出如何随时间衰减**"：下游 GPU 会不会空转、观测窗口什么时候关、超过 15% WAN overhead 训练是不是就作废。这些是关于 workflow **本身的事实**，可核对、难虚报。

**所以 LLM 的角色不是替人决定优先级**，而是把已经写在 workflow 描述和领域惯例里的语义，翻译成求解器能算的形状。人填的是偏好，LLM 推的是后果——后者才是我们比 DMM 多出来的那一点。

---



# 承诺怎么执行、坏了怎么办

`at_risk` 在协议里声明了但没设计。展开它的时候会先撞上一个我们一直隐含着的错误假设。

### 那个错误假设：一个 transfer = 一条 circuit

不成立。0908 §七 明确说：**SENSE 建 L2 overlay 很慢，所以 overlay 通常长期保留，快速恢复发生在 L3（flow redirection）。**

如果建一条电路要几分钟，那么一个 workflow 在同一对站点之间的 5 次传输绝不该建 5 条电路。**30 秒恢复目标也直接排除了"故障后重建电路"这条路。**

所以要加一层间接：

```
commitment（逻辑承诺，对 scheduler 说的话）
        ↓  多对一
circuit（物理电路，对 SENSE 说的话）
```

**commitment = 一趟班次，circuit = 一条包下来的专用车道。** 开辟车道要几分钟，排班次是瞬间的事。

### 一条 circuit 上跑多个 commitment

```
circuit C1：ANL→ORNL，100 Gbps，09:00 建立，18:00 拆除
            └── 这是对 SENSE 说的：provision 一条物理电路

  09:00         10:30        12:00        14:00        18:00
  │─commitment A─│──空闲──│─commitment B─│─commitment C─│
      WF-1 的传输              WF-2 的传输     WF-1 的另一条
      └────────── 这些是对 Scheduling 说的：我承诺你的数据几点到 ──────────┘

```

三个 commitment 可能来自不同 workflow，但**只 provision 了一次电路**。这就是"多对一"。

**生命周期也不同**：circuit 活得比任何单个 commitment 都长——建一次，反复用，空闲超时才拆。本质是连接池。

### 为什么必须这么做

如果一个 transfer 就建一条电路：

- 一个 workflow 在 ANL↔ORNL 之间有 5 次传输 → 5 次电路建立 → 每次几分钟，全浪费在等 provisioning 上
- **30 秒恢复目标直接死掉**——故障后重建电路根本来不及
- `quote → commit` 的响应时间也不可能落进 p50 < 200 ms

有了电路池：commit 一个 commitment 多数时候只是在账本上占个位 + 复用一条已经开着的电路，快；故障时也是在**已有电路内部**改速率或改路径（L3 flow redirection），不碰 L2 overlay。这正对上 0908 说的"L2 overlay 慢所以长期保留，快速恢复发生在 L3"。

### 代价：空闲时那 100 Gbps 还占着

图里 10:30–12:00 那段空闲，电路预约的容量仍然锁着，别人用不了。

**这正是 KK 批评 DMM 的那件事**——固定分配、flow 之间不复用。所以**统计复用的入口就在这一层**：让保温电路的闲置容量能被别的 commitment 借用。第一版不做，但架构上必须留位置，否则 Phase 2 接不上。

### 对账本的影响

账本要记两套东西，两条时间轴：

- **commitment 层**：谁承诺了什么、什么时候、多少带宽 ← 对 scheduling agent 负责
- **circuit 层**：哪些电路开着、剩多少余量、什么时候拆 ← 对 SENSE 负责



### 其他

**两者生命周期分离**：电路按需懒创建、用完保温、空闲超时才拆。本质是连接池。commit 一个 commitment 不等于建一条电路——可能只是往一条已在保温的电路上排一段时间。

这一层解释了三件事：

- **30 秒恢复变得可信**：不重建电路，只在已有电路内部改路径或改速率
- 电路建立延迟被摊薄，quote→commit 的响应时间才可能落进 p50 < 200 ms
- ledger 要分别记 commitment 和 circuit，两套时间轴

**代价要说清楚**：保温的电路空占着预约带宽。这恰好就是 KK 批评 DMM 的那件事——固定分配、flow 之间不复用。所以**统计复用的入口就在这一层**：让保温电路的闲置容量能被别的 commitment 借用。第一版不做，但架构上要给它留位置，否则 Phase 2 没法接。

### 失败闭环：两条路径，判据是 slack

```
偏差被检测到
   ├─ 还赶得上 latest_finish  → 快路径：network agent 自己修，事后通知
   └─ 赶不上了               → 慢路径：发 at_risk，scheduler 重新仲裁

```

判据现成：scheduler 给的窗口是 `[earliest_start, latest_finish]`，而 network agent 承诺的是一个更早的 `predicted_finish`。**两者之间的差就是本地自修预算。** 协议不用改——我们之前设计的字段刚好带着做这个决策所需的全部信息。

快路径必须存在，否则每个抖动都惊动 scheduler，30 秒预算全花在协商上。

### 协议要补一个事件

之前只定义了 `at_risk`，不够。network agent 自主修复后必须**上报**，否则 scheduler 手上那份"我承诺了什么"的账会和现实脱节：

- `repaired` — 通报，承诺仍成立，无需决策
- `at_risk` — 升级，承诺保不住，等你决定

两者语义完全不同，混成一个会让 scheduler 分不清"要不要动"。

### 5 秒那个 gate 需要诚实拆开

0908 已经把它列为待核对项，我认为拆法是这样：


|                | 性质         | 5 秒可行吗                   |
| -------------- | ---------- | ------------------------ |
| 链路失效 / 电路 DOWN | 事件，有明确信号   | 可行                       |
| 吞吐退化 30%       | 统计量，需要观测窗口 | **不可行**——5 秒内无法把退化和抖动区分开 |


所以 5 秒只能承诺前者。后者的检测延迟由采样率和判定阈值决定，是可调的，而且 **"检测延迟 vs 误报率"本身就是一条可测曲线**——比含糊承诺"5 秒检测一切"体面得多，也正好是 0908 要向 SENSE 团队核对的那个问题的我方版本。

## 需要你定的一件事

**digital twin 的 telemetry，要不要故意做得和真实 SENSE 一样贫瘠？**

检测需要观测量，但我们能拿到什么是有疑问的：传输进度归 Rucio/FTS 管，不在我们手里；SENSE 侧的实时测量按你 0904 的调研基本是空白（L3 那层）。Phase 1 跑在 digital twin 上，twin 里我们想给什么观测量都行——这正是危险的地方。

- **给全**：检测做得又快又准，但那是因为我们给自己开了后门，结论迁移不到真实系统。
- **按真实 SENSE 的能力边界裁剪**：结果诚实，而且**你 0907 笔记里那个实验立刻变得可做**——逐项拿掉 telemetry，看性能退化多少。你当时说这是"最漂亮的一个实验"，我同意，但它成立的前提就是 twin 必须先能表达"信息缺失"这件事。

我倾向后者：twin 默认按 SENSE 实际能力供给观测量，把"额外 telemetry"做成可开关的实验变量。这样 baseline 和 agent 跑在同一信息条件下，对照才有意义。

这条也直接回应 [CLAUDE.md](http://CLAUDE.md) 里那句"现阶段首要任务是把'要解决什么问题'收敛成一个可测的假设"——这就是那个假设的载体。

你怎么看？暂不定。

---



# 北向接口：谁在调 scheduling agent

先说一个和南向的根本差别：南向的对话方（network agent）是我们自己写的，可以随便定协议。**北向的对话方是别人的、已经存在的、而且不止一个**（Pegasus、Rafael 那套 API、可能还有别的）。所以北向不是对称地再定一份协议，而是要在"我们需要什么"和"人家肯给什么"之间找落点。

### 核心张力：谁控制执行时序

两种模式，差别是根本性的：

**模式 A（咨询式）**：workflow 系统要传数据了，来问一句"这个能传吗、什么时候"，agent 回答。不侵入、好接入。

**但模式 A 会让我们前面的设计全部作废。** agent 每次只看得见眼前这一个 transfer，看不见 DAG、算不出 slack、更谈不上跨 workflow 错峰——**它就退化成我们上一步定的 B1 baseline 了**。这一点值得记住：接入门槛最低的方案，恰好是把我们的贡献消掉的方案。

**模式 B（托管式）**：整个 workflow 交给 agent，agent 规划所有传输时序。拿到全局视图，前面的设计才成立。但它要求 workflow 系统交出执行控制权——Pegasus 这类成熟系统不会轻易听我们的。

**我主张 B'（规划-协商式）：拿视图，不夺权。**

workflow 系统提交完整 workflow → agent 返回一份**执行计划**（建议）→ workflow 系统可接受、可拒绝、可部分接受 → 执行仍由 workflow 系统自己走，但每完成一步**回报**。

agent 得到了全局视图，workflow 系统保住了主权，接入阻力小得多。代价是计划可能不被遵守——所以回报闭环是必需的，不是可选的。

### 三个动词

```
submit(workflow)                     DAG + deadline + priority，返回执行计划
refine(workflow_id, task_id, 实测值)  运行时把估计换成事实，触发增量重规划
report(task_id, 实际起止时间)          执行回报，喂给偏差检测与 achievability 校准

```

`refine` 存在的理由：真实 workflow 是**渐进展开**的——DAG 下半部分的数据量往往要等上半部分跑完才知道。没有 refine，agent 拿着一堆过期估计做规划。

**顺带一提：**`refine` **只有在"推导"模式下才有意义。** 如果 workflow 直接声明每个 transfer 的 deadline，那些 deadline 是别人拍好的，refine 无处作用。这是支持"推导"的一个新论据——不是要现在定，但可以记进搁置项。

### 响应分两路

南向的 offers 是给机器消费的。北向的接收方可能是**人**：

- **结构化执行计划** → workflow 系统
- **自然语言说明与协商** → 科学家

后者正是 Tier 2 的落点，也是 11 月 demo 里"能问为什么"的那个交互面。同一个决策，两种渲染。

### 归一化做成 adapter

Pegasus DAX / CWL / Snakemake / Rafael 的 API，**每种一个 adapter，内部 IR 只有一份**。Rafael 那边接口变了只动 adapter，agent 核心不动。这也是 Tier 2 那个"入口归一化"的工程形态——LLM 辅助的 adapter，不是硬编码 parser。

（另有一条通道值得记下但归 Phase 2：APS 这类光源设施的 beamtime 是**提前排好的**，属于"未来已知的需求"。它不是 workflow 提交，是预告。对 proactive admission 价值很大。）

## 需要你定的一件事

**计算侧的时间信息，我们要到什么程度？**

我们的 DAG 推导是从 task 依赖推出 transfer 的 `earliest_start`——意思是"上游 task 产出数据的时刻"。但 task 什么时候真的开始跑，取决于**计算资源排队**，那不归我们管。上游 task 在 GPU 队列里等了两小时，我们算的 `earliest_start` 就全错了，基于它做的传输预约白占容量。

**网络调度的正确性依赖计算侧的时间，但计算调度不归我们。** 三种态度：

1. **假设计算随时可用**——只调度网络。最省事，但和现实脱节，demo 一接真实系统就崩
2. **要 workflow 系统提供 task 的预计启动/完成时间**，当作输入 ← 我倾向这个
3. **联合调度计算与网络**——越界了，而且 0908 明确说本组不做底层网络工程，同理也不该去做计算调度。Phase 2 方向

选 2 的话，这就是**要向 Rafael 要的第二样东西**（第一样是 task runtime 估计）。两样合起来构成一个完整的请求，逻辑链条也清楚：

> 没有 task 的预计启动时间 → transfer 的 earliest_start 是猜的 → 预约的时间窗对不准 → 要么白占容量、要么错过数据就绪时刻。

这比列字段清单更容易说服人，也让"agent 需要哪些输入"这个 KK 排的第三步真正答完。

---



# 执行计划：Scheduling agent 交回 WMS 的东西

北向那三个动词里，`submit` 的**返回值**一直没定义清楚。它就是执行计划，而这份计划的内容决定了 control plane 和 data plane 能不能对上。

## WMS 是数据传输的发起方，不是 SENSE 的调用方

先把两个平面分清：

```
control plane：Network agent ──ServiceIntent──▶ SENSE-O      预约电路
data plane：   WMS ──Globus / GridFTP / Rucio──▶ 实际搬字节
```

在我们的架构里**只有 network agent 碰 SENSE**（分工的第二条后果）。WMS 干的是另一件事：按计划触发实际传输。顺序是 network agent 先把电路预约好，WMS 在那个时间窗里发起传输，传输跑在已预约的电路上。

## 为什么 submit 必须返回一份计划

Scheduling agent 算出的是"哪个 transfer 在哪个时段传"，而 transfer 的 `earliest_start` 是从**上游 task 何时产出数据**推出来的。如果 WMS 自己想什么时候起 task 就什么时候起：

- task 起晚了 → 电路按计划开了，数据还没产出 → **预约的容量空占，别人也用不了**
- task 起早了 → 数据就绪，电路还没到时段 → 白等

不返回计划，我们就只能被动等 WMS 说"我现在要传了"——那就是模式 A，只看得见眼前一个 transfer，看不见 DAG，算不出 slack，跨 workflow 错峰做不了，**整个设计退化成 B1 baseline**。

## 执行计划有三样内容

```
ExecutionPlan:
  taskSchedule[]:                        建议
    { task_id, suggested_start }

  transferWindows[]:                     已预约的事实
    { transfer_id, start, rate_profile, predicted_finish, confidence }

  endpointBindings[]:                    ← 之前漏掉的一样
    { transfer_id, src_uri, dst_uri, vlan, interface, protocol_hint }
```

**第三样是新补的，而且不可省。**

WMS 发起一次 Globus 传输，凭什么它就走在我们预约的那条 SENSE 电路上？SENSE provision 出来的是带特定 VLAN / IP / network attachment point 的路径——**传输必须在那些具体端点之间发起才会落到电路上**，否则数据照样走默认路由，我们的预约白做。

这正是 Rucio–SENSE 那篇论文里 **DMM 干的事**：把 flow 绑定到 SENSE 预约上。0908 的行动项说"重读 DMM paper，决定是否作为 network agent 的底层组件"——现在知道它具体补的是哪一块了。

**对南向协议的影响**：`commit` 目前只返回 `commitment_ids`，不够。它必须同时返回该 commitment 对应的端点绑定信息，才能装进执行计划交给 WMS。

## 计划是协商，不是命令

计算调度不归我们管（GPU 排队、资源分配都在别处），所以这份计划是**不对称**的：


| 部分                 | 性质     | WMS 能不能不听               |
| ------------------ | ------ | ----------------------- |
| `taskSchedule`     | 建议     | 能——它可以说"我做不到"，agent 重规划 |
| `transferWindows`  | 已预约的事实 | 不听就是浪费自己的预约             |
| `endpointBindings` | 技术必需   | 不听传输就不落在电路上             |


这也是它画成双向链路而不是单向箭头的原因。0908 明确说本组不做底层网络工程，同理也不该去夺计算调度的权。

## 第三个作用：它是对照基准

这份计划是后面 `report` 回来对照的基准——承诺了什么、实际发生了什么、差在哪。它是 Commitment Ledger 在 workflow 侧的对应物，也是长回路校准的输入。

---



# 执行回写：格式与用法【总】

> 回顾：执行回写分成两条： 
>
> 1. wms->scheduling agent，包括task readyAt / startedAt / runtime、文件落点（task部分信息），以及实际传了多少字节、用了多久、几条并行流（网络部分信息）。其中网络部分信息还得从scheduling agent流向network agent（用于学reserved和achieved）。 2. sense-o/twins -> network agent，包括链路状态、利用率、丢包、路径。这是network agent主动拉的。
>
> 目前，我们缺少execution write-back的格式。包括从WMS到scheduling agent的task和network两部分内容，以及从scheduling agent到network agent的network部分内容，以及从sense-o到network agent的内容。 以及需要说明： 1. scheduling agent是怎么使用task和network两部分内容的 2. network是怎么使用network内容（from WMS）以及来自于sense-o的内容的。

执行计划是下行的，这一节是它对称的另一半：事实怎么回来、谁用、怎么用。

**一条原则先立住**：`report` 不新造 schema，它就是 `WfFormat.execution` 的一个增量切片。WMS 本来就在写 execution 记录，我们要的不是让它多实现一套上报格式，而是让它把已经在写的东西**早一点、分片地**送过来。这是把接入成本压到最低的关键。

## ① WMS → Scheduling agent：`report`

字段名全部沿用 `WfFormat.execution`（见 `20260910_adding_the_network.md` §8.2），`NEW` 标记的是需要新增的：

```jsonc
{
  "platformRef": "wfplatform:esnet-anl-ornl@2026-08-20",
  "campaignRef": "wfcampaign:summer26-run17#sub-003",
  "reportedAt":  "2026-08-20T09:36:00Z",        // NEW：增量快照的时刻

  "tasks": [
    { "id": "ID0000001",
      "readyAt": "…09:00:00Z", "startedAt": "…09:00:05Z",
      "runtimeInSeconds": 4.2, "coreCount": 1, "machines": ["anl-n01"] }
  ],

  "files": [
    { "id": "chunk.txt",
      "locations": ["anl-n01", "anl-n02"],
      "sizeInBytes": 2.0e10 }                   // NEW：中间产物的实际大小
  ],

  "transfers": [
    { "fileId": "input.txt",
      "source": "aps-beamline-8id", "destination": "anl-n01",
      "startedAt": "…08:31:12Z",
      "durationSeconds": 1720.0, "bytesTransferred": 5.0e11,
      "path": ["APS-LCRC"],
      "rttMs": { "p50": 3.1, "p95": 4.4, "p99": 9.8 },
      "parallelStreams": 8, "protocol": "globus-gridftp",
      "concurrentTransfers": 2,
      "commitmentRef": "cmt-7f3a91",            // NEW：关联到 agent 的承诺
      "status": "completed" }                   // NEW：completed | failed | partial
  ],

  "machines": [ { "nodeName": "anl-n01", "site": "anl-lcrc", "cpu": { "coreCount": 8 } } ],
  "metrics":  { "sumTaskRuntimesInSeconds": 2104.2,
                "totalNumBytesTransferred": 5.2e11,
                "totalTransferSeconds": 1734.5 }
}
```

不需要的字段（算得出来，不让 WMS 填，少一个填错的机会）：task 的 `finishedAt`（`startedAt + runtimeInSeconds`）、transfer 的 `finishedAt` 和 `achievedRateGbps`（`bytesTransferred / durationSeconds`）。

### 必须新增的四项

**1.** `transfers[].commitmentRef`

现有的传输键是 `(fileId, source, destination, startedAt)`。Scheduling agent 手上有前三个，但 `startedAt` 是实际值——**重传时同一对端点会出现多条记录**，靠时间就近匹配是启发式的。配错就把别人的 achieved 算到这条 commitment 头上，而 achievability model 学的正是这一对数，等于污染训练集。

一个字符串换掉一个启发式匹配，很值。退路：不加也能跑（自然键 + 最近时间匹配），但要接受配对噪声。

**2.** `transfers[].status`（`completed | failed | partial`）

现在只记成功的传输，两个后果：

- **幸存者偏差**——achievability model 只见成功样本会系统性乐观，而失败的那些恰恰最该学
- **算不出 gate 4**——proposal 要 campaign success ≥ 90%，没有失败记录就没有分母

`partial` 时 `bytesTransferred` 记**实际传成的量**，不是应传的量。

**3.** `files[].sizeInBytes`

`execution.files[]` 现在只有 `id` 和 `locations[]`；而 `specification.files[].sizeInBytes` 对中间产物来说是**估计值**，真数运行时才知道。

这一条直接决定 `WfCampaign.estimates` 能不能训练——**估 vs 实的配对样本，"实"的那一半现在无处可取**。

**4. 增量上报的语义约定**（不是字段，是约定）

现在 `execution` 是运行结束后的一份完整文档。但 `refine` 要在 task 一完成就知道才能平移下游窗口，长回路也不该等整个 workflow 跑完。

约定：`report` 的 payload 就是 `execution` 的**同结构片段**，字段可缺、数组可只含新增项，接收方按主键合并；`reportedAt` 表明快照时刻。

### 三项可选，暂不决定


| 字段                          | 用途               | 为什么暂缓                                              |
| --------------------------- | ---------------- | -------------------------------------------------- |
| `tasks[].status`            | 区分正常完成 / 失败 / 被杀 | 失败 task 的 `runtimeInSeconds` 语义含糊，但影响面比 transfer 小 |
| `transfers[].rateProfile[]` | 分段实际速率，不只平均值     | 拥塞造成的速率波动会被平均值抹掉；v1 平均值够用，字段形状值得预留成 list           |
| `transfers[].retries`       | 重传次数             | 有 `status` 后可由多条记录数出来                              |


> 状态：**待定**，回顾时再决定。



### 一处已确认的语义

`transfers[].concurrentTransfers` 指**这条链路上所有的并发**，包含非本 workflow 的流量——不是同一 workflow 内的并发数。

这个口径是对的，因为它才是影响单流吞吐的真实因素，也正好对应 `blocked_by: foreign_traffic` 那一侧的信息；而同 workflow 的并发数 agent 自己就知道，不必上报。

> ② `transfer_outcome`（Scheduling → Network）的格式，见「Scheduling 到 Network Agent 的通信协议：Scheduling 怎么问」。
> ③ 从 SENSE-O / NDT 拉回来的三类，见「Network Agent 与 SENSE-O / NDT 的通信」。



## Scheduling agent 怎么用

**task 部分，三件事**


| 用途             | 怎么算                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 训练 `estimates` | `runtimeInSeconds` → `taskRuntimeSeconds` 的分布；`files[].sizeInBytes` → `fileSizeBytes`；`files[].locations` → `existingReplicas` |
| 校准自己计划的现实性     | `startedAt − suggested_start` 的分布。系统性偏晚 = 没考虑 GPU 排队，下次 `taskSchedule` 要留余量                                                    |
| 判断 WMS 依从度     | 同一分布看长期趋势。某个 WMS 长期不听，就别再基于建议启动时间做紧凑规划                                                                                         |


`readyAt` 与 `startedAt` 的差单独有用：**它把"等数据"和"等计算资源"分开了**——前者是我们的责任，后者不是。这个区分决定偏差该归咎于谁。

**network 部分，两件事**（转发之前它自己也要用）

- **承诺兑现记账**：实际完成时刻 vs 计划里的 `predicted_finish` → Commitment Ledger 的 workflow 侧，也是 demo 里那张"承诺 vs 兑现"图的数据源
- **fairness 记账**：每个 workflow 实际占到的 **slot·bandwidth 面积** → 我们给 0908 那个"fair share 分母未定义"问题的答案



## Network agent 怎么用

**来自 WMS 的 network 部分：配对与归因**

```
achieved = bytesTransferred / durationSeconds
reserved = 账本里 commitmentRef 对应的 rate
ratio    = achieved / reserved
```


| 用途                     | 怎么用                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------- |
| 回归 achievability model | `(reserved, 路径, 主机对, protocol, parallelStreams, concurrentTransfers, RTT) → achieved` 的参数拟合 |
| 归因诊断                   | ratio 稳定且与路径无关 → 端系统；ratio 波动且与时段相关 → 网络侧。**结合 ③ 的** `lossPct` **定案【啥意思】**                  |
| 收紧 confidence 区间       | 残差分布 → `predicted_finish` 的 p50/p95 宽度；决定 safety margin【啥意思】                                |
| 电路池决策                  | 某 circuit 上的实际利用率 → 空闲超时该不该拆、该不该缩容；也是**统计复用**将来要用的输入                                        |


**1. 归因诊断**

`ratio = achieved / reserved`，看它**跟着什么变**：


| 现象       | 例子                       | 说明瓶颈在                           |
| -------- | ------------------------ | ------------------------------- |
| 稳定且与路径无关 | 这对主机不管走哪条路、白天夜里，总是 ≈ 0.6 | **端系统**——瓶颈跟着主机走（NIC、磁盘、TCP 参数） |
| 波动且与时段相关 | 白天 0.4、夜里 0.9；或换条路就好了    | **网络侧**——瓶颈跟着网络状态走（拥塞、别人的流量）    |


判断出来之后修法不同：前者调并行流 / 换 DTN，后者换路径 / 换时段。

**2. 残差分布与 safety margin**

**残差** = 实际完成时间 − 模型预测的完成时间。每次传输完得到一个。

积累多次后看这堆误差：

- 误差小、集中 → 区间窄：`p50: 11:20, p95: 11:35`
- 误差大、分散 → 区间宽：`p50: 11:20, p95: 12:40`

p95 的意思是"95% 的情况下不会比这更晚"。

**safety margin** = 做承诺时额外留的余量。区间越宽，余量越大——比如按 p95 而不是 p50 去承诺完成时间、多留 slack、或预约时多要一点。**模型越准，余量越小，容量浪费越少**——这就是"收紧"的意思。

## 收束

**两条源、两个消费者、两个学习对象**：

```
task 部分     → Scheduling agent → 学「估计 → 实际」
network 部分  → 两边都用：Scheduling 记账兑现与公平，Network 配对 reserved vs achieved
SENSE 拉取    → Network agent   → 维护 observed 层 + 归因 + 冷启动先验
```

---



# Network Agent 与 SENSE-O / NDT 的通信

这是南向最后一段接口。**NDT（network digital twin）与 SENSE-O 在这里可互换**——Phase 1 跑 twin，接口不变，上面两层完全不知道底下换了什么。这条界面就是 0908 说的"Phase 1 以仿真为主"的落点。

## 下行：把 commitment 编译成 ServiceIntent

Network agent 是唯一碰 SENSE 的模块。它把账本上的一条 commitment 翻译成 `ServiceIntent`：

```jsonc
{
  "service": "dnc",
  "alias": "scinet-cmt-7f3a91",
  "queries": [ … ],
  "terminals": [                                  // ← 由 bindings 经 /discover/lookup 解析
    { "uri": "urn:ogf:network:anl.gov:2013:…", "vlan_tag": "any" },
    { "uri": "urn:ogf:network:ornl.gov:2013:…", "vlan_tag": "any" }
  ],
  "bandwidth": {
    "capacity": "40000",                          // Mbps 字符串；是 cap，不是吞吐保证
    "qos_class": "guaranteedCapped"               // guaranteedCapped | softCapped | anyAvailable | bestEffort
  },
  "schedule": { "start": "…09:00:00Z", "end": "…10:07:00Z" },
  "path_tprofile": { "exclusion_list": [ … ] }    // 只表达偏好，不指定链路序列
}
```

对应的生命周期动词（`PUT /instance/{siUUID}/{action}`）：


| 我们的动词     | SENSE 动作                         | 说明                     |
| --------- | -------------------------------- | ---------------------- |
| `hold`    | `propagate`                      | 算好并预留，不下发配置            |
| `commit`  | `commit`                         | 真正下发；失败走 `rollback`    |
| `modify`  | `POST /instance/{siUUID}/modify` | 在线改带宽或时间（快回路的"提速补量"用它） |
| `release` | `cancel` / `release`             | 拆除或释放                  |


两处纪律：

- `capacity` **是 cap，不是吞吐保证**——填进去的数字来自账本，而承诺给上层的完成时间必须经过 achievability model 折算，两者不是一个量
- **路径只作偏好**。`path_tprofile` 的 inclusion/exclusion 可以用，但绝不指定完整链路序列——0908 明确要求"保持 source 与 destination 固定，让中间网络图可变"，而且 SENSE 也读不回完整有序 route



## 上行：Network agent 主动拉的三类

**三类走的是两个不同的 API 面，可信度和可得性都不同**：


|                  | API 面                                                              | 状态           |
| ---------------- | ------------------------------------------------------------------ | ------------ |
| `CapacitySample` | **SENSE-O Northbound Intent API**（`total-block-maximum-bandwidth`） | 已确认可用        |
| `ServiceState`   | **SENSE-O**（`GET /instance/{uuid}`）                                | 已确认可用        |
| `ProbeResult`    | **SiteRM Debug API** —— 不是 SENSE-O。站点侧组件，由它驱动真实机器跑探测               | **三条未决**（见下） |


```jsonc
// CapacitySample —— SENSE-O。周期刷新，喂 observed 层
{ "src": "anl-lcrc", "dst": "ornl-olcf",
  "window": ["…09:00Z", "…09:15Z"],
  "maxReservableGbps": 100,          // 注意：整段窗口的瓶颈值
  "queriedAt": "…08:55Z", "validUntil": "…09:05Z",
  "source": "sense-query" }          // sense-query | twin

// ServiceState —— SENSE-O。服务生命周期
{ "serviceInstanceUuid": "…", "circuitId": "C1",
  "state": "STABLE",                 // CREATE-COMMITTED | STABLE | CANCEL-COMMITTING | …
  "provisioned": true, "changedAt": "…08:58Z" }

// ProbeResult —— SiteRM Debug API（rapid-ping / traceroute / iperf-client）。有代价
{ "src": "anl-lcrc", "dst": "ornl-olcf",
  "kind": "iperf",                   // iperf | rapid-ping | traceroute
  "measuredAt": "…08:50Z",
  "throughputGbps": 62.4,
  "rttMs": { "p50": 12.2, "p95": 18.0, "p99": 35.1 },
  "lossPct": 0.02, "path": ["L1", "L2", "L3"],
  "cost": { "bandwidthUsedGbps": 10, "seconds": 30 } }
```

全部进账本时必须带 provenance（`semantics`、`source`、`timestamp`、`valid_until`）。尤其 `ServiceState: STABLE` **只是配置状态，不是性能证据**——这是 0904 调研里点名的语义陷阱，混淆它会让账本把一条烂路当好路。

### SiteRM Debug API 这一路的四个后果

`ProbeResult` 到了机器那一层，但不是我们直连机器——是通过站点上的 SiteRM 转一手。0904 明确记着它*"属于 SiteRM Debug API，不是 SENSE-O Northbound Intent API"*。由此：

1. **可得性未确认。** 0904 的待核对清单里有三条悬着：是否允许直接访问 SiteRM、各站点支持哪些 debug action、**跨站点可访问性仍需部署实测**。所以 probe planner 的第一条规则应该是"先探测这个站点对支不支持探测"——这一步本身就可能失败。
2. **授权边界不同。** SENSE-O 一个 token 走天下；SiteRM 可能每个站点单独授权。多机构环境下这是真摩擦。
3. **单次探测不是持续遥测**（0904 原话）。`iperf` 给的是那一刻那一条合成流的数字，不是曲线——所以 ①（WMS 报上来的真实传输）才是 achievability model 的主数据源，探测只作补充与冷启动先验。
4. **Twin 要模拟两套接口。** 如果 twin 只实现了 SENSE-O 那一半，probe 这条路在 Phase 1 就是空的，achievability 的冷启动只能靠常数。**这一条值得提前问清楚**，它决定第一版有没有 probe planner。

**还有一层谁都够不着**：真正决定 achievable 的端系统事实——DTN 的 NIC 能力、PCIe、存储读写、TCP 拥塞控制参数——两个 API 都不给（0907 笔记里的 L4 缺口）。只能从 ① 的实测结果里**反推**，推不出成因，只能推出"这对站点就是跑不满"。

## 这三类各自去哪


|                  | 去哪                                                                | 注意                                       |
| ---------------- | ----------------------------------------------------------------- | ---------------------------------------- |
| `CapacitySample` | observed 层的时隙填充                                                   | 返回的是整段瓶颈值，所以刷新策略要决定切多细。**这是账本唯一的外部真相来源** |
| `ServiceState`   | circuit 层的生命周期跟踪                                                  | 只作 provisioning 状态用，**绝不作性能证据**          |
| `ProbeResult`    | RTT 进 achievability 的输入变量；`lossPct` 进归因判据；`path[]` 补 SENSE 读不回的路径 | 冷启动时它是唯一的先验来源                            |


---



# 如何将workflow拆分成任务

整份设计从"workflow 已经是一个 task DAG，且每个 task 的网络需求已知"开始，直接就有 `TransferRequest` 了。谁把 task 变成 TransferRequest，中间那一步是空的。

不过在补之前要先分清，"拆解"有三种读法，混在一起会补错地方：


| 读法       | 内容                         | 我们的状态                |
| -------- | -------------------------- | -------------------- |
| ① 解析     | workflow 文件本来就是 DAG，读出来    | adapter 层已覆盖，无智力含量   |
| ② **映射** | **task DAG → transfer 集合** | **完全空缺** ← 真缺口       |
| ③ 切分     | 一个大 transfer 切成多段错峰        | 协议里的 `divisible` 已占位 |




## 缺的是②：task DAG → transfer DAG

一条 task 依赖边**不一定**对应一次传输。


| 我要的            | schema 里的位置                               | 判定                       |
| -------------- | ----------------------------------------- | ------------------------ |
| task placement | `WfCampaign.submissions[].placement`      | ✅ 事前给定，正是我要的             |
| 数据对象与依赖        | WfFormat 本来就有 files + task I/O            | ✅                        |
| 副本位置           | `execution.files[].locations`             | ⚠️ 只有事后；规划前"某站点已有副本"无处表达 |
| task runtime   | `execution.tasks[].runtimeInSeconds`      | ❌ 观测值，不是估计值              |
| task 预计启动时间    | `execution.tasks[].readyAt` / `startedAt` | ❌ 同上                     |




## 当前wfschema：四层划分缺一个时态维度

这套 schema 的归属判据是 **"换个平台跑，这个值会不会变"**——一个关于*来源*的判据。四个桶里，spec / platform / campaign 都是事前，execution 是事后。

但"**预计** runtime"是**提交相关、且事前**的东西。它既不是平台固有（换平台会变）、也不是运行结果（还没跑）。**这个桶不存在。** 所以所有预测性的量都被挤进了 execution，而 execution 在时间上晚于我们需要它的时刻。

## 修法很小：WfCampaign 加一格

```json
"submissions": [{
  "placement": { "ID0000001": "anl-n01" },
  "sla": { ... },
  "estimates": {                                    ← 缺的这一格
    "taskRuntimeSeconds": { "ID0000001": 4.2 },
    "taskReadyAt":        { "ID0000001": "...09:00:00Z" },
    "fileSizeBytes":      { "chunk.txt": 20000000000 },
    "existingReplicas":   { "chunk.txt": ["anl-n02"] }
  }
}]

```

和 `placement`、`sla` 并列——它们性质完全一样：都是**提交时已决定、但运行前无法验证**的东西。

## 而这一格正是 agent 的产物

schema 已经把**反馈那一半做得很完整**了（execution 记录了 runtime、readyAt、实际传输、RTT、并发流数……）。缺的只是**前馈那一半**：

```
历次 execution.tasks[].runtimeInSeconds   ← schema 已有，很完整
              ↓  Tier 2.5（读历史 + workflow 结构，产出估计）
   WfCampaign.submissions[].estimates      ← 缺的这一格
              ↓  S1 前后向推导
        transfer 时间窗 → quote
              ↓  执行
        execution 回写                      ← 闭环

```

所以对 Rafael 的说法应该改一改：**不是"我们要三个新字段"，而是"schema 缺一格放 agent 的输出，而那一格填好之后，你们已有的 execution 记录就自动变成训练数据"。** 这个说法对他更有吸引力——他不用替我们造估计，只要留出位置。

## 顺带两处该提的问题

**1.** `route` **放在 campaign 里，和 0908 的指示直接冲突。**

```json
"route": { "anl-lcrc->ornl-olcf": ["L1", "L2", "L3"] }

```

KK 在 0908 明确要求："保持 source 与 destination 固定，让中间网络图可变，task 不应声明必须经过某个中间站点。"提交时钉死链路序列正是他要排除的做法。

而且按你 0904 的调研，SENSE **根本读不回完整有序 route**（§5.2.2）——所以这个字段既不该作输入，也填不满作输出。§9 那张映射表其实已经给了正确答案：路径只能作为 `path_tprofile` 的 inclusion/exclusion **偏好**，不是指定。建议把 `route` 从 campaign 挪到 execution，语义改成"事后观测到的路径"。

**2. §7.1 的带宽派生公式是欠定的。**

> 本次运行需要的带宽：由 `files[].sizeInBytes` 和对应文件 deadline 推导

`size / deadline` 只给出**平均速率**，不是一个可执行的预约——同一份需求有无数 (rate, window) 组合，选哪个取决于别人占了哪些时段。这正是我们第二步立的那条原则：形状是 network agent 的决策变量，不是 schema 层的一个除法。

建议 schema 只承载 `sizeInBytes` + deadline（它已经有了），**不要写这条派生规则**，否则会诱导实现者在 workflow 层就把带宽定死，把 agent 架空。

---



# 小结：还没设计的

**② commitment 的状态机与错误路径** 协议定了动词，没定状态。`quoted → held → committed → active → done` 之外，那些**错误路径**一个都没设计：hold 的 TTL 过期了怎么办、commit 到一半失败怎么回滚、circuit 建不起来算谁的、`at_risk` 之后 scheduler 迟迟不决策怎么办。协议目前只有 happy path，不完整。

**③ achievability model** 我一路当它存在，但没设计过。`reservable → achievable` 的映射到底长什么样、冷启动时用什么、从历史里学什么、怎么校准。这是 network agent 里**唯一真正在"学"的东西**，也是"agent 做出可兑现承诺"这个 framing 的核心——没有它，`predicted_finish` 就是编的。

**④ Tier 3 的 policy 接口形状** 我说要把 meta-decision 抽成可替换接口，但没定义接口签名。不定义就落不了地。

**⑤ 状态持久化与重启** agent 崩了重启，账本和承诺从哪恢复。SENSE 那边的预约还在，我们的记忆没了——这个不一致必须有处理办法。工程性质，但绕不过。

**⑥ 多实例** 一个 network agent 管全网，还是每个 domain 一个？DOE 多机构环境下这是真问题，但我倾向归 Phase 2。