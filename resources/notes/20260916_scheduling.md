# Scheduling Agent：它做什么，以及怎么用遥测

- 来源：`20260909_agentdesign.md`（设计对话）、`20260911_slides_agentdesign.md`（第一版 slides 规划）、`20260914_slides_v2.md`（KK 反馈后的修正）。三份之间有演进，本文以**最新口径**为准，冲突处在正文注明。
- 用途：为补充 scheduling agent 的 slides 理清逻辑线。已有两页（拆解与 slack、offer 选择）分别落在本文 §3.1–3.2 与 §3.4。
- 状态标记：**【已定】** 会上或笔记里已拍板；**【倾向】** 有主张、未拍板；**【未定】** 明确悬置；**【待核对】** 依赖外部事实。

---

## 1. Overview：一条主线、三个阶段、三类信息

### 1.1 一句话定位

**Scheduling agent 把 workflow 的依赖和 deadline 翻译成网络能执行的需求（带时间窗的传输），在多个 workflow 之间仲裁网络容量；运行时再把遥测翻译回"对 workflow 意味着什么"，决定要不要重排。**

它讲 *workflow 语言*（DAG、依赖、deadline、utility），不碰 SENSE；网络语言归 network agent。两者之间只走类型化协议。

### 1.2 主线：slack 的一生

Scheduling agent 做的所有事，都围着一个量转——**每个节点（transfer / task）的 slack**。

```
规划期                         运行期                              跨 run
─────────────────────────     ──────────────────────────────     ──────────────────────
推导时间窗 → 产生 slack         遥测到达 → 更新 slack.remaining      执行事实回流
在 compute / transfer 间分配    remaining < 0 → 受影响，重排         → 估计更准
选 offer → 消耗 slack           remaining ≥ 0 → 不动（避免误伤）     → 下次 slack 算得更准、留得更省
```

- **规划期产生并花掉 slack**：slack 就是调度自由度（能错峰、能谈 counter-offer）。
- **运行期遥测的全部作用，是把 slack 从一个"计划值"变成一个"实时值"**。遥测本身不触发动作；slack 余量变负才触发。
- **跨 run 的执行事实让 slack 的来源（runtime、数据量、排队时间的估计）更准**。估计越准，要预留的安全余量越少，浪费的容量也越少。



### 1.3 三个阶段、十个任务

**规划期**（admission 前后）


| #   | 任务                        | 输入                                                                         | 输出                                              | 本文   |
| --- | ------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------- | ---- |
| P1  | 拆解：task DAG → transfer 集合 | DAG、placement、文件大小、副本位置（**不涉及时间**）                                         | TransferRequest 集合（窗口未填）                        | §3.1 |
| P2  | 推导时间窗、分配 slack            | P1 的结果 + deadline + **task 的 runtime / 排队时间估计（p50、p95）** + 设备产出时刻 + 传输名义时长 | 每个 transfer 的 `[earliest_start, latest_finish]` | §3.2 |
| P3  | 构造目标                      | workflow 描述、SLA、领域惯例                                                       | utility 曲线 + priority                           | §3.3 |
| P4  | 问网络、选 offer、admission     | bundle → offers                                                            | 原子 commit 的一组放置                                 | §3.4 |
| P5  | 下发执行计划                    | 已 commit 的放置 + 端点绑定                                                        | ExecutionPlan → WMS                             | §3.5 |


**运行期**（分钟级）


| #   | 任务           | 输入                                   | 输出                 | 本文   |
| --- | ------------ | ------------------------------------ | ------------------ | ---- |
| R1  | 吸收事实（refine） | 实际大小 / 完成时间 / 落点 / 分支                | 更新后的窗口；必要时重新 quote | §4.2 |
| R2  | 响应网络异常       | `repaired` / `at_risk`（成批，带 `cause`） | 受影响集合 → 重排         | §4.3 |
| R3  | 响应计算超时       | 看门狗（事件缺席）                            | 挪下游网络预约            | §4.4 |
| R4  | 重排与同步        | 受影响集合 + utility                      | 协议动作 + 新执行计划       | §4.5 |


**跨 run**（长回路）


| #   | 任务         | 输入        | 输出                                       | 本文   |
| --- | ---------- | --------- | ---------------------------------------- | ---- |
| L1  | 从执行事实学习与记账 | 历次 report | `estimates`、计划偏差、WMS 依从度、兑现 / fairness 账 | §5.1 |




### 1.4 三类信息，按"何时到达"分


| 类别                     | 内容                                                  | 来源                                                    | 到达时机    | Scheduling agent 用来做什么 |
| ---------------------- | --------------------------------------------------- | ----------------------------------------------------- | ------- | ---------------------- |
| **① 规划输入**（事前）         | DAG、文件大小、placement、SLA、`estimates`                  | WfFormat / WfCampaign                                 | 提交时     | P1–P3                  |
| **② 网络回答**（事前，但依赖网络遥测） | offers（带 `predicted_finish{p50,p95}`）、`binding`     | Network agent（背后是 SENSE 容量查询 + achievability model）   | quote 时 | P4                     |
| **③ 运行时事件**（事中）        | task 就绪/开始/完成、文件实际大小、传输完成；`repaired` / `at_risk`；超时 | WMS → Telemetry Service；Network agent；Runtime DAG 看门狗 | 分钟级     | R1–R4                  |
| **④ 执行事实**（事后）         | 同 ③ 的累积记录                                           | 历次 `report`                                           | 跨 run   | L1，反过来改善 ①             |


注意 ② 这一格：**scheduling agent 在规划期就已经在间接使用网络遥测了**——offer 里的 p95 完成时间，是 network agent 用历史传输实测校准过的（reservable ≠ achievable）。所以"遥测"不是只在运行期才出场。

