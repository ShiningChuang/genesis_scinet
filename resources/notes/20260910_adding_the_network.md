# Part 2：Adding the Network

- 来源：`resources/slides/How to Describes a Workflow.pptx`
- 范围：第 12–28 页，标题为 “Part 2 — Adding the Network”
- 整理时间：2026-09-10 13:16:19 PDT（UTC-07:00）
- 本次更新：2026-09-10 13:30:45 PDT（UTC-07:00），补全 Example 1/4–4/4
- 文档性质：对演示文稿内容的结构化整理。文中的 schema 和字段是幻灯片提出的设计草案，不代表已经定稿或验证的项目结论。

## 1. 要解决的问题

现有 WfFormat 能描述工作流的任务 DAG、文件依赖、文件大小、机器和任务执行指标，但无法完整表达网络相关信息，例如：

- 文件从哪里读入、写到哪里；
- 文件传输经过哪些链路；
- 平台的网络拓扑；
- 链路能提供多少容量和多大延迟；
- 某次运行需要多少带宽；
- 实际吞吐和 RTT；
- 工作流、任务或文件传输是否满足 deadline；
- 流量在不同链路和时间窗口中的分布。

Part 2 的目标是为这些信息找到合适的归属位置，同时区分：

1. 工作流本身固有、与平台无关的信息；
2. 平台及其网络能提供的信息；
3. 某次提交特有的 SLA、资源绑定和调度决策；
4. 运行结束后观测到的事实。

## 2. 总体设计

方案新增两个 schema，并扩展 WfFormat 的 `specification` 和 `execution`：

| 位置 | 描述对象 | 主要内容 |
|---|---|---|
| `WfPlatform`（新 schema） | 平台与网络 | administrative domains、sites、nodes、links、routes、容量、延迟、管理方和遥测可见性 |
| `WfCampaign`（新 schema） | 一次 campaign / run | workflow 与 platform 引用、提交时间、SLA、角色到具体资源的绑定、placement、route、到达过程 |
| `WfFormat.workflow.specification`（扩展） | 平台无关的工作流定义 | 文件端点角色 `origin` / `destination`，以及应用固有的时间约束 `constraints` |
| `WfFormat.workflow.execution`（扩展） | 一次运行的观测结果 | `platformRef`、`campaignRef`、任务时间、文件位置、实际传输 `transfers[]`、机器所在 site 和传输汇总指标 |

字段归属的核心判断标准是：重新把同一个工作流运行在另一套平台上，这个值是否会变化。

- 不变化：属于 WfFormat `specification`；
- 随平台能力变化：属于 `WfPlatform`；
- 随某次提交变化：属于 `WfCampaign`；
- 运行后才能知道：属于 WfFormat `execution`。

## 3. WfPlatform：平台与网络拓扑

现有 `execution.machines[]` 只是机器平面列表，只包含 `nodeName`、内存和 CPU 等信息，没有 site、link 或 route。草案因此提出 `WfPlatform` 来描述资源拓扑。

### 3.1 主要对象

```json
{
  "id": "wfplatform:esnet-anl-ornl@2026-08-20",
  "measuredAt": "2026-08-20T06:00:00Z",
  "measurementMethod": "perfsonar bwctl + owamp",
  "domains": [],
  "sites": [],
  "links": [],
  "routes": []
}
```

#### `domains[]`

表示网络提供方或设施等 administrative domain。示例字段包括：

- `id`：如 `ESnet`、`ANL`；
- `kind`：如 `network-provider`、`facility`；
- `reservation.supported` 和 `reservation.api`：是否支持预约及对应系统，例如 OSCARS；
- `telemetryVisible`：本方是否能看到该 domain 的遥测。

幻灯片强调，其他租户流量可能不可见。因此某个链路负载数字是否可信，应根据链路的 `administeredBy` 和对应 domain 的 `telemetryVisible` 推导，而不是把可信度作为一个孤立值直接存储。

#### `sites[].nodes[]`

site 归属于某个 domain，可以带地理位置。instrument、DTN、compute node 和 archive 统一建模为 node，通过 `capabilities` 区分能力，例如：

