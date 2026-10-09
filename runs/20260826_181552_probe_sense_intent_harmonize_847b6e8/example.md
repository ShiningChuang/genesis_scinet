# SENSE-O harmonization examples

> 本文件集中保存 Exp2 的具体映射例子。主调研结论见 `[sense_o_intent_harmonization.md](sense_o_intent_harmonization.md)`。

## Example 1：Bandwidth capacity request 与 Real throughput 的完整闭环

> WfPlatform.capacityGbps 是可用能力，SENSE bandwidth.capacity 是本次申请值，Real throughput 是传输结束后的观测结果。Real throughput 不应放进建链 request；它由实际 bytes / duration 计算并写入 WfFormat execution。

本例同时表达三个不同阶段的带宽：


| 阶段  | 数值       | 表达位置                                    | 含义                    |
| --- | -------- | --------------------------------------- | --------------------- |
| 规划前 | 100 Gbps | `WfPlatform.links.capacityGbps`         | 候选链路最多能提供的能力          |
| 建链前 | 80 Gbps  | SENSE-O `bandwidth.capacity = "80000"`  | 本次 intent 向网络提交的带宽参数  |
| 传输后 | 72 Gbps  | WfFormat execution 的 `bytes / duration` | 实际测得的 Real throughput |


三者不能混用：platform capacity 用于可行性检查，SENSE capacity 用于发出网络请求，Real throughput 用于执行后判断 science-SLA 是否真正满足。

先只看 APS → ANL 一段。三个 schema 各自提供不同信息，不能把 `WfPlatform.links.capacityGbps` 原样当成一次 workflow 的申请值。

### 第一步：WfFormat 描述要搬什么

```yaml
specification:
  files:
    - id: detector-output
      sizeBytes: 36000000000000  # 36 TB（十进制）
      origin:
        kind: instrument
        ref: aps_detector        # role，不是网络地址
      destination:
        kind: compute
        ref: anl_compute         # role，不是网络地址
```



### 第二步：WfPlatform 描述网络最多能提供什么

```yaml
links:
  - id: aps-anl-link
    source: aps-edge
    destination: anl-edge
    capacityGbps: 100
```

这里的 `100 Gbps` 是 platform capability，用来做可行性检查；它不是“这次传输要预留 100 Gbps”。

### 第三步：WfCampaign 描述这次提交的绑定与 SLA

```yaml
bindings:
  aps_detector: aps-beamline-8id  # role → WfPlatform node id
  anl_compute: anl-n01            # role → WfPlatform node id

submissions:
  - id: submission-17
    route: [aps-anl-link]
    sla:
      fileDeadlines:
        detector-output: "2026-08-27T02:30:00Z"
```

假设 adapter 开始处理时，距离 deadline 正好还有 1 小时。忽略协议开销的最小理论速率为：

```text
requiredGbps
  = sizeBytes × 8 / remainingSeconds / 1e9
  = 36e12 × 8 / 3600 / 1e9
  = 80 Gbps
```

adapter 再用 WfPlatform 做可行性检查：

```text
80 Gbps required <= 100 Gbps available  →  此 route 在容量上可行
```

实际系统还应考虑协议效率、并发流和安全余量；这些属于 adapter policy，不能把未经决定的余量硬编码进 schema。

### 第四步：adapter 生成 SENSE-O request

SENSE-O 2.0.4 的 `bandwidth.capacity` 单位是 Mbps，因此 adapter 把 `80 Gbps` 转成字符串 `"80000"`：

```json
{
  "service": "dnc",
  "alias": "submission-17-detector-output",
  "data": {
    "type": "Multi-Path P2P VLAN",
    "connections": [
      {
        "name": "aps-to-anl",
        "terminals": [
          {
            "name": "aps",
            "uri": "urn:ogf:network:example:aps:port1",
            "vlan_tag": "any"
          },
          {
            "name": "anl",
            "uri": "urn:ogf:network:example:anl:port7",
            "vlan_tag": "any"
          }
        ],
        "bandwidth": {
          "capacity": "80000",
          "qos_class": "guaranteedCapped"
        }
      }
    ]
  }
}
```

请求流程：

1. `GET /instance` 取得 `siUUID`；
2. `POST /instance/{siUUID}`，body 为上面的 `ServiceIntent`；
3. response 中保存 `service_uuid` 和 `intent_uuid`，供 WfCampaign/execution 关联与后续 read-back。



### 第五步：将实际传输写入 WfFormat execution

SENSE-O request 中的 `bandwidth.capacity: "80000"` 只是建链前提交的参数。Real throughput 必须等传输结束后，用实际观测到的 `bytes` 和 `duration` 计算。

**这两个值默认不从 SENSE-O Intent API 2.0.4 获取。** 该版本没有返回 per-transfer `bytes`、`duration` 或 throughput 的 GET endpoint：

- `GET /instance/{siUUID}/verify` 返回 service model addition/reduction 的验证结果，不返回数据传输统计；
- `GET /logging/logs/{siUUID}` 返回 SENSE-O 服务端日志，不是稳定、结构化的 transfer metrics 接口；
- OpenAPI 虽声明 `monitor` tag，但没有任何 path 使用该 tag。

本例中的 per-file 观测应优先来自真正执行文件传输的系统，例如 workflow runtime/data mover：


| 观测值                     | 建议来源                                | 表示什么                                 |
| ----------------------- | ----------------------------------- | ------------------------------------ |
| `bytes`                 | data mover 的 transfer record        | 该文件实际传输了多少 bytes                     |
| `startedAt` / `endedAt` | data mover 或 workflow runtime 的事件时间 | 该次文件传输的实际起止时间                        |
| `durationSeconds`       | `endedAt - startedAt`               | 该次文件传输持续多久                           |
| Real throughput         | `bytes × 8 / durationSeconds`       | application-level end-to-end goodput |