---



## 2. 规划输入：从哪拿到什么


| 需要                   | 在哪                                   | 现状                                           |
| -------------------- | ------------------------------------ | -------------------------------------------- |
| task DAG、文件依赖与大小     | `WfFormat.specification`             | ✅ 已有；中间产物大小只是估计（`is_estimate`）               |
| task placement       | `WfCampaign.submissions[].placement` | ✅ 事前给定                                       |
| deadline / priority  | `WfCampaign.submissions[].sla`       | ✅ 已有                                         |
| task runtime 估计      | —                                    | ❌ 只有事后的 `execution.tasks[].runtimeInSeconds` |
| task 预计就绪 / 启动时间     | —                                    | ❌ 只有事后的 `readyAt` / `startedAt`              |
| task 排队时间（p50 / p95） | —                                    | ❌ 只能从事后 `startedAt − readyAt` 学（§3.2 前后向都要用） |
| 已有副本位置               | —                                    | ⚠️ 只有事后的 `execution.files[].locations`       |


**缺口**：schema 的四层按"来源"划分，没有时态维度。预测性的量只能挤在事后的 `execution` 里，而规划需要它们在事前。

**修法（给 Rafael 的请求）**：`WfCampaign.submissions[]` 加一格 `estimates`，与 `placement`、`sla` 并列。

```json
"estimates": {
  "taskRuntimeSeconds": { "ID0000001": { "p50": 4.2, "p95": 6.0 } },
  "taskQueueWaitSeconds": { "ID0000001": { "p50": 600, "p95": 1800 } },   // 本文新增，§3.2
  "taskReadyAt":        { "ID0000001": "2026-08-20T09:00:00Z" },
  "fileSizeBytes":      { "chunk.txt": 20000000000 },
  "existingReplicas":   { "chunk.txt": ["anl-n02"] }
}
```

**这一格是 scheduling agent 自己的产物**（§5.1），由历史执行事实推出来。对 Rafael 的说法：不是"我们要三个新字段"，而是"留出一格放 agent 的输出，你们已有的 execution 记录就自动变成训练数据"。

**为什么缺了不行**（论证链）：没有 task runtime 估计 → 后向推导不成立 → transfer 时间窗导不出来 → 算不出 slack → 时间维度是假的，agent 退化成 SENSE 转发器。

> 【未定】时间窗是 agent **推导**，还是 workflow **直接声明**每个 transfer 的 deadline？倾向推导：声明进来的 deadline 已经吃掉了 slack，而且 `refine` 只在推导模式下才有意义。

---



## 3. 规划期

规划期五步：P1–P2 对应已有第 9 页，P4 对应已有第 10 页。P1–P2 用一个贯穿例子 **W1** 走完。

### 3.1 P1 拆解：task DAG → transfer 集合

一条 task 依赖边**不一定**对应一次传输，由三件事决定：

- **task placement**：同站点，不用传
- **数据对象及其大小**
- **副本位置**：目的站点已有副本，不用传

"从哪个副本读"是真正的决策点，不只是解析。**拆解发生在 admission 之前**（KK 强调）。P1 **只看结构、不看时间**，所以这一步不需要 compute 时间。

> 【待核对 / 倾向】0914 指出 Pegasus Mapper 本来就会插入跨站点传输节点，也有 replica selector。所以 P1 和副本选择**可能让给 Pegasus**：scheduling agent 直接读 Mapper 产出的可执行 workflow。需要 Rafael 确认 Pegasus 5.x 的现状。slides 上建议写成"P1 可由 WMS 完成，我们消费它的结果"，避免被指出和 Pegasus 重复。



#### 例子 W1：输入

站点沿用 Overview 图里的物理网络。W1 是"光源采集 → ANL 预处理 → ORNL 训练 → ORNL 归档"，deadline **17:00**，priority 3。


| 节点              | 类型         | placement（站点）             | 读入                   | 产出                                   |
| --------------- | ---------- | ------------------------- | -------------------- | ------------------------------------ |
| `I0`            | instrument | aps-beamline-8id（anl-aps） | —                    | `raw.h5`，5 TB，09:00 产出（beamtime 已排定） |
| `t1` preprocess | compute    | anl-n01（anl-lcrc）         | `raw.h5`、`calib.dat` | `feat.npz`，**估计** 20 TB              |
| `t2` train      | compute    | ornl-n01（ornl-olcf）       | `feat.npz`、`ref.db`  | `model.ckpt`，50 GB                   |
| `t3` archive    | compute    | ornl-esgf（ornl-olcf）      | `model.ckpt`         | —                                    |


已有副本：`calib.dat` 在 anl-dtn01；`ref.db` 在 anl-dtn01 **和** ornl-esgf。

#### 逐条依赖边判定


| 依赖        | 数据           | 源 → 目的                 | 判定     | 原因                                                      |
| --------- | ------------ | ---------------------- | ------ | ------------------------------------------------------- |
| I0 → t1   | `raw.h5`     | anl-aps → anl-lcrc     | **X1** | 跨站点（走 APS-LCRC）                                         |
| (副本) → t1 | `calib.dat`  | anl-dtn01 → anl-n01    | 不产生    | 同站点 anl-lcrc                                            |
| t1 → t2   | `feat.npz`   | anl-lcrc → ornl-olcf   | **X2** | 跨 domain（ANL → ESnet → ORNL）                            |
| (副本) → t2 | `ref.db`     | 选 ornl-esgf → ornl-n01 | 不产生    | **副本选择**：选 ORNL 本地那份就不用过网；若选 anl-dtn01 会多出一条 1 TB 的跨域传输 |
| t2 → t3   | `model.ckpt` | ornl-n01 → ornl-esgf   | 不产生    | 同站点 ornl-olcf                                           |