```json
{
  "id": "anl-lcrc",
  "domain": "ANL",
  "location": "Lemont, IL",
  "nodes": [
    {
      "id": "anl-dtn01",
      "capabilities": ["store", "transfer"]
    },
    {
      "id": "anl-n01",
      "capabilities": ["compute", "store"],
      "cpu": {"coreCount": 8}
    }
  ]
}
```

transit PoP 也需要声明为 site，但可以没有 nodes：

```json
{
  "id": "esnet-chi",
  "domain": "ESnet",
  "transit": true,
  "nodes": []
}
```

#### `links[]`

link 可以连接 node，也可以连接 site；站内链路也纳入模型。

```json
{
  "id": "L0",
  "level": "node",
  "endpoints": ["anl-n01", "anl-n02"],
  "capacityGbps": 25,
  "administeredBy": "ANL",
  "latencyMs": {
    "p50": 0.08,
    "p95": 0.15,
    "p99": 0.4
  }
}
```

#### `routes[]`

route 描述 site 对之间的候选路径及策略：

```json
{
  "src": "anl-lcrc",
  "dst": "ornl-olcf",
  "policy": "ecmp",
  "paths": [["L1", "L2", "L3"]]
}
```

### 3.2 快照性质

完整示例带有 `measuredAt` 和 `measurementMethod`，说明 WfPlatform 本身也是一次测量或快照，而不是永远有效的静态真值。当 provider 流量不可见时，由工作流传输记录计算出的 load 只能视为 lower bound。

## 4. WfCampaign：某次提交的运行上下文

同一个工作流可以在不同时间提交到不同资源，并携带不同 SLA。因此 SLA、角色到资源的绑定、placement 和 route 不属于工作流静态定义，而属于某次 campaign / submission。

### 4.1 主要内容

完整示例中的 `WfCampaign` 包含：

- `id`：campaign 标识；
- `platformRef`：本次运行使用的平台快照；
- `bindings`：抽象端点角色到具体 node 的映射；
- `arrivalProcess`：多个 workflow submission 的到达模型、速率、burstiness 和 active window；
- `submissions[]`：每次提交的时间、工作流引用、placement、route 和 SLA。

```json
{
  "id": "wfcampaign:summer26-run17",
  "platformRef": "wfplatform:esnet-anl-ornl@2026-08-20",
  "bindings": {
    "primary-detector": "aps-beamline-8id",
    "long-term": "ornl-esgf",
    "preview-target": "viz01"
  },
  "arrivalProcess": {
    "model": "poisson",
    "ratePerHour": 12,
    "burstiness": 2.4,
    "activeWindow": [
      "2026-08-20T08:00Z",
      "2026-08-20T20:00Z"
    ]
  },
  "submissions": [
    {
      "id": "sub-003",
      "at": "2026-08-20T08:30:00Z",
      "workflowRef": "1000genome-crosslab-001",
      "placement": {
        "ID0000001": "anl-n01",
        "ID0000002": "anl-n02"
      },
      "route": {
        "anl-lcrc->ornl-olcf": ["L1", "L2", "L3"]
      },
      "sla": {
        "deadline": "2026-08-20T09:40:00Z",
        "priority": 3,
        "taskDeadlines": {
          "ID0000002": "2026-08-20T09:36:00Z"
        },
        "fileDeadlines": {
          "input.txt": "2026-08-20T09:00:00Z"
        }
      }
    }
  ]
}
```

跨实验室的 burst 到达模式放在 campaign 层，不嵌入单个 workflow。

## 5. WfFormat specification 的扩展

### 5.1 文件端点使用抽象角色

工作流定义只声明端点的语义角色，不写具体地址或节点：

```json
{
  "id": "input.txt",
  "sizeInBytes": 500000000000,
  "origin": {
    "kind": "instrument",
    "ref": "primary-detector"
  },
  "destination": null
}
```

```json
{
  "id": "result.txt",
  "sizeInBytes": 130000000,
  "origin": null,
  "destination": {
    "kind": "archive",
    "ref": "long-term"
  }
}
```

这样，把同一个工作流从 ANL 重新绑定到其他实验室时，只需修改 WfCampaign 的 `bindings`，不必修改 workflow specification。

中间文件如 `chunk.txt` 不一定能在 specification 中声明固定端点，因为它的实际位置取决于运行时 placement。

