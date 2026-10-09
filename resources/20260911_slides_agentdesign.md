# Slides 规划：Agent 架构设计（组会用）

- 来源：`resources/20260909_agentdesign.md` 的完整设计对话
- 叙事顺序：先给全局图，再自顶向下走（workflow → scheduling → network → SENSE）
- 正文 13 页 + 备份 5 页

---

## 1. 这次回答三个问题

**这页只讲一件事**：本次汇报的范围。

- 两个 agent 怎么分工？
- 它们之间说什么？
- 各自需要哪些输入？

---

## 2. Overview：四站 + 三条回路

**这页只讲一件事**：整个系统长什么样。全场的锚，后面每页都指回这张图。

```
                            人（科学家 / 运维）
                                   ▲
                        解释 / 协商 │ 自然语言
                                   │
Workflow 系统 ──submit/refine──▶ Scheduling ──quote/hold/commit──▶ Network ──ServiceIntent──▶ SENSE-O
 WfFormat      ◀───执行计划─────    Agent    ◀──repaired/at_risk──  Agent   ◀──state/telemetry──  或 twin
 WfPlatform                          │                               │    ③b 主动拉：周期刷新 + probe
 WfCampaign                          │                          ① 快回路
      │                              │                               │
      └──③a report───────────────────┴──转发网络部分──────────────────┘
         task 时间、文件落点                              在 Network agent 配对
         实测字节数 / 耗时 / 并行流数                     reserved vs achieved
                                                              ↓
                                       ③ 长回路：校准 achievability + estimates
                                ② 慢回路：at_risk 上行，Scheduling 重新仲裁
```

**长回路有两条源，不是一条**：③a 的 task 时间与实测传输量**只有 WMS 知道**（后者来自 Globus/Rucio 这类搬运工具），③b 的链路状态由 Network agent 向 SENSE/twin **主动拉**。③a 到 Scheduling 后要**再转一跳**给 Network agent——achievability model 在那儿，`reserved`（自己的账本）和 `achieved`（报上来的）必须在同一处配对。

---



## 3. SENSE 之上：两个 agent 的分工

**这页只讲一件事**：SENSE 的边界是清晰的，缺口在它上面那两层。

**SENSE 提供的 primitive**

- 一对 endpoint + bandwidth capacity + 时间约束（start / end=deadline）
- provision 整条 path，保证每条 link 留出容量
- 两阶段接口 `propagate → commit`（下一页会用到）

**缺口不在单次传输**：单个 task 把数据从 A 搬到 B，现有 SENSE 完全可做。缺的是 task 之间的**依赖**无法表达、多个 workflow 争抢时**谁让位**无人仲裁。

**所以在这个 primitive 之上建两层，按"面向谁说话"分工**


|                      | 说什么语言                                | 负责什么                                       |
| -------------------- | ------------------------------------ | ------------------------------------------ |
| **Scheduling agent** | workflow 语言：DAG、依赖、deadline、priority | 拆解 workflow、推导时间窗、跨 workflow 仲裁与 admission |
| **Network agent**    | 网络语言：circuit、bandwidth、时间窗           | 唯一碰 SENSE 的模块；持有容量账本，回答可行性                 |


这样分的三个后果：

1. **admission 落在有全局视图的一侧**——判断能不能接纳一个 workflow，必须知道别人已经占了多少；这个视图只有 Scheduling agent 有。
2. **只有一个模块碰 SENSE**——网络的所有细节（容量曲线、语义标注、achievability）都收在 Network agent 内部，上面看不见。
3. **两者之间只有一个协议**——正好对上 SENSE 的 `propagate → commit` 两阶段；而且这条界面就是 **digital twin 与真实 SENSE 的互换点**，Phase 1 换 twin 不影响上层。

---



## 4. Scheduling ↔ Network 的协议

**这页只讲一件事**：两个 agent 之间说什么。

**一条原则：发需求，不发方案。**
Scheduling 不说"给我 40 Gbps"（那已经是答案了），而说"这 5 TB 要在 t1 之后开始、t2 之前到"。带宽 × 时长的形状是 network agent 的决策变量——因为只有它看得见容量曲线。

**动词：5 下行 + 2 上行**