5 条依赖边，只产生 2 个 transfer。

#### P1 输出：TransferRequest 集合（窗口尚未填）

```jsonc
[
  { "id": "X1", "workflow_id": "W1", "priority": 3,
    "file": "raw.h5",
    "src": "aps-beamline-8id", "dst": "anl-n01",
    "bytes": 5.0e12,  "is_estimate": false,     // 设备产出量已知
    "window": null,                             // ← P2 填
    "divisible": true,                          // 文件传输，可断点续传
    "min_useful_rate": "10 Gbps",
    "upstream": "I0", "downstream": "t1" },     // 在 DAG 里的位置，P2 用

  { "id": "X2", "workflow_id": "W1", "priority": 3,
    "file": "feat.npz",
    "src": "anl-n01", "dst": "ornl-n01",
    "bytes": 2.0e13,  "is_estimate": true,      // 中间产物，t1 跑完才知道真值
    "window": null,
    "divisible": true,
    "min_useful_rate": "10 Gbps",
    "upstream": "t1", "downstream": "t2" }
]
```

`upstream` / `downstream` 不在 0909 的 TransferRequest 字段里，是 scheduling agent **内部**保留的 DAG 位置（发给 network agent 时可以去掉）。

### 3.2 P2 推导时间窗、分配 slack



#### 推导时间窗：compute 时间怎么进来

**P2 离不开 compute 时间。** transfer 的窗口两端都由相邻 task 决定：

- `earliest_start(X)` = 上游产出数据的时刻 = 上游**就绪 + 排队 + 运行**完
- `latest_finish(X)` = 下游最晚必须就绪的时刻 = 下游**最晚开始 − 排队**

所以每个 compute 节点需要两个量，各带 p50 / p95：


| 量            | 含义                                  | 来源                      |
| ------------ | ----------------------------------- | ----------------------- |
| `queue_wait` | 数据就绪 → 真正开始跑（`startedAt − readyAt`） | 历史 report（§5.1）         |
| `runtime`    | 开始 → 结束（`runtimeInSeconds`）         | 历史 report / `estimates` |


**前向 / 后向用不同分位**：

```
前向（earliest）：用 p50  —— "数据预计什么时候到"，不过早占电路
后向（latest）  ：用 p95  —— "下游最坏情况下最晚要什么时候就绪"，保守
```

> 0914 只写了后向扣 `queue_wait`。前向同样要加上游的排队与运行时间，否则 `earliest_start` 系统性偏早、电路空转。这里补齐。

**还缺一个量：传输自己要多久。** 前后向推导穿过 transfer 节点时需要它的时长，但时长取决于速率，而速率要等 network agent 给 offer 才知道。v1 用**名义时长**：

```
名义时长 = bytes / (路径名义容量 × achievability 系数)
         路径名义容量来自 WfPlatform；系数冷启动取 0.6（§3.4）
```

> 【新增，待定】名义时长是本文补的假设，笔记里没有定义。替代做法是按拓扑序逐个放置：上游 transfer 选定 offer 后，用它的 p95 完成时间重算下游窗口（和 v1 贪心天然契合）。

算法仍是 CPM：拓扑排序 + 两次线性扫描，O(V+E)，**纯确定性，不用 LLM**。

#### 分配 slack：不能让网络独吞

前后向各自算出的窗口，**单看每一个都对，合起来会重复计算余量**。所以要先算整条链的总余量，再显式分给 compute 和各个 transfer（0914 §1）。

```
总余量 = deadline − 按 p50 前向推出的预计完成时刻
compute 预留 = Σ (queue_wait.p95 − p50) + (runtime.p95 − p50)   ← 先给 compute
transfer 可分 = 总余量 − compute 预留                           ← 剩下的才进 transfer 窗口
```

【未定】transfer 之间怎么分。例子里按名义时长比例分，只作示意。

边界：**我们规划 compute 的时间，但不分配 compute 的资源。**

#### 例子 W1 续：填上窗口

**输入的时间估计**（分钟）


| 节点                               | queue_wait p50 / p95 | runtime p50 / p95 | 名义传输时长 |
| -------------------------------- | -------------------- | ----------------- | ------ |
| X1（5 TB，APS-LCRC 100G × 0.6）     | —                    | —                 | 11     |
| t1                               | 10 / 30              | 40 / 60           | —      |
| X2（20 TB 估计，ANL→ORNL 100G × 0.6） | —                    | —                 | 45     |
| t2                               | 20 / 60              | 180 / 210         | —      |
| t3                               | 0 / 0                | 10 / 15           | —      |


**前向（p50）**

```
I0 产出 09:00 → X1 earliest_start 09:00，名义到 09:11
t1 就绪 09:11 → 开始 09:21 → 完成 10:01 → X2 earliest_start 10:01，名义到 10:46
t2 就绪 10:46 → 开始 11:06 → 完成 14:06
t3 就绪 14:06 → 完成 14:16                      预计完成 14:16，deadline 17:00
```

**后向（p95）**

```
t3 最晚完成 17:00 → 最晚开始 16:45
t2 最晚完成 16:45 → 最晚开始 13:15 → 最晚就绪 12:15 → X2 latest_finish 12:15
X2 最晚开始 11:30 → t1 最晚完成 11:30 → 最晚开始 10:30 → 最晚就绪 10:00 → X1 latest_finish 10:00
```

**不分配时的窗口 —— 重复计算**


|     | window         | 宽度  | 扣掉名义时长后的余量 |
| --- | -------------- | --- | ---------- |
| X1  | [09:00, 10:00] | 60  | 49         |
| X2  | [10:01, 12:15] | 134 | 89         |


两者加起来 138 分钟，但真正能给传输用的只有 49 分钟：