若 SiteRM 或其他 SENSE telemetry 另行提供端口计数器、链路利用率等数据，可以作为网络侧解释证据；但它不属于当前审计的 SENSE-O Intent API 2.0.4，且 link utilization 也不等同于某一个文件的 end-to-end throughput。

### 谁执行文件传输？

SENSE 主要负责建立网络服务，但通常不负责“把文件从 A 搬到 B”。

真正执行文件传输的是：

- DTN 上的 transfer service；
- Globus、FTS、XRootD；
- TaskVine worker/runtime；
- 或 workflow 自己启动的传输程序。

这些组件运行在端点上，不是交换机或路由器内部。

### WfFormat 应该保存在哪里？

建议保存在 workflow/provenance control plane：

```
逻辑上属于用户/workflow 一侧
```

它可以部署在实验室服务器或共享 workflow service 上，不一定在用户笔记本上，但不应由网络内部系统维护 canonical copy。

WfFormat 不需要维护在网络内部。建议由 workflow provenance collector 保存权威副本并回写 execution：

原因是网络系统通常不知道：

- 某个 flow 对应哪个文件；
- 文件属于哪个 task；
- workflow deadline 是什么；
- campaign 为什么选择这条 route。

网络只需要提供网络服务和获准暴露的观测证据。

如果 data mover （ Globus、FTS、XRootD、TaskVine）不提供 job 级 `bytes` 和时间，那么 Real throughput 就应记为 unavailable，不能用预计文件大小或端口总流量冒充实际 per-file throughput。

```text
transfer service on DTN/end host
    └── 只向有权限的 workflow controller 返回本次 transfer job 的
        bytes、startedAt、endedAt、status
                ↓
workflow provenance collector
    └── 更新用户侧 WfFormat.execution
```

终端用户不需要拥有 DTN 登录权限或全网 telemetry 读取权限；controller 可以使用 service account、delegated credential 或 transfer-job token，只读取该用户/该 workflow 的 job record。如果执行系统不提供这些数据，本例中的 Real throughput 就无法计算，必须标为 unavailable，不能用预计文件大小或端口总计数替代。

假设实际传输记录为：

```yaml
execution:
  campaignRef: campaign-42
  transfers:
    - file: detector-output
      source: aps-beamline-8id
      destination: anl-n01
      bytes: 36000000000000
      startedAt: "2026-08-27T01:30:00Z"
      endedAt: "2026-08-27T02:36:40Z"
      durationSeconds: 4000
```

按照 PPT 的口径，Real throughput 由 execution 中的 `bytes / duration` 得出：

```text
realThroughputGbps
  = bytes × 8 / durationSeconds / 1e9
  = 36e12 × 8 / 4000 / 1e9
  = 72 Gbps
```

adapter 另行保存本次 campaign/submission 与 SENSE 对象的关联，避免在尚未定稿的 WfFormat 中擅自新增字段：

```text
campaign-42 / submission-17
    → service_uuid: network-service-123
    → intent_uuid: intent-456
```



### 推荐的数据流

```
1. 用户编写 WfFormat.specification
2. workflow controller 创建 WfCampaign
3. adapter 调 SENSE-O 建立网络
4. workflow controller 调 data mover 执行传输
5. data mover 返回本次 job 的 bytes 和时间
6. provenance collector 写 WfFormat.execution
```



### 第六步：用 Real throughput 判断 science-SLA

本例的 file deadline 是 `02:30:00Z`，实际结束时间是 `02:36:40Z`：

```text
platform capacity            = 100 Gbps
requested bandwidth parameter = 80 Gbps
real throughput               = 72 Gbps
deadline miss                 = 400 s
science-SLA                   = 未满足
```

这是客观结果，但不能仅凭 `72 < 80` 断言原因是网络。差异也可能来自发送/接收端、存储、传输协议、并发流，或 SENSE `qos_class` 对 `capacity` 的实际语义。若要定位原因，需要另外的 telemetry 或对照实验。

SENSE-O Intent API 2.0.4 本身没有 typed throughput response，所以 Real throughput 不是从 `GET /intent` 或其他现有 GET 读出来的；它来自 workflow runtime/data mover 的实际传输记录，再写回 WfFormat execution。

### 字段映射总结

```text
WfFormat.sizeBytes + WfCampaign.fileDeadline
                  ↓ adapter 计算
SENSE-O data.connections[*].bandwidth.capacity（Mbps）

WfCampaign.bindings[role]
                  ↓ adapter 解析
SENSE-O data.connections[*].terminals[*].uri

data mover / DTN telemetry: bytes + duration
                  ↓ 执行后计算
WfFormat.execution.transfers 中的 Real throughput
```



### 这个例子暴露出的接口问题

`guaranteedCapped` 在 OpenAPI 中只有枚举名，没有解释它是否保证达到 `capacity`。而 `capacity` 的字段描述是 bandwidth **limit**。因此这个 request 可以明确表达“80,000 Mbps 这个带宽参数”，却尚不能仅凭 2.0.4 schema 证明网络承诺提供至少 80 Gbps。需要向 SENSE 团队确认 QoS 语义，或由实际 provisioning/verification 结果验证。

另外，OpenAPI 对 `ServiceIntent.data` 与 `DNCSchema` 的嵌套定义存在疑点；上例采用官方 workflow example 使用的 `data.connections[...]` 路径表示概念映射，正式调用前仍需用可运行 profile/manifest 核对最终 POST body。

## Example 2：同一 transfer 的三种 latency

本例完全复用 Example 1 的文件、endpoint bindings、`aps-anl-link`、file deadline、SENSE instance 和 transfer record，只描述 latency 新增部分。

### 新增一：WfPlatform 记录 Link latency

在 Example 1 的 `aps-anl-link` 上新增 PPT 定义的 percentile distribution：

```yaml
links:
  - id: aps-anl-link
    # source、destination、capacityGbps 复用 Example 1
    latencyMs:
      p50: 2.0
      p95: 2.6
      p99: 7.1
```