```
quote(bundle)        只读、不占资源            ┐
hold(offer, ttl)     试探性预留 → SENSE propagate │ Scheduling → Network
commit(hold_id)      落实      → SENSE commit     │
modify / release     在线调整 / 释放            ┘

repaired             已自主修复，承诺仍成立     ┐ Network → Scheduling
at_risk              承诺保不住，请重新决策     ┘（异步）
```

`hold` 为什么必需：有了它，一个 workflow 的全部 transfer 可以先 quote 一圈、全部 hold 住、确认都可行才原子 commit——**这就是 workflow admission 的正确实现**，而 SENSE 白送了这个能力。

**消息形状**

```
TransferRequest: id, workflow_id, priority, src, dst,
                 bytes(+is_estimate), window[earliest_start, latest_finish],
                 divisible, min_useful_rate

QuoteRequest:    bundle[], mode: all_or_nothing | best_subset

QuoteResponse:   status, offers[{start, rate_profile, predicted_finish, confidence}],
                 binding{ when, blocked_by: own_commitment | foreign_traffic }
```

两处刻意设计：

- `offers` **是复数** = counter-offer 的载体，而且是结构化、能直接进求解器的，不是给人看的一句话
- `blocked_by` **只需两个值**：`own_commitment`（可抢占/让路）vs `foreign_traffic`（不归我管，只能绕）——这一条区分让优先级仲裁从盲目试错变成有向搜索

**执行回写的上行：**`transfer_outcome`（Scheduling → Network，执行之后）

```jsonc
{ "commitmentRef", "fileId", "source", "destination", "startedAt",
  "durationSeconds", "bytesTransferred", "path", "rttMs",
  "parallelStreams", "protocol", "concurrentTransfers", "status" }
```

`commitmentRef` 是关键——Network agent 靠它把 `reserved`（自己账本里的）和 `achieved`（这里报上来的）配成一对，喂 achievability model。

---



## 5. Scheduling ↔ WMS：执行计划

**这页只讲一件事**：control plane 和 data plane 怎么对上。

**WMS 是数据传输的发起方，不是 SENSE 的调用方。**

```
control plane：Network agent ──ServiceIntent──▶ SENSE-O      预约电路
data plane：   WMS ──Globus / GridFTP / Rucio──▶ 实际搬字节
```

北向三个动词：`submit`（提交 DAG，返回执行计划）/ `refine`（运行时把估计换成事实）/ `report`（执行回报）。

**执行计划有三样内容**

```
taskSchedule[]      { task_id, suggested_start }                        建议
transferWindows[]   { transfer_id, start, rate_profile,
                      predicted_finish, confidence }                    已预约的事实
endpointBindings[]  { transfer_id, src_uri, dst_uri, vlan, interface }  技术必需
```

**第三样不可省**：SENSE provision 出来的是带特定 VLAN / IP / network attachment point 的路径，**传输必须在那些具体端点之间发起才会落到电路上**，否则数据照走默认路由，预约白做。这正是 Rucio–SENSE 论文里 **DMM 干的事**——0908 那条"重读 DMM paper"的行动项，补的就是这一块。

→ 对南向协议的影响：`commit` 不能只返回 `commitment_ids`，必须同时返回端点绑定信息。

**为什么** `submit` **必须返回一份计划**：transfer 的 `earliest_start` 是从上游 task 何时产出数据推出来的。task 起晚了，电路开着数据没到，容量空占；起早了，数据就绪电路没开，白等。不返回计划就只能被动等 WMS 说"我要传了"——那就看不见 DAG、算不出 slack，**整个设计退化成 baseline**。

**它是协商，不是命令**：计算调度不归我们管，所以 `taskSchedule` 是建议（WMS 可以说做不到，agent 重规划），`transferWindows` 才是已预约的事实。这也是画成双向链路的原因。

**执行回写：**`report`（增量上报，按主键合并）

```jsonc
{ "platformRef", "campaignRef", "reportedAt",
  "tasks":  [ { "id", "readyAt", "startedAt", "runtimeInSeconds",
                "coreCount", "machines" } ],
  "files":  [ { "id", "locations", "sizeInBytes" } ],
  "transfers": [ { "fileId", "source", "destination", "startedAt",
                   "durationSeconds", "bytesTransferred", "path", "rttMs",
                   "parallelStreams", "protocol", "concurrentTransfers",
                   "commitmentRef", "status" } ] }
```