```
总余量       = 17:00 − 14:16                    = 164
compute 预留 = t1 (20+20) + t2 (40+30) + t3 (0+5) = 115
transfer 可分 = 164 − 115                        = 49
```

X1 的 49 就是全部 49；X2 的 89 里还含着 t1 的 40 分钟 compute 预留。若 network agent 让 X1 拖到 10:00 才完成、同时又让 X2 用掉自己的余量，两者就在花同一笔钱，t2 的排队预留被吃掉。

**分配后的窗口**（49 按名义时长 11 : 45 分：X1 ≈ 10，X2 ≈ 39）

```
X1  [09:00, 09:21]     09:00 + 名义 11 + 分到的 10
t1  预算到 10:51        09:21 + p50 的 50 + compute 预留 40
X2  [10:01, 12:15]     10:51 + 名义 45 + 分到的 39 = 12:15
```

填进 TransferRequest：

```jsonc
{ "id": "X1", …, "window": { "earliest_start": "09:00", "latest_finish": "09:21" } }
{ "id": "X2", …, "window": { "earliest_start": "10:01", "latest_finish": "12:15" } }
```

读法：

- **X1 被收紧**（10:00 → 09:21）：它原来占着的余量有 39 分钟本该属于 X2。
- **X2 的** `earliest_start` **仍是 10:01**：t1 按 p50 跑完数据就到了。但 10:01–10:51 这段其实是 t1 的 compute 预留，**X2 只有 39 分钟是自己的**。t1 若按 p95 才完成，X2 最早 10:51 开始，仍能在 12:15 前完成。
- **最后发给 network agent 的就是这两行**。`bytes / (latest_finish − earliest_start)` 只是平均速率下界；具体 (start, rate) 的形状由 network agent 在账本上找。
- 每个 transfer 最终的 slack 要等选定 offer 才确定：`slack = latest_finish − predicted_finish.p95`。



#### slack 的双重身份

- **调度自由度**：没有 slack，每个传输都只能"立刻发"，错峰和 counter-offer 都无从谈起。
- **修复预算**：network agent 判断"自己修，还是上报 at_risk"，看的就是 `predicted_finish` 到 `latest_finish` 之间还剩多少（§4.3）。

两种用途抢同一份额度，这就引出 §3.4 的权衡。

### 3.3 P3 构造目标

offer 选择需要一个目标函数。难点不在求解，在于**这个目标函数从哪来**。

#### 为什么只有 priority 不够

priority 是个标量，只能说明"谁先"。调度需要知道"晚多久开始亏、亏得多快"：

```
W_A  训练任务     priority 高   deadline 18:00，缓慢衰减
W_B  Rubin alert  priority 低   10:00 断崖，过点归零
容量只够一个先跑
```


| 方案             | A 损失 | B 损失           | 结果    |
| -------------- | ---- | -------------- | ----- |
| 按 priority，A 先 | 5%   | **100%**（错过断崖） | 差     |
| 让 B 先          | 10%  | 3%             | **好** |


按 priority 排序永远选不到第二种方案。

#### utility 曲线

- **形状**（同一 workflow 晚一点亏多少）有客观来源：观测窗口何时关、gate 阈值（如 WAN overhead ≤ 15%）、下游有多少 GPU 在等。
- **高度**（不同 workflow 之间谁更重要）没有技术答案。所以**每条曲线按自身最大值归一化到 [0,1]，比较相对损失**；priority 作为乘数，只负责跨 workflow 分层。
- **表示**：分段线性、几个控制点，例如 `Rubin: [(now,1),(10:00,1),(10:00+ε,0)]`。

#### utility 曲线的输入：


| 类别        | 例子                 | 对应的曲线形状   |
| --------- | ------------------ | --------- |
| 外部时限      | 观测窗口关闭、下一批数据到来     | 断崖        |
| 结果有效性阈值   | gate、SLA 的硬指标      | 断崖（越过即作废） |
| 等待资源的空转成本 | 下游 GPU、beamtime 在等 | 连续衰减      |


**谁来推**：LLM 读 workflow 描述、SLA、领域惯例，输出一个**人一眼能审的小结构化对象**，再交给确定性求解器。可以做消融实验（LLM 推导 / 手调 / 全部均匀）。

#### 目标的分法（避免多目标互相打架）

```
硬约束：容量不超限                       ← 正确性要求，不是优化目标
硬约束：每个 workflow ≥ 30% fair share
目  标：maximise Σ_i utility_i(completion_time_i)
```

fair share 的分母【倾向】用**账本上分到的 slot·bandwidth 面积**，回应 0908 里"分母没定义"的问题。

### 3.4 P4 问网络、选 offer、admission（对应已有第 10 页）



#### 发需求，不发方案

Scheduling agent 不说"给我 40 Gbps"，而是说"这 5 TB 要在 t1 之后开始、t2 之前到"。`bytes / deadline` 是欠定的：满足它的 (rate, window) 组合有无数个，选哪个取决于别人占了哪些时段，而只有 network agent 看得见容量曲线。

```
TransferRequest: id, workflow_id, priority, src, dst,
                 bytes (+is_estimate), window[earliest_start, latest_finish],
                 divisible, min_useful_rate
QuoteRequest:    bundle[], mode: all_or_nothing | best_subset
```



#### 拿回来的是什么，以及背后的遥测

```
QuoteResponse (per transfer):
  status:  feasible | infeasible | unreachable
  offers:  [ { start, rate_profile, predicted_finish{p50, p95}, qos_class } ]
  binding: { when, blocked_by: own_commitment | foreign_traffic }
```