### 5.2 应用固有的时间约束

`constraints` 表示即使更换平台或重新提交也保持不变的应用约束。例如，仪器每五分钟产生下一批数据，当前批次必须在此周期内完成处理：

```json
{
  "constraints": [
    {
      "type": "periodicDeadline",
      "scope": "workflow",
      "periodSeconds": 300
    }
  ]
}
```

`periodSeconds` 表示应用自身的节奏，不属于某个具体平台或某次提交。

## 6. WfFormat execution 的扩展

execution 记录这次运行实际发生的事情。

### 6.1 运行引用和任务时间

```json
{
  "platformRef": "wfplatform:esnet-anl-ornl@2026-08-20",
  "campaignRef": "wfcampaign:summer26-run17#sub-003",
  "tasks": [
    {
      "id": "ID0000001",
      "readyAt": "2026-08-20T09:00:00Z",
      "startedAt": "2026-08-20T09:00:05Z",
      "runtimeInSeconds": 4.2,
      "coreCount": 1,
      "machines": ["anl-n01"]
    }
  ]
}
```

`readyAt` 和 `startedAt` 可以反映任务就绪后等待资源或数据的时间。

### 6.2 文件位置

```json
{
  "files": [
    {
      "id": "chunk.txt",
      "locations": ["anl-n01", "anl-n02"]
    }
  ]
}
```

`locations` 记录文件副本实际落到哪些节点。

### 6.3 实际文件传输

`execution.transfers[]` 是网络观测的核心记录。草案给出的传输键为：

```text
(fileId, source, destination, startedAt)
```

一条完整记录可包含：

```json
{
  "fileId": "input.txt",
  "source": "aps-beamline-8id",
  "destination": "anl-n01",
  "startedAt": "2026-08-20T08:31:12Z",
  "durationSeconds": 1720.0,
  "bytesTransferred": 500000000000,
  "path": ["APS-LCRC"],
  "rttMs": {
    "p50": 3.1,
    "p95": 4.4,
    "p99": 9.8
  },
  "parallelStreams": 8,
  "protocol": "globus-gridftp",
  "concurrentTransfers": 2
}
```

站内文件移动也应计入 `transfers[]`，不能只记录跨站 WAN 传输。

### 6.4 机器和汇总指标

execution 中的机器可以增加 `site`：

```json
{
  "nodeName": "anl-n01",
  "site": "anl-lcrc",
  "cpu": {"coreCount": 8}
}
```

汇总指标示例：

```json
{
  "sumTaskRuntimesInSeconds": 2104.2,
  "totalNumBytesTransferred": 520000000000,
  "totalTransferSeconds": 1734.5
}
```

## 7. 五类网络信息如何表达

### 7.1 Bandwidth

带宽被拆成三种不同含义：

1. **平台提供的容量**：`WfPlatform.links[].capacityGbps`；
2. **本次运行需要的带宽**：由 `WfFormat.files[].sizeInBytes` 和 WfCampaign 中对应文件的 deadline 推导；
3. **运行实际达到的吞吐**：由 `execution.transfers[].bytesTransferred / durationSeconds` 计算。

若 deadline budget 为秒，所需带宽可计算为：

```text
required_bandwidth_Gbps
  = sizeInBytes × 8 / deadline_budget_seconds / 1e9
```

实际吞吐为：

```text
observed_throughput_Gbps
  = bytesTransferred × 8 / durationSeconds / 1e9
```

capacity、required bandwidth 和 observed throughput 不能混为一个字段。

### 7.2 Latency

延迟也分成三层：

1. **平台基线**：`WfPlatform.links[].latencyMs`，可记录 p50、p95、p99；
2. **本次运行需要的延迟**：由数据流的 deadline 推导，而不是直接照搬链路属性；
3. **实际测得的 RTT**：`execution.transfers[].rttMs`。

### 7.3 SLA

SLA 被拆成应用固有约束和本次提交约束：

| 类型 | 位置 | 示例 |
|---|---|---|
| 更换平台后仍不变的应用约束 | WfFormat `specification.constraints[]` | `periodicDeadline`、`periodSeconds` |
| 本次提交特有的 SLA | WfCampaign | 整个 workflow 的 `deadline`、调度 `priority`、task deadline、file-transfer deadline |