这是规划前的平台基线，回答“候选链路通常有多大 latency”。它不是本次 workflow 的申请值，也不是本次 transfer 的实际观测值。

### 新增二：由既有 file deadline 推导 Required latency

WfCampaign 不新增 `requiredLatencyMs`。继续复用 Example 1 已有的：

```yaml
sla:
  fileDeadlines:
    detector-output: "2026-08-27T02:30:00Z"
```

adapter/scheduler 把文件大小、剩余时间、所需吞吐、传输协议参数和 WfPlatform latency baseline 输入一个经过校准的 transfer performance model：

```text
predictedDuration = M(
    bytes = 36 TB,
    requestedBandwidth = 80 Gbps,
    RTT,
    protocol/window/parallelism/loss
)

要求：predictedDuration <= 3600 s
反解：required RTT p95 <= 5.0 ms   # 本例假设的模型输出
```

这里 `5.0 ms` 是 adapter 的派生决策，不是新的 source-of-truth schema 字段。PPT 说 required latency 可由 `fileDeadlines` 决定；落实到系统时，deadline 提供时间约束，但不能脱离 bytes、protocol/window、parallelism 和 loss 单独算出 RTT 门槛。

### 新增三：SENSE-O request 只能间接表达 latency 选择

SENSE-O Intent API 2.0.4 的 `Connection` 没有 `latency` 或 `maxLatencyMs` 字段，因此下面这种直接请求是无效的：

```json
{
  "maxLatencyMs": "5.0"
}
```

如果 WfPlatform/discovery 已知某个 SENSE Path URI 满足该门槛，adapter 可以复用现有 `path_tprofile`，在 Example 1 的同一个 connection 中只新增：

```json
{
  "path_tprofile": {
    "inclusion_list": [
      {"uri": "urn:ogf:network:example:path:aps-anl-low-latency"}
    ],
    "exclusion_list": []
  }
}
```

这表示“选择已知的低延迟路径”，不是“向 SENSE 声明并保证 RTT ≤ 5 ms”。如果没有预先测量并映射到 Path URI 的候选路径，2.0.4 就无法表达这个 latency requirement；这才是当前的真正候选缺口。

### 新增四：WfFormat execution 记录 Real latency

传输执行后，只在 Example 1 的同一条 `execution.transfers[]` 记录上新增：

```yaml
rttMs:
  p50: 3.1
  p95: 4.4
  p99: 9.8
```

完整对象不再重复。`rttMs` 应来自本次 transfer 的端点测量、data mover/DTN instrumentation，或能与该 transfer 可靠关联的 telemetry；SENSE-O Intent API 2.0.4 没有返回该字段的 GET endpoint。

### Latency 判定

使用相同 percentile 和相同测量语义比较：

```text
required RTT p95 = 5.0 ms   # adapter 从 deadline + performance model 派生
real RTT p95     = 4.4 ms   # execution 实测
latency target   = 满足
```

但 Example 1 的 Real throughput 是 72 Gbps，文件仍晚于 deadline 400 秒。因此本例只能得出：latency target 满足，但整体 science-SLA 未满足；不能把 deadline miss 归因于 latency。

### 三种 latency 的字段归属


| Latency          | 表达位置                                                       | 生命周期    | 是否传给 SENSE-O 2.0.4      |
| ---------------- | ---------------------------------------------------------- | ------- | ----------------------- |
| Link latency     | `WfPlatform.links[].latencyMs`                             | 规划前平台基线 | 不直接传；可用于选择 Path URI     |
| Required latency | `WfCampaign.sla.fileDeadlines` + adapter performance model | 建链前派生约束 | 无直接字段；只能通过已知路径间接表达      |
| Real latency     | `WfFormat.execution.transfers[].rttMs`                     | 传输后观测   | 不是从当前 Intent API GET 获得 |




## Example 3：同一 workflow 的两层 SLA

本例继续复用 Example 1 的 `detector-output`、APS → ANL transfer、bindings、route、file deadline 和 SENSE request；只增加 PPT 中 SLA 尚未展示的部分。

### 新增一：WfFormat 只保存 application-intrinsic constraint

假设该 workflow 处理周期性到达的仪器 batch，并且每个 batch 必须在下一批到达前完成。这个要求换到另一台机器或另一条网络仍然成立，因此新增到 WfFormat specification：

```yaml
specification:
  # files 等其他内容复用 Example 1
  tasks:
    - id: analyze-output

  constraints:
    - type: periodicDeadline
      scope: workflow
      periodSeconds: 7200
```

`periodSeconds: 7200` 表示下一批数据每 2 小时到达，本 workflow 必须在下一批到达前完成。它描述应用本身，不描述本次在哪个平台运行，也不直接传给 SENSE-O。

### 新增二：WfCampaign 保存本次 submission 的 SLA

在 Example 1 的 `submission-17` 上补齐 PPT 定义的 per-submission SLA；已有 `fileDeadlines.detector-output` 原样复用：

```yaml
submissions:
  - id: submission-17
    at: "2026-08-27T01:30:00Z"
    workflowRef: detector-pipeline-v1
    # bindings、placement、route 复用 Example 1
    sla:
      deadline: "2026-08-27T03:00:00Z"
      priority: 3
      taskDeadlines:
        analyze-output: "2026-08-27T02:50:00Z"
      fileDeadlines:
        detector-output: "2026-08-27T02:30:00Z"
```

四个字段的含义不同：


| 字段              | 约束对象                      | 本例语义                                  |
| --------------- | ------------------------- | ------------------------------------- |
| `deadline`      | 整个 submission，包含最终 egress | 本次运行必须在 `03:00` 前全部完成                 |
| `priority`      | 本次 submission 的调度优先级      | 值为 `3`；数字大小的排序语义仍需由本组 policy 定义       |
| `taskDeadlines` | 指定 task                   | `analyze-output` 必须在 `02:50` 前完成      |
| `fileDeadlines` | 指定文件的数据流                  | `detector-output` 必须在 `02:30` 前到达目标位置 |