| 字段                          | 背后的遥测                                        | Scheduling agent 怎么用                                       |
| --------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| `offers[]`（复数）              | 容量账本：SENSE 容量查询（observed 层）减去自己已占的量（own 层）   | 可行前沿，在本地做组合搜索，不用反复往返                                       |
| `predicted_finish{p50,p95}` | achievability model：历史传输中"预约多少 vs 实际跑到多少"的回归 | **p95 越过** `latest_finish` **的 offer 直接排除；slack 按 p95 算**  |
| `binding.blocked_by`        | observed 层与 own 层的差来自谁                       | `own_commitment` → 可以抢占或让路；`foreign_traffic` → 动不了，换时段或换路径 |
| `status: unreachable`       | 容量查询同时算出"没有路"                                | 不是调度问题，是配置问题，直接报给人                                         |




#### 选择在优化什么

**每个 offer 单独看都可行，但只是相对于当前账本。** 选中一个就改写了账本，也决定了后面的传输还剩什么空间。

> 如果整批只有一个 workflow，选哪个 offer 几乎无所谓。**offer 选择的全部价值来自竞争。**


| 选早完成                       | 选晚完成                 |
| -------------------------- | -------------------- |
| slack 留得多，出故障时快回路有预算自修     | slack 用光，一出偏差就升级到慢回路 |
| 占住早期容量，可能挡住后来更紧急的 workflow | 把早期容量让出去             |


例子（T1：50 TB，window [09:00, 15:00]；09:00–12:00 只剩 40 Gbps，12:00 之后有 100 Gbps）：

```
a1  09:00 起 @ 40 Gbps  → 13:47 完成   早开始，有重试余地，但霸占早上 5 小时
a2  12:00 起 @ 100 Gbps → 13:07 完成   完成最早、占用最短，但 12 点前没有任何缓冲
a3  09:00 起 @ 20 Gbps  → 14:34 完成   最省容量，slack 几乎用尽
```

选哪个，取决于别的 workflow 需要什么。这个信息只有 scheduling agent 有。

#### admission 与搜索

```
quote(bundle) → 每个 transfer 若干 offers
本地组合搜索  → 选出一组（如 a2, b1, c3）
hold([...], ttl) → 一个 hold_id        ← 整个 bundle 一起占住（SENSE propagate）
commit(hold_id)                         ← 原子提交（SENSE commit）
```

- workflow admission 是**全有或全无**：一个传输排不进来，整个 workflow 不接纳，其他传输也不应占着资源。
- 跨 workflow 试探时，`hold + TTL` 就是搜索原语：先 hold A 的方案，再 quote B，组合更优就 release A 重放。TTL 保证失败的试探不留下垃圾预留。
- **【已定】v1 用优先级序贪心，不回溯**；升级到回溯或 MILP 时协议不用改。停止规则：时间预算（p50 < 200 ms）、连续 N 轮无改进、轮次上限。
- **【已定】Phase 1 是批量调度**（一组预先给定的 workflow）；在线到达留给 Phase 2。



### 3.5 P5 执行计划交回 WMS

```
control plane：Network agent ──ServiceIntent──▶ SENSE-O        预约电路
data plane：   WMS ──Globus / GridFTP / Rucio──▶ 实际搬字节
```

```
ExecutionPlan:
  planVersion
  taskSchedule[]      { task_id, suggested_start }                        建议
  transferWindows[]   { transfer_id, start, rate_profile,
                        predicted_finish{p50,p95} }                       已预约的事实
  endpointBindings[]  { transfer_id, src_uri, dst_uri, vlan, interface }  技术必需
```


| 部分                 | 性质     | WMS 不遵守的后果          |
| ------------------ | ------ | ------------------- |
| `taskSchedule`     | 建议     | 可以说"做不到"，agent 重新规划 |
| `transferWindows`  | 已预约的事实 | 浪费自己的预约             |
| `endpointBindings` | 技术上必需  | 传输不落在电路上，走默认路由，预约白做 |


**这份计划也是运行期的对照基准**：它在 Runtime DAG 里是每个节点的 `plan`，后面所有偏差都相对它来算。

---



## 4. 运行期

这一节是新增 slides 的核心。4.1 是 R1–R4 共用的底座：遥测怎么进来、怎么变成受影响集合；4.2–4.5 是四种具体情况。

### 4.1 遥测怎么进到 scheduling agent（R1–R4 共用）



#### 原则：按"真相源"分流，scheduling agent 只收事件和结论


| 事实                     | 真相源（谁拥有、谁能据此行动）                    | 到 scheduling agent 时的形态                                        |
| ---------------------- | ---------------------------------- | -------------------------------------------------------------- |
| task 就绪 / 开始 / 完成、运行时长 | WMS（如 `pegasus-monitord`）          | 事件：`readyAt` / `startedAt` / `runtimeInSeconds`                |
| 中间产物实际大小、副本落点、分支走向     | WMS                                | 事件：`refine`                                                    |
| 传输完成、字节数、耗时、流数         | WMS 调用的搬运工具（Globus / Rucio）        | 事件：`transfers[]` 记录（带 `commitmentRef`）                         |
| 链路容量下降、吞吐退化、电路状态       | Network agent（从 SENSE / SiteRM 拉取） | **结论**：`repaired` / `at_risk`，附 `cause` 和新的 `predicted_finish` |
| "本该发生却没发生"             | 没有来源                               | Runtime DAG 的**看门狗**自己判定                                       |


为什么不把原始网络指标也送到 scheduling agent：

- 它没有能力解读：利用率 80% 对某个 commitment 意味着什么，得结合账本和 achievability model 才知道，而这两样都在 network agent 里。
- **集中采集不等于关联**。关联靠键链（`commitmentRef` → transfer → DAG 节点），谁持有键，谁才能做关联。
- 汇总到 WMS 也不合适（KK 0914 §4 的建议）：WMS 是别人的现成系统，没有 commitment 那一半的键，而且会打破"只有 network agent 碰网络侧"的边界。