时间戳沿用 WfFormat 的 ISO 8601 UTC 格式。

### 7.4 Endpoints

端点分三个阶段表达：

```text
WfFormat specification
  抽象角色：primary-detector / long-term

WfCampaign bindings
  具体资源：aps-beamline-8id / ornl-esgf

WfFormat execution.transfers[]
  实际到达的 source、destination 和时间窗口
```

对应关系如下：

1. workflow 声明 `files[].origin` / `destination`，只引用角色；
2. campaign 用 `bindings` 把角色绑定到本次运行的具体资源；
3. execution 用 `transfers[]` 记录真正使用的 source 和 destination。

### 7.5 Spatial and temporal traffic distribution

空间和时间流量分布都从现有字段派生，无需再增加专门字段。输入包括：

- `transfers[].bytesTransferred`；
- `transfers[].startedAt`；
- `transfers[].durationSeconds`；
- `transfers[].path`；
- `WfPlatform.links[].capacityGbps`。

两种视图最终都形成同一数据对象：

```text
load[link][bucket]
```

它表示某条 link 在某个时间 bucket 中承载的字节数。

#### 空间分布

在观察窗口内，将所有经过某条 link 的 workflow transfer bytes 累加，再除以该 link 在窗口内的理论容量：

```text
for each transfer t:
    for each link in t.path:
        load[link] += t.bytesTransferred

util[link]
  = load[link] × 8
    / (link.capacityGbps × 1e9 × observation_window_seconds)
```

这能定位流量发生在哪些链路，以及 workflow 占用了各链路多少容量。

#### 时间分布

先假定一次 transfer 在其持续时间内具有平均速率：

```text
rate = bytesTransferred / durationSeconds
```

然后把 transfer 覆盖的每个时间 bucket 按重叠时长分摊：

```text
for each transfer t:
    rate = t.bytesTransferred / t.durationSeconds
    for each link in t.path:
        for each bucket overlapping t:
            load[link][bucket] += rate × overlap(bucket, t)
```

若 bucket 宽度为 10 秒，持续时间为 3–14 秒的 transfer 会跨越前两个 bucket，各 bucket 获得 `rate × overlap` 对应的字节数。

#### 用途

- 定位 bottleneck 出现在哪条链路、哪个时间窗口；
- 向 SENSE 提供 link、带宽量和时间窗口组成的 demand profile；
- 在 workflow 提交前检查计划是否可能满足 deadline。

这里计算的是 workflow-attributed load。若要获得链路总利用率，还需要 provider telemetry。

## 8. 完整示例：Example 1/4–4/4

以下逐项整理第 25–28 页展示的完整 example。为便于阅读，幻灯片中的星号标记被改写为 `// NEW` 注释。源稿本身用 `…` 省略的值和缩写时间戳仍原样保留，因此这里是**幻灯片所展示内容的完整转录**，不是一个可以直接通过 schema validator 的完整实例。

### 8.1 Example 1/4：WfFormat specification

```jsonc
// ★ = new relative to WfFormat 1.6
{
  "name": "1000genome-crosslab-001",
  "schemaVersion": "1.6+net",
  "runtimeSystem": {
    "name": "pegasus",
    "version": "5.0.6"
  },
  "workflow": {
    "specification": {
      // Platform-independent: rebinding to SLAC changes nothing below.
      "tasks": [
        {
          "name": "split",
          "id": "ID0000001",
          "parents": [],
          "children": ["ID0000002"],
          "inputFiles": ["input.txt"],
          "outputFiles": ["chunk.txt"]
        },
        {
          "name": "analyze",
          "id": "ID0000002",
          "parents": ["ID0000001"],
          "children": [],
          "inputFiles": ["chunk.txt"],
          "outputFiles": ["result.txt"]
        }
      ],
      "files": [
        {
          "id": "input.txt",
          "sizeInBytes": 5.0e11,
          // NEW: a role, never an address.
          "origin": {
            "kind": "instrument",
            "ref": "primary-detector"
          },
          "destination": null
        },
        {
          "id": "chunk.txt",
          "sizeInBytes": 2.0e10
          // Intermediate file: no endpoint can be written here.
        },
        {
          "id": "result.txt",
          "sizeInBytes": 1.3e8,
          "origin": null,
          // NEW
          "destination": {
            "kind": "archive",
            "ref": "long-term"
          }
        }
      ],
      // NEW: intrinsic to the application. The next detector batch
      // arrives in five minutes.
      "constraints": [
        {
          "type": "periodicDeadline",
          "scope": "workflow",
          "periodSeconds": 300
        }
      ],
      "metrics": {
        "numberOfTasks": 2,
        "numberOfFiles": 3,
        "numberOfLevels": 2,
        "minimumWidth": 1,
        "maximumWidth": 1
      }
    },
    "execution": {
      "…": "continued in Example 2/4"
    }
  }
}
```