同一个 `detector-pipeline-v1` 下次提交时可以使用完全不同的 deadline 和 priority，而不修改 WfFormat。这就是 PPT 所说 “Same workflow, two different SLAs — so the SLA is not part of the workflow”。

### 新增三：只有一部分 SLA 会影响 SENSE-O request


| SLA 内容                | 谁消费                                                   | 是否新增 SENSE-O 字段                                        |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------ |
| `periodicDeadline`    | workflow/campaign scheduler，用于决定是否接受新 batch、是否扩容或并发   | 否                                                      |
| submission `deadline` | workflow scheduler，约束整个运行和最终 egress                   | 否；不能直接等同 `Connection.schedule.end`                     |
| `priority`            | workflow scheduler；若有明确 policy，可映射到 SENSE `qos_class` | 暂不新增；`priority: 3` 不能机械翻译成某个 QoS enum                  |
| `taskDeadlines`       | task scheduler                                        | 否；网络 API 不调度 task                                      |
| `fileDeadlines`       | adapter + transfer scheduler                          | 否；复用 Example 1，结合文件大小推导 `bandwidth.capacity = "80000"` |


因此 Example 1 的 SENSE-O request 不需要因为新增 overall/task SLA 而复制一组 deadline 字段。当前唯一已经展示的直接影响仍是：

```text
file size + fileDeadline
        ↓ adapter
SENSE-O bandwidth.capacity
```

如需控制网络服务何时建立、保留多久，adapter 可以从 campaign 时间约束派生 `Connection.schedule`；但 SENSE-O 2.0.4 没有澄清 `schedule.start/end/duration` 的精确格式与语义，所以本例不把 submission deadline 原样复制为 `schedule.end`。

### 新增四：execution 只记录事实，SLA 判定另行计算

为判断 `taskDeadlines.analyze-output`，在 WfFormat execution 中只补该 task 的实际事实：

```yaml
execution:
  tasks:
    - id: analyze-output
      startedAt: "2026-08-27T02:37:00Z"
      runtimeInSeconds: 600
```

由此得到 task completion time：

```text
02:37:00 + 600 s = 02:47:00
02:47:00 <= task deadline 02:50:00
task SLA = 满足，提前 180 s
```

结合 Example 1 已有 execution：


| SLA                                     | 当前观测                                 | 判定            |
| --------------------------------------- | ------------------------------------ | ------------- |
| `fileDeadlines.detector-output = 02:30` | 文件实际 `02:36:40` 结束                   | ❌ 晚 400 s     |
| `taskDeadlines.analyze-output = 02:50`  | task 实际 `02:47` 完成                   | ✅ 提前 180 s    |
| submission `deadline = 03:00`           | Example 1 没有完整 workflow 最终 egress 事实 | 未知，不能提前判定     |
| intrinsic `periodicDeadline = 7200 s`   | 还需要本次完整 completion 与下一批 arrival      | 未知，不能提前判定     |
| `priority = 3`                          | 它是调度输入，不是完成结果                        | 不适用 pass/fail |


这个结果说明：局部 task deadline 满足，不代表 file deadline 或整体 SLA 满足；每条 SLA 必须与对应 scope 的 execution facts 独立比较。

## Example 4：Endpoints 从三个 schema 映射到 SENSE-O terminals

本例复用 Example 1 的 `detector-output` 和 APS → ANL connection，只把先前简写的 endpoint 映射完整展开。Example 1 已同步改正为 PPT 的口径：WfCampaign binding 指向 WfPlatform node ID，execution source/destination 也记录 node ID，而不是 SENSE URI。

### 新增一：WfFormat 只声明文件端点角色

复用 Example 1 已修正的 file：

```yaml
specification:
  files:
    - id: detector-output
      sizeBytes: 36000000000000
      origin:
        kind: instrument
        ref: aps_detector
      destination:
        kind: compute
        ref: anl_compute
```

`aps_detector` 和 `anl_compute` 是平台无关角色，不是 hostname、Globus collection、IP 或 SENSE URI。任务不携带 endpoints；文件才携带数据从哪里来、最终要到哪里去的角色约束。

### 新增二：WfCampaign 把角色绑定到本次运行的 node

复用 Example 1 已修正的 bindings：

```yaml
bindings:
  aps_detector: aps-beamline-8id
  anl_compute: anl-n01
```

bindings 的 key 必须对应 WfFormat 中的 `origin.ref` / `destination.ref`，value 必须是当前 WfPlatform `sites[].nodes[].id`。因此本次运行的逻辑解析是：

```text
aps_detector → aps-beamline-8id
anl_compute  → anl-n01
```

同一份 WfFormat 如果下次改绑到 SLAC，只修改 WfCampaign，不修改 workflow specification。

### 新增三：WfPlatform 提供 node 与数据访问地址

只补本次 binding 引用的两个 node：

```yaml
sites:
  - id: anl-aps
    domain: ANL
    nodes:
      - id: aps-beamline-8id
        capabilities: [produce]
        address:
          protocol: globus
          collection: ddb59aef-6d04-11e5-ba46-22000b92c6ec
          path: /8id/raw

  - id: anl-lcrc
    domain: ANL
    nodes:
      - id: anl-n01
        capabilities: [compute, store]
```

这里 `address` 回答“workflow/data mover 如何访问数据”。它不自动等于 SENSE terminal：Globus collection/path 是应用层数据地址，而 SENSE `Terminal.uri` 是网络 service attachment point。

### 新增四：adapter 先尝试用 SENSE discovery 解析 terminal URI

adapter 按以下链条解析每个 role：

```text
WfFormat role
    ↓ WfCampaign.bindings
WfPlatform node id
    ↓ WfPlatform node → site/domain
SENSE GET /discover/lookup/{name}
    ↓ 匹配返回的 edge point / port URI
SENSE terminal URI
```