#### 关联点：Workflow Runtime DAG

KK 的问题是"遥测分流之后，谁知道整个 workflow 发生了什么"。答案是一张**运行时 DAG**，每个 workflow 一张。它是全系统唯一的跨组件关联点。

**是 DAG，但不只是 DAG**：

- 节点分三类：`instrument` / `compute` / `transfer`。传输和设备也是一等节点；同站点内的文件流动不单独成节点。
- 每个节点挂**三份时间**：


|            | 来自                    | 用途                      |
| ---------- | --------------------- | ----------------------- |
| `plan`     | 执行计划（§3.5）            | 对照基准                    |
| `actual`   | Telemetry Service 的事件 | 已发生的事实，填上后不再预测          |
| `forecast` | 传播计算                  | 未发生节点的当前最佳估计（p50 / p95） |


- 另外还挂 `slack{allocated, remaining}`、`status`、`cause`、`commitmentRef`（与 network agent 关联的键）。
- **版本化**：每次重排 `planVersion + 1`，旧版本保留，用于事后解释和长回路回放。

```jsonc
{ "id": "xfer:input.txt:aps-beamline-8id>anl-n01", "kind": "transfer",
  "commitmentRef": "cmt-7f3a91",
  "window":   { "earliestStart": "…08:31Z", "latestFinish": "…09:00Z" },
  "plan":     { "start": "…08:31Z", "finish": "…09:00Z" },
  "actual":   { "startedAt": "…08:31:12Z", "finishedAt": null },
  "forecast": { "finish": { "p50": "…09:05Z", "p95": "…09:12Z" } },
  "slack":    { "allocated": 600, "remaining": -720 },
  "status": "running", "cause": "network" }
```

**它不存什么**：不存原始遥测（在 Telemetry Service）；不存网络资源耦合（两个 workflow 共用一条路径不是 DAG 边，那在 network agent 的账本里）。

> 【已定】按 Overview 图，Runtime DAG 放在 scheduling agent 内部（0914 称之为"新增关联实体"，当时未给归属）。



#### 遥测 → 决策：同一个传播算法

**运行期的传播和规划期的 P2 是同一个算法**：前向推导。区别只在于，已有 `actual` 的节点用实际值，其余节点用 `forecast`。

```
遥测事件到达
   │
   ▼
写入节点 actual（或看门狗判定超时 → 更新 forecast）
   │
   ▼
沿 DAG 前向传播 → 重算下游每个节点的 forecast 与 slack.remaining
   │
   ├─ remaining ≥ 0（按 p95）  → 只更新账，不动计划          ← 避免误伤
   └─ remaining < 0            → 进入受影响集合 → §4.5 重排
```

**受影响集合** = `slack.remaining < 0` 的节点，加上从它们沿边可达、且 `forecast.p95` 越过自身窗口的节点。其他节点一律不动。

`cause` 用来区分根因和连带影响：`network` / `end_host` / `foreign_traffic` 来自 network agent，`compute` / `queue` 来自看门狗，`upstream` 在传播时自动标记。重排时据此判断：该动的是出问题的那一条，还是只需要把下游整体平移。

**容差阈值**：偏差在阈值以内只更新账，不重新规划，防止计划反复抖动、WMS 跟不上。【倾向】v1 用固定百分比，做成可替换的 policy 接口；是否随剩余 slack 自适应留给 Tier 3。

### 4.2 R1 估计被事实替换（refine）

workflow 是**渐进展开**的：提交时的估计，到中途就不准了。没有 refine，agent 会拿着过期的猜测一直规划到底，等发现不对时 slack 已经用完。


| 事实              | 触发时机         | 对计划的影响                                | 能换来什么                                      |
| --------------- | ------------ | ------------------------------------- | ------------------------------------------ |
| 中间产物**实际大小**    | 上游 task 写完文件 | `is_estimate` 被真值替换                   | 估大了：**释放多占的容量**给别人；估小了：**现在就预警**，还有时间重排或协商 |
| task **实际完成时间** | task 结束      | 下游所有 transfer 的 `earliest_start` 整体平移 | **平移下游**，避免电路按时开着、数据还没产出                   |
| 副本**实际落点**      | 文件落盘         | 后续传输的 `src` 变了                        | 改变传输本身                                     |
| 分支**实际走向**      | 条件判定         | 有些 transfer 根本不需要了                    | release 对应预留                               |


`refine` **和** `report` **方向相反**：`refine` 是前瞻的，改变还没执行的计划；`report` 是回顾的，记录已经发生的事，喂给长回路。同一个事实（比如 task 完成时间）通常两边都要走一遍。

> 口径变化：0909 中 `refine` / `report` 是 WMS 直接调 scheduling agent 的两个动词；0914 引入 Telemetry Service + Runtime DAG 之后，事实先落进 Runtime DAG 再触发传播。两种写法语义一致，slides 上建议按 0914 的画法。



### 4.3 R2 网络异常

**Network agent 那一侧先做的事**（scheduling agent 需要知道，但不参与）：

1. **先扫描，再逐条判断**。容量（observed）下降时，重算该路径上**所有**自己已占的记录，包括正在跑的和还没开始的。
2. 每条按自己的窗口判断：
  - 还能在 `latest_finish` 前完成 → **自修**：吃自己的 slack 往后挪（只是账本操作）、`modify` 提速、换到电路池里的另一条电路。
  - 赶不上 → 上报 `at_risk`。
3. **成批上报**。一次故障通常同时产生几条 `repaired` 和几条 `at_risk`，一起发上来，让 scheduler 一次性看到全貌。

**上行消息**（0914 §3 定义）：