这部分的设计原则是：endpoint 在 specification 中只以角色出现。同一个 workflow 可以绑定到 ANL 或 ORNL，这种可重绑定性是 cross-lab 实验所需要的。

### 8.2 Example 2/4：WfFormat execution

```jsonc
"execution": {
  "makespanInSeconds": 2118.0,
  "executedAt": "2026-08-20T09:00:00Z",

  // NEW
  "platformRef": "wfplatform:esnet-anl-ornl@2026-08-20",
  // NEW
  "campaignRef": "wfcampaign:summer26-run17#sub-003",

  "tasks": [
    {
      "id": "ID0000001",
      // NEW
      "readyAt": "…09:00:00Z",
      "startedAt": "…09:00:05Z",
      "runtimeInSeconds": 4.2,
      "coreCount": 1,
      "machines": ["anl-n01"]
    },
    {
      "id": "ID0000002",
      "readyAt": "…09:00:09Z",
      "startedAt": "…09:00:18Z",
      "runtimeInSeconds": 2100.0,
      "coreCount": 4,
      "machines": ["anl-n02"]
    }
  ],

  // NEW: where the replicas landed.
  "files": [
    {
      "id": "chunk.txt",
      "locations": ["anl-n01", "anl-n02"]
    }
  ],

  // NEW: key = (fileId, source, destination, startedAt)
  "transfers": [
    {
      "fileId": "input.txt",
      "source": "aps-beamline-8id",
      "destination": "anl-n01",
      "startedAt": "…08:31:12Z",
      "durationSeconds": 1720.0,
      "bytesTransferred": 5.0e11,
      "path": ["APS-LCRC"],
      "rttMs": {
        "p50": 3.1,
        "p95": 4.4,
        "p99": 9.8
      },
      "parallelStreams": 8,
      "protocol": "globus-gridftp",
      "concurrentTransfers": 2
    },
    {
      "fileId": "chunk.txt",
      "source": "anl-n01",
      "destination": "anl-n02",
      // Intra-site moves count.
      "startedAt": "…09:00:09Z",
      "durationSeconds": 8.4,
      "bytesTransferred": 2.0e10,
      "path": ["L0"]
    },
    {
      "fileId": "result.txt",
      "source": "anl-n02",
      "destination": "ornl-n01",
      "startedAt": "…09:35:18Z",
      "durationSeconds": 6.1,
      "bytesTransferred": 1.3e8,
      "path": ["L1", "L2", "L3"],
      "rttMs": {
        "p50": 12.2,
        "p99": 35.1
      }
    }
  ],

  "machines": [
    {
      "nodeName": "anl-n01",
      // NEW
      "site": "anl-lcrc",
      "cpu": {"coreCount": 8}
    },
    {
      "nodeName": "anl-n02",
      "site": "anl-lcrc",
      "cpu": {"coreCount": 8}
    }
  ],

  "metrics": {
    "sumTaskRuntimesInSeconds": 2104.2,
    // NEW
    "totalNumBytesTransferred": 5.2e11,
    "totalTransferSeconds": 1734.5
  }
}
```

### 8.3 Example 3/4：WfPlatform