概念调用如下，具体 URL encoding 省略：

```http
GET /discover/lookup/aps-beamline-8id
GET /discover/lookup/anl-n01
```

假设 discovery/adapter registry 得到：

```text
aps-beamline-8id → urn:ogf:network:example:aps:port1
anl-n01          → urn:ogf:network:example:anl:port7
```

需要实测确认：2.0.4 把该 endpoint 描述为按 name / NetworkAddress / FQDN 查询 URI，但 response schema 却引用 `DomainDescription`，并不是一个清晰的 node → terminal mapping object。不能仅凭 Swagger 假设任意 WfPlatform node ID 都能被成功解析。

### 新增五：写入现有 SENSE-O `terminals[].uri`

解析成功后，复用 Example 1 的同一个 `Connection`，只看 terminals 部分：

```json
{
  "terminals": [
    {
      "name": "aps",
      "uri": "urn:ogf:network:example:aps:port1",
      "vlan_tag": "any"
    },
    {
      "name": "anl",
      "uri": "urn:ogf:network:example:anl:port7",
      "vlan_tag": "any"
    }
  ]
}
```

SENSE-O 已经有 `terminals[].uri`，因此无需扩展 SENSE API。真正需要解决的是 adapter 如何从 WfPlatform node 找到正确的 network attachment URI。

### 新增六：WfFormat execution 记录实际 node，不回填 SENSE URI

传输完成后，复用 Example 1 的 transfer record：

```yaml
execution:
  transfers:
    - file: detector-output
      source: aps-beamline-8id
      destination: anl-n01
      # bytes、durationSeconds、rttMs 等复用前例
```

`source` / `destination` 必须继续引用 WfPlatform node ID。SENSE terminal URI 由 adapter 与 `service_uuid` / `intent_uuid` 的关联记录保存，不把平台相关网络 URI 塞回 WfFormat execution 的 node-id 字段。

### 如果 discovery 无法解析：最小候选扩展属于 WfPlatform

只有在 node/site identity 无法通过 SENSE discovery 或既有 registry 解析时，才考虑在 WfPlatform node 上显式增加 network attachment mapping：

```yaml
nodes:
  - id: aps-beamline-8id
    address:
      protocol: globus
      collection: ddb59aef-6d04-11e5-ba46-22000b92c6ec
      path: /8id/raw
    networkAttachments:              # 候选扩展，尚未定稿
      - provider: sense-o
        terminalUri: urn:ogf:network:example:aps:port1
```

不把 `terminalUri` 混进 `address`，因为两者 owner 和语义不同：`address` 属于 data access，`networkAttachments` 属于 network attachment。多宿主 node 也可能对应多个 attachment，所以候选结构使用数组。

### 三个 schema 与 SENSE-O 的完整映射

```text
WfFormat.files[].origin.ref / destination.ref
                    │  平台无关 role
                    ↓
WfCampaign.bindings[role]
                    │  本次运行绑定
                    ↓
WfPlatform.sites[].nodes[].id
                    │  node → site/domain/address
                    ↓ adapter discovery 或 attachment registry
SENSE-O Connection.terminals[].uri
                    │  网络 provisioning attachment
                    ↓ transfer 执行后
WfFormat.execution.transfers[].source / destination
                       = 实际 WfPlatform node id
```

字段分类：


| 信息                          | 归属                                                                       | 是否需要扩 SENSE-O |
| --------------------------- | ------------------------------------------------------------------------ | ------------- |
| 文件端点角色                      | WfFormat specification                                                   | 否             |
| 本次 role → node binding      | WfCampaign                                                               | 否             |
| node 的数据访问地址                | WfPlatform `nodes[].address`                                             | 否             |
| node → SENSE attachment URI | 优先由 adapter discovery/registry 解析；失败时才考虑 WfPlatform `networkAttachments` | 否             |
| provisioning terminal       | SENSE-O `terminals[].uri`                                                | 已有，直接复用       |
| 实际传输 source/destination     | WfFormat execution，引用 WfPlatform node ID                                 | 否             |




## Example 5：把 transfers 投影到 links，得到 Spatial distribution

本例复用 Example 1 的 `detector-output` transfer、Example 4 的 endpoint/node 映射以及已有 campaign；只新增 spatial distribution 必需而前例没有的 topology links、planned route 和 actual path。为了让不同 link 可比较，再增加两个最小 transfer。

### 新增一：WfPlatform 补齐分层 topology

```yaml
domains:
  - id: ANL
    kind: facility
    telemetryVisible: true
  - id: ESnet
    kind: network-provider
    telemetryVisible: false

# sites/nodes 大部分复用 Example 4；只展示计算需要的 links
links:
  - id: aps-anl-link
    level: site
    endpoints: [anl-aps, anl-lcrc]
    capacityGbps: 100
    administeredBy: ANL

  - id: L0
    level: node
    endpoints: [anl-n01, anl-n02]
    capacityGbps: 25
    administeredBy: ANL

  - id: L1
    level: site
    endpoints: [anl-lcrc, esnet-chi]
    capacityGbps: 100
    administeredBy: ESnet

  - id: L2
    level: site
    endpoints: [esnet-chi, esnet-atl]
    capacityGbps: 400
    administeredBy: ESnet

  - id: L3
    level: site
    endpoints: [esnet-atl, ornl-olcf]
    capacityGbps: 100
    administeredBy: ESnet

routes:
  - src: anl-aps
    dst: anl-lcrc
    policy: single
    paths: [[aps-anl-link]]
  - src: anl-n01
    dst: anl-n02
    policy: single
    paths: [[L0]]
  - src: anl-lcrc
    dst: ornl-olcf
    policy: ecmp
    paths: [[L1, L2, L3]]
```

`level` 决定 link endpoints 是 node 还是 site；中转 PoP `esnet-chi`、`esnet-atl` 必须作为 transit sites 存在，不能让 link 引用悬空 ID。