```
repaired / at_risk:
  commitmentRef
  predicted_finish { p50, p95 }      ← repaired 也要带：slack 被吃掉了，scheduler 得知道
  cause: end_host | network | foreign_traffic | unknown
  affected_window
```

> 0909 把"加并行流 / 调传输参数"列为 network agent 的自修手段；0914 更正：这是数据面参数，归 WMS 的搬运工具控制，network agent 改不了。**只能由 scheduling agent 写进更新后的执行计划，交给 WMS 去执行。**

**Network agent 看不到、只有 scheduling agent 能补上的三件事**：

1. **连带影响**：上游 T1 晚了 → 下游 task 晚开始 → 下游 T2 也得挪。但 T2 走的是一条健康的路，network agent 根本不会标出它。
2. **哪些** `at_risk` **属于同一条链**：同一个 workflow 的上下游应该一起重排，而不是当作两件独立的事。
3. `repaired` **的隐患**：自修吃掉了 slack，窗口内没问题；但如果那份 slack 本来是留给下游 compute 排队的（§3.2），下游照样会破。

这三件事都靠 §4.1 的传播发现。

**关联链**：故障 → (src, dst) / circuit → commitments → `commitmentRef` → transfer 节点 → 沿 DAG → 下游 task / transfer → deadline。

**必须诚实承认的信息边界**：SENSE 不给 link 级拓扑，账本只能按 (src, dst) 建。两条路径如果共用一条看不见的瓶颈链路，就会漏报或误报。缓解手段是 `ProbeResult.path` 和 `WfPlatform.routes`。

### 4.4 R3 计算超时

与网络故障对称，但有两处本质不同：**检测靠"该来的事件没来"**；**应对主要是挪网络预约，而不是修计算**。


| 类型   | 判据                                                            | `cause`   |
| ---- | ------------------------------------------------------------- | --------- |
| 排队超时 | 有 `readyAt`，`now > readyAt + queue_wait.p95`，仍无 `startedAt`   | `queue`   |
| 运行超时 | 有 `startedAt`，`now > startedAt + runtime.p95`，仍无 `finishedAt` | `compute` |


- `queue_wait` 和 `runtime` 的分布来自长回路（§5.1）。**看门狗的阈值本身就是历史遥测。**
- forecast 更新：有进度信号就按进度外推；没有就用 v1 规则 `now + (runtime.p95 − runtime.p50)`，每个周期重新评估。
- 盲点：没有进度信号，就分不清"慢但活着"和"已经挂了"。需要 schema 补 `tasks[].status`，可选 `tasks[].progress` 或心跳【待核对，需要 Rafael】。



#### 与网络异常（R2）对比


|         | 网络故障                                       | 计算超时                    |
| ------- | ------------------------------------------ | ----------------------- |
| 谁先发现    | Network agent（指标 / 探测）                     | Runtime DAG 看门狗         |
| 检测依据    | 有信号：容量下降、吞吐偏低                              | **无信号**：事件缺席            |
| 第一步     | Network agent 扫描并尝试自修                      | 直接传播，没有自修阶段             |
| 主要应对    | 修路径、换电路、重排                                 | **挪下游网络预约**，必要时提速把时间补回来 |
| `cause` | `network` / `end_host` / `foreign_traffic` | `compute` / `queue`     |




### 4.5 R4 重排决策与同步



#### 在受影响集合上做什么

**快回路只动自己，慢回路要动别人。** 慢回路的决策权必须在 scheduling agent，因为只有它有跨 workflow 的视图。


| 决定               | 适用                                          | 协议动作                                                 |
| ---------------- | ------------------------------------------- | ---------------------------------------------------- |
| 接受更晚完成           | utility 曲线允许                                | 对原 commitment quote 新窗口 → `modify`                   |
| **用网络补回计算耽误的时间** | 计算超时，平移后越过 `latest_finish`，但换更快的 offer 能赶回来 | quote 更高速率 → `modify`                                |
| 平移并释放            | 计算超时，平移后仍在窗口内                               | `modify` 往后挪，**把前面空出的时段还给账本**                        |
| 重排下游             | 连带影响（健康路径上的 T2）                             | 以平移后的窗口重新 quote → `modify`                           |
| 抢占低优先级           | `binding.blocked_by = own_commitment`       | 为自己 `hold` 新放置 → 被抢者 `modify` / `release` → `commit` |
| 换副本源             | 另一副本走另一条路                                   | 新 transfer `quote → hold → commit`，成功后 `release` 旧的  |
| 放弃               | 以上都不行                                       | `release`，通知人并给 counter-offer                        |


取舍依据：跨 workflow 比较 `priority × 相对 utility 损失`（§3.3）。

**【倾向】v1 用固定降级阶梯**：吃自己的 slack 往后挪 → 降速 → 抢占更低优先级 → 通知人。做成可替换的 policy 接口，之后再量化比较换成 LLM 是否更好。

**演示点**："用网络补回计算耽误的时间"说明计算和网络在同一条时间线上，**一侧的延误可以由另一侧的余量吸收**。这直接回应 KK 的问题："scheduler 必须同时考虑 compute 和 transfer"。

#### 两条纪律

- **先占新，再放旧**（make-before-break）：新方案 `hold` 成功 → release 旧的 → `commit`。如果先 release，释放的那一刻容量可能被别人拿走，最后两头落空。
- `at_risk` **要有响应期限**：scheduler 迟迟不决策时，network agent 不能无限等。【未定】默认行为，例如超时后按 best-effort 继续传，并把该承诺标记为违约。



#### 同步

- **推送新执行计划给 WMS**（`planVersion + 1`）：新的 `transferWindows`、可能变了的 `endpointBindings`、新的 `taskSchedule`，以及给 WMS 的建议（加并行流、换节点重跑，WMS 自己决定）。
- 需要时通过 Tier 2 接口向人解释。**解释是渲染，不是推理**：只读 Commitment Ledger、`binding`、`cause`，不重新推导数字。