```jsonc
{
  "id": "wfplatform:esnet-anl-ornl@2026-08-20",
  "measuredAt": "2026-08-20T06:00:00Z",
  "measurementMethod": "perfsonar bwctl + owamp",
  // The platform description is itself a measurement.

  "domains": [
    {
      "id": "ESnet",
      "kind": "network-provider",
      "reservation": {
        "supported": true,
        "api": "oscars"
      },
      "telemetryVisible": false
      // Therefore load is a lower bound.
    },
    {
      "id": "ANL",
      "kind": "facility",
      "telemetryVisible": true
    }
  ],

  "sites": [
    {
      "id": "anl-aps",
      "domain": "ANL",
      "location": "Lemont, IL",
      "nodes": [
        {
          "id": "aps-beamline-8id",
          "capabilities": ["produce"],
          "address": {
            "protocol": "globus",
            "collection": "ddb59aef…"
          }
        }
      ]
    },
    {
      "id": "anl-lcrc",
      "domain": "ANL",
      "location": "Lemont, IL",
      "nodes": [
        {
          "id": "anl-dtn01",
          "capabilities": ["store", "transfer"]
          // A DTN is neither host nor endpoint.
        },
        {
          "id": "anl-n01",
          "capabilities": ["compute", "store"],
          "cpu": {"coreCount": 8}
        },
        {
          "id": "anl-n02",
          "capabilities": ["compute", "store"],
          "cpu": {"coreCount": 8}
        }
      ]
    },
    {
      "id": "ornl-olcf",
      "domain": "ORNL",
      "nodes": [
        {
          "id": "ornl-n01",
          "capabilities": ["compute"]
        },
        {
          "id": "ornl-esgf",
          "capabilities": ["store"]
        }
      ]
    },
    {
      "id": "esnet-chi",
      "domain": "ESnet",
      "transit": true,
      "nodes": []
    },
    {
      "id": "esnet-atl",
      "domain": "ESnet",
      "transit": true,
      "nodes": []
      // Transit PoPs must be declared.
    }
  ],

  "links": [
    {
      "id": "L0",
      "level": "node",
      "endpoints": ["anl-n01", "anl-n02"],
      "capacityGbps": 25,
      "administeredBy": "ANL",
      "latencyMs": {
        "p50": 0.08,
        "p95": 0.15,
        "p99": 0.4
      }
      // Intra-site link.
    },
    {
      "id": "APS-LCRC",
      "level": "site",
      "endpoints": ["anl-aps", "anl-lcrc"],
      "capacityGbps": 100,
      "…": "source slide omits the remaining fields"
    },
    {
      "id": "L1",
      "…": "source slide omits the remaining fields"
    },
    {
      "id": "L2",
      "…": "source slide omits the remaining fields"
    },
    {
      "id": "L3",
      "administeredBy": "ESnet",
      "…": "source slide omits the remaining fields"
    }
  ],

  "routes": [
    {
      "src": "anl-aps",
      "dst": "anl-lcrc",
      "policy": "single",
      "paths": [["APS-LCRC"]]
    },
    {
      "src": "anl-lcrc",
      "dst": "ornl-olcf",
      "policy": "ecmp",
      "paths": [["L1", "L2", "L3"]]
    }
  ]
}
```

### 8.4 Example 4/4：WfCampaign

```jsonc
{
  "id": "wfcampaign:summer26-run17",
  "platformRef": "wfplatform:esnet-anl-ornl@2026-08-20",

  // Role to node id. Rebinding to SLAC touches this map and nothing else.
  "bindings": {
    "primary-detector": "aps-beamline-8id",
    "long-term": "ornl-esgf",
    "preview-target": "viz01"
  },

  // Cross-lab bursts come from this layer, not from inside one workflow.
  "arrivalProcess": {
    "model": "poisson",
    "ratePerHour": 12,
    "burstiness": 2.4,
    "activeWindow": [
      "2026-08-20T08:00Z",
      "2026-08-20T20:00Z"
    ]
  },

  "submissions": [
    {
      "id": "sub-003",
      "at": "2026-08-20T08:30:00Z",
      "workflowRef": "1000genome-crosslab-001",

      // The input half of each decision. Execution holds the recorded half.
      "placement": {
        "ID0000001": "anl-n01",
        "ID0000002": "anl-n02"
      },
      "route": {
        "anl-lcrc->ornl-olcf": ["L1", "L2", "L3"]
      },

      // deadline covers the whole run, including egress.
      // Task and file deadlines are optional refinements.
      "sla": {
        "deadline": "2026-08-20T09:40:00Z",
        "priority": 3,
        "taskDeadlines": {
          "ID0000002": "2026-08-20T09:36:00Z"
        },
        "fileDeadlines": {
          "input.txt": "2026-08-20T09:00:00Z"
        }
      }
    }
  ]
}
```