### 新增二：WfCampaign 记录 planned route

在 Example 3 的同一个 submission 上只补 route decision：

```yaml
route:
  anl-aps->anl-lcrc: [aps-anl-link]
  anl-n01->anl-n02: [L0]
  anl-lcrc->ornl-olcf: [L1, L2, L3]
```

这是调度器给出的输入决策，不是执行事实。它的 link IDs 必须引用 WfPlatform `links[].id`。

### 新增三：WfFormat execution 记录 actual path

Example 1 已有的 `detector-output` transfer 只新增 `path`；另加两个 transfer，构成多 link 的最小 spatial example：

```yaml
execution:
  transfers:
    # 复用 Example 1：36 TB，4000 s，Real throughput 72 Gbps
    - file: detector-output
      source: aps-beamline-8id
      destination: anl-n01
      bytes: 36000000000000
      durationSeconds: 4000
      path: [aps-anl-link]

    # 新增：站内移动
    - file: chunk-output
      source: anl-n01
      destination: anl-n02
      bytes: 20000000000
      durationSeconds: 8.4
      path: [L0]

    # 新增：跨域结果输出
    - file: result-output
      source: anl-n02
      destination: ornl-n01
      bytes: 130000000
      durationSeconds: 6.1
      path: [L1, L2, L3]
```

`source` / `destination` 仍是 WfPlatform node IDs；`path` 才是这次端到端 move 实际经过的 WfPlatform link IDs。一条 transfer 可以经过多条 link，因此同一份 `130 MB` 会同时计入 L1、L2、L3。

不能把 WfCampaign planned route 直接复制成 execution actual path：如果发生重路由、故障切换或 provisioning 偏差，两者可能不同。缺少可靠 actual-path observation 时，只能计算 planned spatial distribution，并明确标注，不得冒充 execution fact。

### 新增四：按每条 transfer 的 active window 计算 link utilization

本例每条 link 在所选 active window 内只承载一个已列出的 transfer，因此可使用 slides 中的简式：

```text
loadBytes[link] += transfer.bytes     for each link in transfer.path

utilization[link]
  = loadBytes[link] × 8
    / (capacityGbps[link] × 1e9 × activeWindowSeconds[link])
```

按十进制 GB/TB 计算：


| Link           | Capacity | 本 workflow 承载 bytes | Active window | 本 workflow 的容量占用 |
| -------------- | -------- | ------------------- | ------------- | ---------------- |
| `aps-anl-link` | 100 Gbps | 36 TB               | 4000 s        | 72.00%           |
| `L0`           | 25 Gbps  | 20 GB               | 8.4 s         | 76.19%           |
| `L1`           | 100 Gbps | 130 MB              | 6.1 s         | 0.170%           |
| `L2`           | 400 Gbps | 130 MB              | 6.1 s         | 0.043%           |
| `L3`           | 100 Gbps | 130 MB              | 6.1 s         | 0.170%           |


例如 L0：

```text
20e9 bytes × 8 / (25e9 bit/s × 8.4 s)
  = 0.7619
  = 76.19%
```

所以本例中承载字节最多的是 `aps-anl-link`，但 active window 内最紧张的是只有 20 GB 的站内 `L0`。Spatial distribution 必须把 bytes、path、capacity 和 observation window 一起看，只比较 bytes 会得出错误结论。

### 新增五：区分 workflow-attributed load 与 total network utilization

上表严格计算的是“本 workflow 的 transfers 对各 link capacity 的归属占用”，不自动包含其他用户流量：


| Link owner                  | `telemetryVisible` | 能否据此声称 total utilization                                             |
| --------------------------- | ------------------ | -------------------------------------------------------------------- |
| ANL 管理的 `aps-anl-link`、`L0` | `true`             | 只有再结合 ANL 可见的其他流量 telemetry 才能得到 total；本表本身仍是本 workflow contribution |
| ESnet 管理的 `L1/L2/L3`        | `false`            | 不能；对 total utilization 至多是下界，因为其他租户流量不可见                             |


`telemetryVisible` 从 `link.administeredBy → domains[].telemetryVisible` 派生，不另存 `loadIsGroundTruth`，避免状态漂移。

### 三个 schema 如何映射到 SENSE-O

```text
WfCampaign.route（planned WfPlatform link IDs）
        +
WfPlatform.routes / links
        ↓ adapter 映射到 SENSE Path URI
SENSE-O Connection.path_tprofile.inclusion_list[]
        ↓ provisioning
actual path observation（若有）
        ↓ 规范化回 WfPlatform link IDs
WfFormat.execution.transfers[].path
        + bytes / durationSeconds
        ↓
derived spatial distribution per link
```

SENSE-O 2.0.4 已能用 `path_tprofile.inclusion_list[].uri` 表达 planned path constraint，因此无需新增 SENSE request 字段。但它没有 typed GET 返回 actual path、per-link bytes 或 utilization：

- 若 SENSE model/独立 network telemetry 能提供实际路径，adapter 需把 provider URI 映射回 WfPlatform link IDs；
- 若拿不到 actual path，只能保留 WfCampaign planned route，spatial result 必须标为 planned/estimated；
- link total utilization 仍需 provider/site telemetry，不能由 intent 或本 workflow 的 transfer bytes 推出。

当前真正的候选缺口不是新的 spatial-distribution schema，而是 **planned SENSE Path URI ↔ WfPlatform link IDs ↔ observed actual path** 的可验证映射与 read-back。

## Example 6：把每条 link 的负载展开到时间桶，得到 Temporal distribution

本例完全复用 Example 5 的三条 transfer、actual path 和 WfPlatform link capacity；只新增 `startedAt`，不增加新的 schema 字段。

### 新增一：给既有 transfers 补实际开始时间

按照 `(file, source, destination, startedAt)` 定位 Example 5 的三条 transfer，只补：