#### 完整流程（网络故障为例）

```
① Network agent    扫描受影响路径上的所有 commitment → 能修的修 → 成批发 repaired / at_risk
② Runtime DAG  用 commitmentRef 挂到 DAG 节点 → 叠加实际运行状态 → 沿依赖传播 p95
                   → 输出受影响集合（直接 + 连带），以及哪些 deadline 会破
③ Scheduling agent 在受影响集合上按 utility / priority 取舍
④ 协议             quote → hold → release 旧的 → commit；健康路径上的下游 transfer 也在此 modify
⑤ WMS              收到更新后的执行计划
```

---



## 5. 跨 run



### 5.1 L1 执行事实回流：学习与记账



#### 两个 agent 各自学一样东西


|                      | 学什么                       | 需要的历史                               |
| -------------------- | ------------------------- | ----------------------------------- |
| Network agent        | `reservable → achievable` | 预约多少 vs 实际跑到多少                      |
| **Scheduling agent** | `估计 → 实际`                 | **估计的 runtime / 数据量 / 排队时间 vs 实际值** |




#### Scheduling agent 怎么用 task 部分


| 用途             | 怎么算                                                                                                                           | 改善的是哪一步                      |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| 训练 `estimates` | `runtimeInSeconds` → `taskRuntimeSeconds` 分布；`files[].sizeInBytes` → `fileSizeBytes`；`files[].locations` → `existingReplicas` | P1、P2                        |
| 学排队时间          | `startedAt − readyAt` 的分布 → `queue_wait`                                                                                      | P2 前后向推导（§3.2）、R3 看门狗阈值      |
| 校准自己计划的现实性     | `startedAt − suggested_start` 的分布：系统性偏晚，说明计划没考虑 GPU 排队                                                                        | P5 的 `taskSchedule` 要留余量     |
| 判断 WMS 依从度     | 同一分布的长期趋势                                                                                                                     | 某个 WMS 长期不遵守，就不再基于建议启动时间紧凑规划 |


`readyAt` 与 `startedAt` 的差**把"等数据"和"等计算资源"分开了**。前者是我们的责任，后者不是，这决定偏差该归咎于谁。

#### Scheduling agent 怎么用 network 部分（转发之前自己也用）

- **承诺兑现记账**：实际完成时刻 vs 计划里的 `predicted_finish`。这是 demo 里"承诺 vs 兑现"那张图的数据源。
- **fairness 记账**：每个 workflow 实际占到的 slot·bandwidth 面积，作为 fair share 的分母。
- **转发给 network agent**：`transfer_outcome` 贴上 `commitmentRef`。network agent 靠它把自己账本里的 `reserved` 和报上来的 `achieved` 配成一对，训练 achievability model，进而让下一次 offer 的 p95 更准（回到 §3.4）。



#### 闭环

```
历次 execution（task 时间、文件大小、排队）
        │  Tier 2.5：估计模型
        ▼
WfCampaign.estimates + queue_wait 分布
        │  P2 前后向推导
        ▼
transfer 时间窗 + slack ──quote──▶ offers（p95 来自 network agent 的 achievability）
        │  执行
        ▼
report 回写 ──────────────────────────────────────▶ 回到顶部
```

时间尺度是**跨 run** 的：不影响当前这次执行，只让下一次规划更准。

`report` **不新造 schema**：它就是 `WfFormat.execution` 的增量切片，按主键合并。需要新增四项：`transfers[].commitmentRef`、`transfers[].status`（completed | failed | partial，避免幸存者偏差，也是 gate 4 success rate 的分母）、`files[].sizeInBytes`，以及增量上报约定（`reportedAt`）。

---



## 6. 汇总：遥测 → 决策对照表

这张表适合单独做一页 slide。


| 遥测 / 事实                                      | 从哪来                                   | 哪个阶段用   | 驱动 scheduling agent 的哪个决策           |
| -------------------------------------------- | ------------------------------------- | ------- | ----------------------------------- |
| 历史 task runtime                              | WMS report（跨 run）                     | P2      | 前后向推导的时长 → slack 大小                 |
| 历史排队时间 `startedAt − readyAt`                 | WMS report（跨 run）                     | P2、R3   | 给 compute 留多少 slack；看门狗阈值           |
| 历史文件大小、副本位置                                  | WMS report（跨 run）                     | P1、P2   | 拆解结果；传输量估计                          |
| 预约 vs 实际吞吐（经 network agent 校准）               | 历次 `transfer_outcome` + SENSE / probe | P4      | offer 的 p95 → 排除哪些 offer、slack 按多少算 |
| 当前容量曲线、`blocked_by`                          | SENSE 容量查询（经 network agent）           | P4、R4   | 可行前沿；能不能抢占                          |
| 实际文件大小 / 分支 / 落点                             | WMS 运行时事件                             | R1      | 释放容量、提前预警、改传输                       |
| task 实际完成时间                                  | WMS 运行时事件                             | R1      | 下游窗口平移                              |
| `repaired` / `at_risk` + `cause` + 新 p95     | Network agent                         | R2 → R4 | 受影响集合 → 重排方式                        |
| 事件缺席（超时）                                     | Runtime DAG 看门狗                       | R3 → R4 | 挪下游预约 / 提速补时                        |
| `startedAt − suggested_start`                | WMS report（跨 run）                     | P5      | `taskSchedule` 留多少余量；是否信任该 WMS      |
| 实际完成 vs `predicted_finish`、slot·bandwidth 面积 | WMS report（跨 run）                     | 评估      | 兑现率、fairness                        |


---