Scheduling agent 用 task 部分学「估计 → 实际」，喂 `WfCampaign.estimates`；network 部分贴上 `commitmentRef` 转给 Network agent。

---



## 6. Scheduling agent：拆解与 slack

**这页只讲一件事**：slack 是全部调度自由度的来源。

**S0 拆解**（KK 强调它在 admission 之前）：task DAG → transfer 集合。

一条 task 依赖边**不一定**产生传输，取决于三件事：

- task placement（同站点则无传输）
- 数据对象与大小
- **副本位置**——目标站点已有副本就不用传

其中"从哪个副本取"是一个真实的决策点，不是解析。

**S1 时间窗推导**：

```
前向：从 DAG 起点推每个 transfer 的 earliest_start（上游何时产出数据）
后向：从 workflow deadline 倒推 latest_finish（下游何时必须启动）
差值 = slack
```

**没有 slack，每个 transfer 都是"必须马上传"**——错峰无从做起，counter-offer 也没得谈。

---



## 7. Scheduling agent：在优化什么

**这页只讲一件事**：offer 都可行，选择优化的是机会成本。

每个 offer 单独看都成立——但"可行"是相对于**当前**账本的。选中任何一个都会改变账本，决定后面的 transfer 还剩什么位置。

> 如果整批只有一个 workflow，选哪个 offer 几乎无所谓。**offer 选择的全部价值来自竞争。**

早 vs 晚是真实权衡：


| 选早完成                    | 选晚完成                  |
| ----------------------- | --------------------- |
| 留下大 slack → 故障时快回路有预算自修 | slack 用光 → 一出事就升级到慢回路 |
| 但占住早期容量，可能挡死更紧急的后来者     | 让出早期容量                |


slack 既是调度自由度，也是抗故障储备——**两个用途在抢同一个额度**。

**目标函数的分法**（避免多目标打架）：

```
硬约束：容量不超限制                          ← correctness，不是目标
硬约束：每个 workflow ≥ 30% fair share    ← proposal 的保底条款
目 标：最大化   Σ  utility_i(completion_time_i)
        i
```

---



## 8. Network agent：容量账本

**这页只讲一件事**：账本是一条时间轴上的曲线，不超容由本地减法保证。

**账本长什么样**：按 (src, dst) 建账，时间切成离散时隙

```
  ANL→ORNL      09:00  09:15  09:30  09:45  10:00  10:15   (Gbps)
  observed       100    100    100     40     40     40
  own(已 hold/commit) 40   40      0      0     25     25
  ──────────────────────────────────────────────────────
  可用            60     60    100      0     15     15
```

quote 就是在这张表上找放置——**"最早什么时候能开始"直接查表，不用问 SENSE**。

**曲线不是查来的，是重建出来的**

SENSE 的查询是"给一个时间窗 → 返回整段**都能保证**的容量"，也就是瓶颈值：

```
查 [09:00, 15:00] → 40        ← 整段取最小，看不到 09:00–09:45 有 100
查 [09:00, 09:45] → 100
```

一次查询把曲线压成一个数。要拼出上面那张表，只能**把窗口切开反复问**——6 小时按 15 分钟粒度就是 24 次。三个参数进 config：**horizon**（往未来看多远）、**slot 粒度**（离散时隙，量化误差 vs 装箱复杂度）、**刷新策略**（何时、在哪些时间点重新采样 observed 层）。

**为什么不能无状态**：除了查询次数（gate 要求 p50 < 200 ms），真正的杀手是——**放完第一条 transfer 后，第二条的查询结果是错的**，SENSE 不知道你刚安排了第一条。你只能本地扣掉再算。那一刻你已经在建账本了，只是建在临时变量里用完就扔。

**两层，信任等级不同**

```
observed 层  ← SENSE / twin：这条路"外界"还剩多少
             语义 = reservable，会过期、有误差、要主动刷新

own 层       ← 我们自己 hold / commit 出去的每一笔
             语义 = allocated，精确、即时、无需查询
```

```
可用量(t) = observed(t) − Σ own(t)
```

**这条减法必须在本地做。** 刚 commit 的预约，SENSE 的视图可能还没反映出来；依赖它反映，就会把同一段容量卖两次。KK 点名要求的"并发调度总需求不超过 capacity"，靠的是这条减法，不是 SENSE。