```yaml
execution:
  transfers:
    - file: detector-output
      # 其他字段复用 Example 5
      startedAt: "2026-08-27T01:30:00Z"
      durationSeconds: 4000

    - file: chunk-output
      # 其他字段复用 Example 5
      startedAt: "2026-08-27T02:37:03Z"
      durationSeconds: 8.4

    - file: result-output
      # 其他字段复用 Example 5
      startedAt: "2026-08-27T02:37:24Z"
      durationSeconds: 6.1
```

因此两个短 transfer 的实际区间是：

```text
chunk-output  : 02:37:03.0 → 02:37:11.4
result-output : 02:37:24.0 → 02:37:30.1
```



### 新增二：选择 10 秒 observation bins

```text
b0 = [02:37:00, 02:37:10)
b1 = [02:37:10, 02:37:20)
b2 = [02:37:20, 02:37:30)
b3 = [02:37:30, 02:37:40)
Δ  = 10 s
```

选择 Δ 是分析参数，不写进 WfFormat、WfPlatform 或 WfCampaign。不同 Δ 会产生不同的峰值，因此每份 derived temporal result 必须同时报告 bin width。

### 新增三：用 overlap 把 transfer bytes 分到时间桶

slides 中的推导可直接复用现有字段：

```text
rate[t] = bytes[t] / durationSeconds[t]

for transfer t:
  for link in t.path:
    for bin b overlapping t:
      loadBytes[link][b] += rate[t] × overlapSeconds(t, b)

utilization[link][b]
  = loadBytes[link][b] × 8
    / (capacityGbps[link] × 1e9 × Δ)
```

这里假设一条 transfer 在整个 duration 内匀速。只有 aggregate `bytes + duration` 时，这是可复现的近似，不是真正的瞬时流量；要看到 burst，需要更细粒度的 byte counters 或 transfer telemetry。

### 新增四：计算 `chunk-output` 在 L0 上的时间分布

Example 5 已知：

```text
bytes    = 20 GB
duration = 8.4 s
path     = [L0]
capacity = 25 Gbps
rate     = 20 GB / 8.4 s = 2.38095 GB/s
```

它在 b0 内重叠 7.0 秒，在 b1 内重叠 1.4 秒：


| Bin | Overlap | 分配到 L0 的 bytes | 10 秒桶内 utilization |
| --- | ------- | -------------- | ------------------ |
| b0  | 7.0 s   | 16.667 GB      | 53.33%             |
| b1  | 1.4 s   | 3.333 GB       | 10.67%             |
| b2  | 0       | 0              | 0%                 |
| b3  | 0       | 0              | 0%                 |


Example 5 用 transfer 自己的 8.4 秒 active window 算出 76.19%；换成 10 秒固定桶后，峰值变成 53.33%。数据没变，只是 observation window 变了。

### 新增五：计算 `result-output` 在 L1/L2/L3 上的时间分布

`result-output` 从 `02:37:24` 到 `02:37:30.1`：在 b2 重叠 6.0 秒，在 b3 重叠 0.1 秒。相同 bytes 会沿 actual path 同时投影到三条 link，但分母 capacity 不同：


| Link | Capacity | b2 utilization | b3 utilization |
| ---- | -------- | -------------- | -------------- |
| L1   | 100 Gbps | 0.1023%        | 0.0017%        |
| L2   | 400 Gbps | 0.0256%        | 0.0004%        |
| L3   | 100 Gbps | 0.1023%        | 0.0017%        |




### 新增六：长 transfer 的曲线

`detector-output` 为 36 TB / 4000 s，平均 72 Gbps，并且从 `01:30:00` 开始，恰好覆盖 400 个完整的 10 秒桶。因此在匀速假设下：

```text
aps-anl-link utilization[b] = 72%
for every 10 s bin from 01:30:00 to 02:36:40
```

这条长传输对 10 秒分桶不敏感；8.4 秒和 6.1 秒的短传输则会被 10 秒甚至 60 秒平均显著稀释。

### Temporal result 摘要

```text
time bin                 aps-anl-link      L0       L1       L2       L3
01:30:00–02:36:40        72% (每个10s桶)   0        0        0        0
02:37:00–02:37:10        0                 53.33%   0        0        0
02:37:10–02:37:20        0                 10.67%   0        0        0
02:37:20–02:37:30        0                 0        0.1023%  0.0256%  0.1023%
02:37:30–02:37:40        0                 0        0.0017%  0.0004%  0.0017%
```



### 三个 schema 如何映射到 SENSE-O

```text
WfCampaign.submissions[].at / deadline / route
        ↓ adapter 形成 planned network-service timing
SENSE-O Connection.schedule + path_tprofile
        ↓ provisioning
实际 transfer 执行
        ↓
WfFormat.execution.transfers[]
  startedAt + durationSeconds + bytes + path
        +
WfPlatform.links[].capacityGbps
        ↓ binning（Δ）
derived temporal distribution per link
```

- WfCampaign 的 `at`、deadline 和 route 是计划输入；它们不能替代实际 `startedAt` / `durationSeconds`。
- SENSE-O 2.0.4 的 `Connection.schedule.start/end/duration` 可用于表达 planned connection window，但格式与精确语义仍待确认，不能把它当成实际流量曲线。
- SENSE-O 2.0.4 没有 typed GET 返回 per-bin bytes、actual throughput time series 或 actual path；这些仍需 execution/data-mover/network telemetry。
- Temporal distribution 本身不需要扩展三个 schemas 或 SENSE request。真正缺的是更细粒度生成/观测能力；只有 aggregate transfer record 时，匀速分桶只是估计。



# 总结：用到了sense API的哪些字段

你目前真正需要关注的 SENSE-O 字段，可以压缩成四组：**端点、带宽、路径和计划时间**。