### 8.5 四部分之间的对应关系

工作流的数据流为：

```text
input.txt（500 GB）
    ↓
split
    ↓
chunk.txt（20 GB）
    ↓
analyze
    ↓
result.txt（130 MB）
```

原始 WfFormat specification 只描述 tasks 和 files，不包含 node、site 或 link。WfCampaign 为任务选择机器并把端点角色绑定到具体资源；WfPlatform 提供资源与网络结构；WfFormat execution 再记录实际执行位置和文件传输。

示例中的三次文件移动为：

| 文件 | 实际端点 | 路径 | 链路容量或备注 |
|---|---|---|---|
| `input.txt`，500 GB | `aps-beamline-8id` 到 `anl-n01` | `APS-LCRC` | 100 Gbps |
| `chunk.txt`，20 GB | `anl-n01` 到 `anl-n02` | `L0` | 25 Gbps，示例标注约 76% busy |
| `result.txt`，130 MB | `anl-n02` 到 `ornl-n01` | `L1`、`L2`、`L3` | 100 / 400 / 100 Gbps |

这个例子展示了四部分如何把 workflow 文件依赖连接到实际机器、站点、链路、SLA 和传输观测。

## 9. 与 SENSE-O 的初步映射

Part 2 最后一页提出由 adapter 读取 WfFormat、WfPlatform 和 WfCampaign，并生成 SENSE-O `ServiceIntent`：

| 本方案中的信息 | SENSE-O 中的目标字段 | 说明 |
|---|---|---|
| `bindings` 解析出的具体端点 | `terminals[].uri` | 通过 `GET /discover/lookup` 获得具体 network attachment point |
| `files[].sizeInBytes` 和文件 deadline 推导出的所需带宽 | `bandwidth.capacity` | Mbps 字符串；幻灯片注明它是 cap，不等同于吞吐保证 |
| `sla.priority` | `bandwidth.qos_class` | SENSE-O 只有四个 class，仍需定义映射策略 |
| `submittedAt` 和 deadlines | `schedule.start` / `end` / `duration` | SENSE-O 字段是无类型字符串，且不携带 timezone 约束 |
| 路径或链路偏好 | `path_tprofile.inclusion_list` / `exclusion_list` | 表达使用或避开哪些路径 |

adapter 通过 `POST /instance/{siUUID}` 提交 ServiceIntent。SENSE-O 不能表达的 workflow 语义、执行记录和 SLA 评估仍保留在本方案自己的 schema 中。

## 10. 源稿中尚未统一的地方

以下是 Part 2 各页之间可见的命名或结构差异。整理时保留其原意，但不应把这些差异误认为已经定稿的 schema：

- 早期示例使用 `campaignId` 和 `runs[]`；完整示例改为 `id`、顶层 `bindings` 与 `submissions[]`；
- 文件传输 deadline 在不同页分别写作 `fileXferDeadlines`、`fileDeadlines`；
- 早期示例把 `workflowRef` 放在 campaign 顶层，完整示例把它放进每个 submission；
- 一些时间示例使用省略形式，如 `…T09:36:00Z`，正式 schema 需要完整 ISO 8601 时间戳；
- 空间分布备份页伪代码写有 `t.bytes`，其余页面统一使用 `bytesTransferred`；
- WfPlatform 示例的 `sites[]` 引用了 `ORNL`，但同页展示的 `domains[]` 只显式列出 `ESnet` 和 `ANL`；
- `WfPlatform` 被表述为 topology schema，但完整示例又带 `measuredAt` 和 `measurementMethod`，说明其静态定义、测量快照和更新机制仍需进一步明确。

## 11. 一句话总结

这套草案把网络信息拆成四层：WfFormat specification 描述工作流固有需求，WfPlatform 描述平台与网络，WfCampaign 描述某次提交的 SLA 和绑定，WfFormat execution 记录真实传输；带宽、延迟、端点及空间和时间流量分布再由这四层信息组合或派生。