**一处必须诚实承认的不健全**：SENSE 不暴露内部 node-link graph，账本只能按 (src, dst) 建账，不能按 link 建账。两条路可能共用看不见的瓶颈。处理方式：safety margin + commit 前核对（`propagate` 天然是核对点）+ 运行时 `at_risk` 兜底。

---



## 9. Network agent：承诺 ≠ 电路

**这页只讲一件事**：一个 transfer 不等于一条 circuit。

SENSE 建 L2 overlay 很慢，所以 overlay 长期保留，快速恢复发生在 L3（flow redirection）。**30 秒恢复目标直接排除了"故障后重建电路"这条路。**

```
commitment（逻辑承诺，对 Scheduling 说的话）
        ↓  多对一
circuit（物理电路，对 SENSE 说的话）
```

**commitment 是一趟班次，circuit 是一条包下来的专用车道**——开辟车道要几分钟，排班次是瞬间的事。

```
circuit C1：ANL→ORNL，100 Gbps，09:00 建立，18:00 拆除
            └── 对 SENSE 说的：provision 一条物理电路，只做一次

  09:00         10:30        12:00        14:00        18:00
  │─commitment A─│──空闲──│─commitment B─│─commitment C─│
      WF-1 的传输              WF-2 的传输    WF-1 的另一条
      └───── 对 Scheduling 说的：我承诺你的数据几点到 ─────┘
```

三个 commitment 来自不同 workflow，但**只 provision 了一次电路**。电路按需懒创建、用完保温、空闲超时才拆——本质是连接池。

这一层解释三件事：

- 30 秒恢复变得可信（不重建电路，只在已有电路内改路径或速率）
- 电路建立延迟被摊薄，quote→commit 才可能落进 p50 < 200 ms
- ledger 要分别记 commitment 和 circuit，两套时间轴
  - **commitment 层**：谁承诺了什么、什么时候、多少带宽 ← 对 scheduling agent 负责
  - **circuit 层**：哪些电路开着、剩多少余量、什么时候拆 ← 对 SENSE 负责

**代价**：图里 10:30–12:00 那段空闲，电路预约的容量仍然锁着，别人用不了。这正是 KK 批评 DMM 的那件事（固定分配、flow 间不复用）。**统计复用的入口就在这一层**：让保温电路的闲置容量能被别的 commitment 借用。第一版不做，但架构上留位置。

**失败闭环**：判据是 slack，协议已经带着所需信息。

```
偏差被检测到
   ├─ 还赶得上 latest_finish  → 快路径：自己修，事后发 repaired
   └─ 赶不上了               → 慢路径：发 at_risk，Scheduling 重新仲裁
```

---



## 10. Network ↔ SENSE-O / NDT 的接口

**这页只讲一件事**：这里是 digital twin 与真实 SENSE 的**互换点**——Phase 1 跑 twin，接口不变，上面两层不知道底下换了什么。

**下行：把一条 commitment 编译成** `ServiceIntent`

```jsonc
{ "service": "dnc", "alias": "scinet-cmt-7f3a91",
  "terminals": [ { "uri": "urn:ogf:network:anl.gov:…", "vlan_tag": "any" },
                 { "uri": "urn:ogf:network:ornl.gov:…", "vlan_tag": "any" } ],
  "bandwidth": { "capacity": "40000",                 // Mbps 字符串
                 "qos_class": "guaranteedCapped" },   // 四档之一
  "schedule": { "start": "…09:00:00Z", "end": "…10:07:00Z" },
  "path_tprofile": { "exclusion_list": [ … ] } }      // 只表达偏好
```


| 我们的动词     | SENSE 动作                                      |
| --------- | --------------------------------------------- |
| `hold`    | `propagate`（算好并预留，不下发配置）                      |
| `commit`  | `commit`（真正下发；失败走 `rollback`）                 |
| `modify`  | `POST /instance/{siUUID}/modify`（快回路"提速补量"用它） |
| `release` | `cancel` / `release`                          |


**上行：Network agent 主动拉的三类 —— 但走的是两个 API 面**