| 目的         | SENSE-O 字段                                                                  | 我们三个 schema 的来源                                                  | 重要程度                 |
| ---------- | --------------------------------------------------------------------------- | ---------------------------------------------------------------- | -------------------- |
| 指定虚拟链路两端   | `connections[].terminals[].uri`                                             | WfFormat role → WfCampaign binding → WfPlatform node → SENSE URI | **核心**               |
| 请求链路带宽     | `connections[].bandwidth.capacity`                                          | 文件大小与 `fileDeadline` 推导出的 required bandwidth                     | **核心**               |
| 约束网络路径     | `connections[].path_tprofile.inclusion_list[].uri` / `exclusion_list[].uri` | WfCampaign planned route + WfPlatform topology                   | **核心，但是否需要由实验决定**    |
| 指定建链时间窗口   | `connections[].schedule.start/end/duration`                                 | WfCampaign 的提交时间、deadline 或网络服务窗口                                | **核心，但 2.0.4 语义需确认** |
| 选择网络服务类型   | `data.type`                                                                 | P2P、VLAN bridge 或 L3VPN 的需求                                      | 基础配置                 |
| 设置 QoS 类别  | `bandwidth.qos_class`                                                       | 暂时不能直接从 science priority 映射                                      | 次要、需确认语义             |
| VLAN/IP 配置 | `terminals[].vlan_tag` 等                                                    | WfPlatform 的网络接入信息                                               | 按部署需要                |
| 连接名称       | `connections[].name`                                                        | adapter 生成                                                       | 仅标识                  |


完整定义可看：

- [ServiceIntent (line 1350)](/Users/lxzhong/Documents/GitHub/genesis_scinet/runs/20260826_181552_probe_sense_intent_harmonize_847b6e8/sense_o_intent_api_2.0.4.yaml:1350)
- [DNC data 与 connections (line 1686)](/Users/lxzhong/Documents/GitHub/genesis_scinet/runs/20260826_181552_probe_sense_intent_harmonize_847b6e8/sense_o_intent_api_2.0.4.yaml:1686)
- [Connection 字段 (line 1732)](/Users/lxzhong/Documents/GitHub/genesis_scinet/runs/20260826_181552_probe_sense_intent_harmonize_847b6e8/sense_o_intent_api_2.0.4.yaml:1732)

### 1. 最重要：`terminals[].uri`

```
terminals:
  - uri: "urn:ogf:network:site-a:port-1"
  - uri: "urn:ogf:network:site-b:port-2"
```

它告诉 SENSE：虚拟链路应该连接哪两个网络接入点。

我们的转换链是：

```
WfFormat endpoint role
→ WfCampaign bindings 中的 WfPlatform node ID
→ WfPlatform 中的节点/地址
→ 查询或注册得到 SENSE terminal URI
→ terminals[].uri
```

你最需要解决的是：**WfPlatform node ID 如何稳定、可验证地转换为 SENSE terminal URI。**

### 2. 最直接：`bandwidth.capacity`

```
bandwidth:
  capacity: "80000"
```

- 类型是字符串。
- 单位固定为 **Mbps**。
- `"80000"` 表示请求 80 Gbps。

我们的映射是：

```
WfFormat file size
+ WfCampaign fileDeadline
→ required bandwidth
→ 换算成 Mbps
→ bandwidth.capacity
```

注意：这是**请求带宽**，不是实际吞吐。Real throughput 不从这里读取。

### 3. 路径：`path_tprofile`

```
path_tprofile:
  inclusion_list:
    - uri: "urn:ogf:network:path-a"
  exclusion_list:
    - uri: "urn:ogf:network:path-b"
```

它表达：

- `inclusion_list`：希望路径包含哪些网络路径或资源。
- `exclusion_list`：希望避开哪些路径或资源。

我们的映射是：

```
WfCampaign planned route
+ WfPlatform links/routes
→ SENSE Path URI
→ path_tprofile
```

这里的关键问题是：**WfPlatform link ID 和 SENSE Path URI 如何对应。**

它只能表达计划路径约束，不能证明实际流量最终走了该路径。

### 4. 时间：`schedule`

```
schedule:
  start: "..."
  end: "..."
  duration: "..."
```

它表达的是计划建链或保留网络资源的时间窗口，可以由 WfCampaign 的计划时间与 deadline 推导。

但要特别注意：2.0.4 中时间格式的说明和例子并不充分。因此目前应该把它理解为：

> planned connection window，而不是 transfer 实际开始、结束时间。

真实 Temporal distribution 仍由以下执行记录推导：

```
WfFormat.execution.transfers[].startedAt
+ durationSeconds
+ bytes
+ path
+ WfPlatform link capacity
```

### 5. 暂时不要直接映射：`qos_class`

允许值包括：

```
qos_class: guaranteedCapped
# softCapped
# anyAvailable
# bestEffort
```

这个字段看起来像网络服务等级，但 2.0.4 没有充分说明具体保障语义。因此不要简单这样映射：

```
WfCampaign priority: high
→ qos_class: guaranteedCapped   # 目前不能这样直接断言
```

需要先向 SENSE 团队确认每个 QoS class 的实际 provisioning 和 bandwidth guarantee 语义。

### SENSE-O 没有的字段

以下内容虽然是我们的 science-SLA 重点，但 **SENSE-O 2.0.4 没有直接字段**：

- required latency
- actual RTT
- real throughput
- transferred bytes
- transfer duration
- actual path
- per-link utilization
- temporal traffic distribution
- workflow/task/file deadline
- science priority 的明确语义

所以整体边界是：

```
SENSE-O：
提交端点、带宽、路径和计划时间等网络 intent

三个 schemas：
保存 workflow 语义、science-SLA、平台拓扑和实际执行事实

adapter：
在二者之间推导和转换
```

当前最值得优先确认的四件事是：

1. WfPlatform node 如何解析成 `terminal.uri`。
2. `bandwidth.capacity` 是否确实按 Mbps 执行及其保障边界。
3. WfPlatform link/route 如何对应 `Path.uri`。
4. `schedule` 的准确格式和资源保留语义。