```jsonc
// SENSE-O Northbound Intent API —— 已确认可用
CapacitySample { src, dst, window, maxReservableGbps, queriedAt, validUntil, source }
ServiceState   { serviceInstanceUuid, circuitId, state, provisioned, changedAt }

// SiteRM Debug API（rapid-ping / traceroute / iperf-client）—— 不是 SENSE-O，可得性未确认
ProbeResult    { src, dst, kind, measuredAt, throughputGbps, rttMs, lossPct, path, cost }
```

### CapacitySample

**是什么**：向 SENSE 问一次"这段时间还能预约多少"得到的一条答案。**它是 observed 层的原料**——账本那条容量曲线就是用许多条 CapacitySample 拼出来的。


| 字段                  | 含义                                                          |
| ------------------- | ----------------------------------------------------------- |
| `src` / `dst`       | 站点对，账本的主键（账本只能按 (src,dst) 建账，不能按 link）                      |
| `window`            | 这次问的时间窗 `[t0, t1]`                                          |
| `maxReservableGbps` | **整段窗口都能保证**的最大可预约带宽，也就是这段时间里的瓶颈值                           |
| `queriedAt`         | 什么时候问的 → 这条数据多旧                                             |
| `validUntil`        | 何时视为过期，驱动刷新策略                                               |
| `source`            | `sense-query`（真 SENSE）还是 `twin`（仿真）——provenance，用来区分实测量与模拟量 |


两处纪律：

- `window` 越大，`maxReservableGbps` 越粗——问 6 小时只会得到最窄那一处的数。所以刷新策略要决定把窗口切多细
- 它是 **reservable**，不是 achievable。进账本时语义要标清楚，做承诺前必须过 achievability model 折算

> Q: 但是只有hold/commit/modify/release四个API，哪问的capacitysample？
>
> A: 不走那四个。**它们是生命周期动作，作用在一个已存在的 service instance 上；容量查询是另一条路径。**
>
> **CapacitySample 实际怎么问:**
>
> ```
> GET  /instance                                    → 领一个新的 siUUID
> POST /instance/{siUUID}?sync=true&proceed=false    → 提交带 queries[] 的 ServiceIntent
> 读   $.queries[*].results[*].bandwidth             → 单位 bit/s，÷1e6 得 Mbps
>
> ```
>
> 请求体里那段就是查询本身：
>
> ```jsonc
> { "ask": "total-block-maximum-bandwidth",
>   "options": [ { "name": "Connection 1", "start": "now", "end-before": "+1h" } ] }
>
> ```
>
> `proceed=false` **是关键**——只计算、只回答，不下发配置。
>
> 字段对应关系：
>
>
> | CapacitySample      | 来自                                                                       |
> | ------------------- | ------------------------------------------------------------------------ |
> | `src` / `dst`       | intent 里的 `terminals`（由 `bindings` 经 `GET /discover/lookup/{name}` 解析出来） |
> | `window`            | `options[].start` / `end-before`                                         |
> | `maxReservableGbps` | `$.queries[*].results[*].bandwidth ÷ 1e6`                                |
> | `queriedAt`         | 我们本地记的请求时刻                                                               |
> | `validUntil`        | **SENSE 不给，是我们刷新策略自己定的**                                                 |
> | `source`            | 我们自己标的 provenance                                                        |
>
>
> `ServiceState` 又是第三条路径：`GET /instance/{uuid}` 读回 intent 与 provision 状态，`GET /discover/service/instances` 列出已有实例。
>
> ## 三条结论
>
> **1. 我们的动词映射表漏了两类调用。** 文档里只写了 `hold/commit/modify/release → propagate/commit/modify/release`，那只是生命周期。还缺 **query**（容量查询）和 **discovery**（端点解析）两类，应该补进 0909 的「Network Agent 与 SENSE-O / NDT 的通信」和 slides 第 10 页。
>
> **2.** `proceed=false` **和** `propagate` **必须分清。** 前者只算不留；后者真的预留资源。对应到我们的协议：`quote` 背后是 `proceed=false` 的查询，`hold` 背后才是 `propagate`。这一层之前混着讲了。
>
> **3. 刷新的代价比预想高一档。** 查一次容量 = 领一个 siUUID + POST 一个 intent，**不是一次轻量 GET**。24 个时隙频繁刷新意味着大量 instance 创建，可能还要清理。这让"近期密、远期疏"从优化变成必需，也可能逼我们把时隙粒度放粗。
>
> 顺带一个好处：这个 query **同时算了一条可行路径**，所以它一并回答了"有没有路"——正好是 `status: unreachable` 的判据来源。

### ServiceState

**是什么**：一条已下发的 SENSE service instance 现在处于什么生命周期阶段。**它服务于电路池和承诺状态机**，不服务于性能判断。


| 字段                    | 含义                                                                    |
| --------------------- | --------------------------------------------------------------------- |
| `serviceInstanceUuid` | SENSE 侧的 service instance id（`siUUID`），我们提交 intent 后拿到的               |
| `circuitId`           | 我们电路池里自己的 id，和上面那个 uuid 一一对应                                          |
| `state`               | SENSE 的生命周期状态：`CREATE-COMMITTED` / `STABLE` / `CANCEL-COMMITTING` / … |
| `provisioned`         | 配置是否已真正下发（布尔）                                                         |
| `changedAt`           | 上一次状态变化的时刻                                                            |


用途三处：

- **确认 hold / commit 真的生效**了——`propagate` 之后是不是到了预期状态，`commit` 之后是不是 `provisioned: true`
- **电路池管理**：哪些电路开着、是否该保温、空闲多久该拆
- **故障感知**：电路掉出 `STABLE` 是一个明确的事件信号（对比之下，吞吐退化只能靠统计判断）

**最重要的一条纪律**：`state: STABLE` **只说明配置正常，不说明性能达标**。这是 0904 调研点名的语义陷阱——一条 STABLE 的电路完全可能只跑到预约值的一半。把它当性能证据，账本就会把一条烂路当好路。





`CapacitySample` 填 observed 层，是账本唯一的外部真相来源；`ServiceState` 跟踪电路生命周期；`ProbeResult` 供 RTT 与丢包，冷启动时是唯一先验。

**SiteRM 那一路要单独说**：它到了机器那一层（由站点侧的 SiteRM 驱动真实机器跑探测），但 0904 列了三条未决——是否允许直接访问、各站点支持哪些 action、跨站点可访问性未实测。而且**单次探测不是持续遥测**。所以 achievability 的主数据源是 WMS 报上来的真实传输，探测只作补充。**若 twin 只实现 SENSE-O 那一半，Phase 1 就没有 probe planner。**

**两处纪律**

- `capacity` **是 cap，不是吞吐保证。** 填进去的数字来自账本，而承诺给上层的完成时间必须经 achievability model 折算——两者不是一个量
- `ServiceState: STABLE` **只是配置状态，不是性能证据。** 混淆它，账本会把一条烂路当好路（0904 点名的语义陷阱）
- **路径只作偏好。** `path_tprofile` 的 inclusion/exclusion 可以用，但绝不指定完整链路序列——0908 要求"保持 source 与 destination 固定，让中间网络图可变"，而且 SENSE 也读不回完整有序 route

---



## 11. LLM 放在哪

**这页只讲一件事**：按**工作性质**分四类——不是层次，是四种不同的活。


| 这类工作     | 具体是什么                                | 用 LLM？    | 理由                                                                      |
| -------- | ------------------------------------ | --------- | ----------------------------------------------------------------------- |
| **算数字**  | 关键路径推导、账本减法、quote 求解、容量核算            | **绝不**    | 都有精确算法（CPM、数组减法、一维扫描+贪心），毫秒级可复现；LLM 只会更慢更贵，而**算错 = demo 出现 overcommit** |
| **构造问题** | utility 曲线、缺失参数推断、约束形式化              | **是**     | 输出是**小的、人能一眼审的结构化对象**，再交给求解器消费                                          |
| **对人说话** | 入口归一化、缺失信息追问、解释与协商                   | **是**     | 输入是开放的（DAX / CWL / 一段话），输出给人看，没有精确算法                                    |
| **做取舍**  | 刷新策略、probe planner、`at_risk` 响应、搜索停止 | **v1 不用** | 先用规则跑通，抽成**可替换的 policy 接口**；之后才有资格量化对比 LLM 是否更好                         |


**三个要点**：

1. LLM **不能直接写账本、不能直接产出数字承诺**——只能通过 policy 接口和归一化/解释接口作用于系统
2. **解释是渲染，不是推理**——生成解释时只允许读 Commitment Ledger 和 `binding`，不允许重新推导数字
3. **两个 agent 之间只走类型化协议，不走自然语言**

> 一句话原则：**自然语言只出现在系统边界（对人），不出现在系统内部（agent 之间）。**

---



## 12. Workflow schema：现有四层供给什么

**这页只讲一件事**：已有的 schema 大部分够用。


| 层                        | 内容                                                               | 供给谁                                                         |
| ------------------------ | ---------------------------------------------------------------- | ----------------------------------------------------------- |
| `WfFormat.specification` | task DAG、文件依赖与大小、端点角色、应用固有 `constraints`                         | Scheduling：S0 拆解 + S1 推导                                    |
| `WfPlatform`             | domains / sites / links / routes、容量、延迟 —— **静态拓扑快照**             | Network：**账本的初始化输入（seed）**                                  |
| `WfCampaign`             | `placement`、`bindings`、`sla`（deadline/priority）、`arrivalProcess` | Scheduling：拆解的必要输入 + 目标函数                                   |
| `WfFormat.execution`     | 任务时间、文件位置、实际 `transfers[]`、RTT、并行流数                              | Scheduling：训练 `estimates`；Network：配对 `reserved vs achieved` |


前三层是**规划前**的输入，`execution` 是**运行后**的事实——它同时喂两个 agent，各取一半（task 部分给 Scheduling，network 部分给 Network），这就是 Overview 图里那条长回路。

一处澄清：WfPlatform 描述网络却挂在 workflow 侧，和容量账本看似撞车。切法是——

- **WfPlatform = 静态拓扑快照**（自带 `measuredAt`）→ 账本的 seed
- **容量账本 = 动态时间轴 + own 层** → 必须在 network agent 内部，外部 schema 表达不了

seed 与 state 的关系，不重复。

---



## 13. Workflow schema：缺的一格与两处修正

**这页只讲一件事**：给 Rafael 的具体请求。

**问题**：schema 的四层划分判据是"换个平台跑值会不会变"——一个关于*来源*的判据，**没有时态维度**。所有预测性的量都被挤进了 `execution`（事后），而规划需要它们在事前。


| 规划需要           | schema 里的位置                           | 判定         |
| -------------- | ------------------------------------- | ---------- |
| task placement | `WfCampaign.submissions[].placement`  | ✅ 事前给定     |
| 数据对象与依赖        | WfFormat 已有                           | ✅          |
| task runtime   | `execution.tasks[].runtimeInSeconds`  | ❌ 观测值，非估计值 |
| task 预计启动时间    | `execution.tasks[].readyAt/startedAt` | ❌ 同上       |
| 已有副本位置         | `execution.files[].locations`         | ⚠️ 只有事后    |


**修法：WfCampaign 加一格，和** `placement`**、**`sla` **并列**（性质相同：提交时已决定、运行前无法验证）

```json
"estimates": {
  "taskRuntimeSeconds": { "ID0000001": 4.2 },
  "taskReadyAt":        { "ID0000001": "2026-08-20T09:00:00Z" },
  "fileSizeBytes":      { "chunk.txt": 20000000000 },
  "existingReplicas":   { "chunk.txt": ["anl-n02"] }
}
```

**而这一格正是 agent 的产物**——schema 的反馈那一半已经很完整，缺的只是前馈：

```
历次 execution 记录 ──Tier 2.5──▶ WfCampaign.estimates ──S1 推导──▶ transfer 时间窗
        ▲                                                              │
        └──────────────────── 执行后回写 ──────────────────────────────┘
```

**两处修正**

1. `route` **应从** `WfCampaign` **挪到** `execution`。提交时钉死链路序列，与 KK 在 0908 的指示直接冲突（"保持 source 与 destination 固定，让中间网络图可变"）；而且 SENSE 读不回完整有序 route，这个字段既不该作输入也填不满作输出。至多作为 `path_tprofile` 的 inclusion/exclusion **偏好**。
2. **带宽派生公式（**`size / deadline`**）不要写进 schema**。它只给出平均速率，不是可执行的预约——同一份需求有无数 (rate, window) 组合，选哪个取决于别人占了哪些时段。写进 schema 会诱导实现者在 workflow 层把带宽定死，把 agent 架空。schema 只承载 `sizeInBytes` + deadline（已经有了）。

---

