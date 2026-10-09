# Instance 是什么？

可以把 service instance 理解成“一项持续存在、可以反复操作的网络服务订单”。

例如，我们想建立 APS → ANL 的 virtual link：

```
GET /instance
    ↓
获得 siUUID = network-service-123

POST /instance/network-service-123
    ↓
提交第一次配置：APS ↔ ANL，80 Gbps

PUT /instance/network-service-123/provision
    ↓
要求 SENSE 实际建立这条连接

GET /instance/network-service-123/status
    ↓
查询是否已经 READY
```

instance 和 intent 的区别是：

```
Service instance：网络服务本身，具有稳定 UUID 和生命周期
    ├── Intent 1：最初申请 APS ↔ ANL，80 Gbps
    ├── Intent 2：后来修改为 60 Gbps
    └── Intent 3：再增加一个 ORNL endpoint
```

也就是说：

- instance 是“哪一项网络服务”；
- intent 是“这一次希望它变成什么配置”；
- 同一个 instance 可以先后包含多个 intent；
- SENSE 根据 intent 计算实际需要执行的网络变化，即 service delta。



# 网页左侧类型是什么

`workflow_combined`、`instance`、`profile` 等不是数据类型，而是 SwaggerHub 用来整理 API 的标签。

同一个 API 可以同时显示在多个标签中。例如：

```
POST /instance/{siUUID}
```

同时属于：

- `instance`
- `workflow_combined`
- `workflow_phased`

但它们指向的是同一个 API，并不是三个不同接口。


| 标签                  | 含义                                              | 谁使用                     |
| ------------------- | ----------------------------------------------- | ----------------------- |
| `workflow_combined` | 单阶段流程，尽量用较少步骤完成 provision/cancel/reprovision    | 普通 workflow client      |
| `workflow_phased`   | 两阶段流程，先准备资源，再统一 commit，适合网络、计算、存储 co-scheduling | 需要协同调度的 workflow client |
| `instance`          | 创建、修改、查询和取消 service instance                    | 建立网络服务时的核心 API          |
| `profile`           | 管理可复用的网络服务模板                                    | 用户或管理员                  |
| `intent`            | 按 UUID 读取某次已经提交的 intent                         | 用户，用于审计/read-back       |
| `discover`          | 查询 domain、端口、URI、capacity、peer 等拓扑信息            | 用户或 adapter             |
| `service`           | 声明为 service workflow 分类                         | 2.0.4 中没有 API 实际使用该标签   |
| `monitor`           | 声明为监控分类                                         | 2.0.4 中没有 API 实际使用该标签   |
| `notify`            | 让其他 SENSE 组件向 SENSE-O 回调 model/delta 事件         | 主要是 SENSE 内部组件          |
| `logging`           | 查询、配置或归档 SENSE-O 服务端日志                          | 运维/管理员                  |


因此，并不是所有左侧分类都用于科学 workflow 与网络交互。

对我们最重要的是：

```
discover
    查询可以使用哪些 endpoint URI、domain 和 capacity

instance + workflow_combined/workflow_phased
    提交并建立 virtual network service

intent
    读取之前提交的配置

profile
    使用预先定义好的网络服务模板
```

另外，用户实际交互的是 SENSE-O Orchestrator 的 Northbound API，并不是直接向交换机发送命令：

```
本组 workflow adapter
        ↓
SENSE-O Northbound API
        ↓
SENSE Orchestrator
        ↓
各网络域的 Resource Manager
        ↓
交换机/路由器/网络控制器
```



# 中间 YAML 和左侧 API 是什么关系？

> 我的理解是左边的API是单独和sense 网络交互的结构，中间的是具体的网络配置细节？

- 左侧是“可以调用哪些 HTTP 操作”；
- 中间 YAML 是产生整个网页的源文件；
- 中间 YAML 不仅包含网络配置结构，也包含左侧那些 API 本身。

OpenAPI YAML 主要分成两块：

```
paths:
  /instance/{siUUID}:
    post:
      requestBody:
        schema:
          $ref: "#/components/schemas/ServiceIntent"

components:
  schemas:
    ServiceIntent:
      ...
    Connection:
      ...
```

对应关系是：

```
OpenAPI YAML
    ├── paths
    │     └── 生成左侧 GET / POST / PUT / DELETE 列表
    │
    └── components/schemas
          └── 定义请求和响应里面具体有哪些字段
```

以 Example 1 为例：

```
POST /instance/{siUUID}
```

决定的是：

> 请求要发送到哪里、采用什么 HTTP 方法。

而它引用的：

```
ServiceIntent
  └── data.connections[]
        ├── terminals[]
        ├── bandwidth
        ├── schedule
        └── path_tprofile
```

决定的是：

> POST 请求的 JSON 内容具体长什么样。

所以一次完整调用是：

```
POST /instance/{siUUID}       ← 来自 paths

Request body:
{
  "service": "dnc",
  "data": {
    "connections": [{
      "terminals": [...],
      "bandwidth": {
        "capacity": "80000"
      }
    }]
  }
}                             ← 来自 components/schemas
```

---



# Sense和Sense API到底是什么

> sense和sense api到底是啥？sense本身是一个网络管理工具，并且已经接入esnet能够连接ANL和ornl吗

你的理解接近了，但要改得更精确：

> **SENSE 不是 ESnet 本身，也不只是普通的网络管理工具。它是位于 workflow 与多个网络管理系统之上的“端到端网络服务编排系统”。**



## 三者分别是什么

```
我们的 workflow / application
          │
          │ SENSE-O Intent API
          ▼
   SENSE Orchestrator
   理解需求、选择资源、协调多个域
          │
          │ 南向请求
          ▼
Resource Managers / 既有控制器
  ├─ ESnet WAN
  ├─ ANL site network
  └─ ORNL site network
          │
          ▼
交换机、路由器、VLAN、DTN 接口
```



### SENSE

SENSE 是整套系统，包括：

- **SENSE Orchestrator（SENSE-O）**：接收用户需求，计算并协调端到端服务。
- **Resource Manager（RM）**：管理一个具体域，例如 ESnet WAN、某个实验室的 Science DMZ 或 DTN。
- **模型和适配层**：把不同网络域的资源统一描述，并把编排结果交给各域已有的控制器执行。

官方的准确说法是：SENSE 位于科学 workflow/middleware 和各网络、站点资源的自动化控制层之间，目标是跨多个管理域建立端到端网络服务。[SENSE Architecture](https://sense.es.net/architecture)

因此，说它是“网络管理工具”不算完全错，但更准确的是：

> **SENSE 是跨域网络服务 orchestrator；它依赖各网络域自己的管理系统真正修改设备。**

它并不自己转发数据，也不是文件传输工具。

### SENSE API

我们正在看的 **SENSE-O Intent API 2.0.4**，是 workflow 与 SENSE Orchestrator 交互的北向 REST API。

例如 workflow 提交：

```
terminals:
  - uri: ANL的网络接入点
  - uri: ORNL的网络接入点
bandwidth:
  capacity: "80000"
```

它表达的是：

> “请在这两个网络接入点之间建立一个 80 Gbps 的网络服务。”

之后是 SENSE Orchestrator 联系 ESnet RM、ANL RM、ORNL RM 等组件，分别配置它们负责的那一段。

所以：

- SENSE = 整个编排系统。
- SENSE-O = 其中的 Orchestrator。
- SENSE-O Intent API = workflow 向 Orchestrator 提交需求的接口。
- ESnet = 实际承载跨实验室流量的广域网络之一。
- ANL/ORNL 网络 = 两端各自独立管理的站点网络。



## SENSE 是否已经接入 ESnet？

**是，公开资料能够确认 SENSE 已经在 ESnet 及其他科研网络的生产和 testbed 基础设施上部署、验证过。**

SENSE 由 ESnet 牵头开发，底层也曾集成 OSCARS、NSI、OpenDaylight、ONOS 等网络控制系统。[SENSE 官方介绍](https://sense.es.net/)，[SENSE 系统论文](https://www.osti.gov/servlets/purl/1577127)

但这里的“接入 ESnet”不等于：

> ESnet 上的任意两个机构都自动可以通过 SENSE API 建链。



## 是否已经能够用 SENSE 连接 ANL 和 ORNL？

**目前不能根据公开资料确认。**

目前能确认的是：

- **ANL 明确参加过 SENSE testbed**，站点包含 Science DMZ、DTN 和站点 Resource Manager。[ESnet SENSE testbed 文档](https://www.es.net/assets/Uploads/76kkEi9wqPrVdrGK4bSFdg.pdf)
- ANL 和 ORNL 都接入 ESnet，因此普通 IP 数据传输当然可以经过 ESnet。
- 但我没有找到官方公开证据表明 **ORNL 当前部署了可被这个 SENSE Orchestrator 控制的 SiteRM/兼容控制器**。
- 更没有找到“当前 SENSE 实例已经注册 ANL–ORNL 两端 terminal URI，且允许我们申请服务”的证据。

因此应当区分两个命题：

```
ANL 与 ORNL 能通过 ESnet通信
                ✅ 基本确定

当前 SENSE 实例能自动建立 ANL–ORNL 端到端虚拟链路
                ❓ 尚未确认
```



## 为什么接入 ESnet 还不够

建立真正的 ANL–ORNL 端到端链路，至少涉及：

```
ANL DTN/GPU
   │ ANL site network
   │
   ├──── ESnet WAN ────┤
                       │ ORNL site network
                       │
                    ORNL DTN/GPU
```

SENSE 必须至少能够控制或协调：

1. ANL 的站点接入段。
2. ESnet 的广域网段。
3. ORNL 的站点接入段。

如果只有 ESnet WAN 接入 SENSE，而 ORNL 没有 SiteRM，那么 SENSE 最多可能把服务建到 ORNL 的网络边界，不能保证继续延伸到指定的 ORNL DTN/GPU。

---



# DTN是啥

DTN = **Data Transfer Node**（数据传输节点）。

科研网络里专门用来搬大数据集的主机，通常部署在站点边界（靠近 DMZ / Science DMZ），特点是：

- 高速网卡（100/400 GbE）、大带宽存储、内核与 TCP 参数针对长肥管道调优；
- 上面只跑传输服务，不跑通用计算负载，避免抢资源；
- 传输工具就跑在它上面 —— Globus / GridFTP、FTS、XRootD、TaskVine worker 等。

在你这两份文档的语境里，DTN 的关键作用是**划清职责边界**：

- SENSE 负责建立网络服务（把 intent 配到交换机/控制器），但**不负责把文件从 A 搬到 B**；
- 真正执行传输的是 DTN 上的 transfer service，它是端点主机，不在交换机或路由器内部；
- 因此 `bytes`、`startedAt`/`endedAt` 这些 per-file 观测只能从 DTN 侧的 transfer record 拿到，再由 provenance collector 写回 `WfFormat.execution` 算出 Real throughput。SENSE-O Intent API 2.0.4 没有这类接口。

---



# Science DMZ 和 provenance collector



## **Science DMZ**

> Science Demilitarized Zone

ESnet 提出的一种网络架构模式。核心想法是：把大流量科研数据传输**从校园/园区的通用网络里摘出来**，单独走一条路径。

- 通用企业网的防火墙、NAT、深度包检测会把长肥管道上的大流量打残（丢包一点点，TCP 吞吐就断崖式下降）；
- 所以在站点边界划出一块专用区域，直连高速外网，**不过通用防火墙**，改用路由器 ACL + 主机层管控做安全；
- 这块区域里放的就是 DTN、以及 perfSONAR 之类的常驻测量节点。

所以 DTN 和 Science DMZ 的关系是：Science DMZ 是那块地，DTN 是地上的机器。

和 VPN 的区别是：


| 对比   | VPN             | Science DMZ             |
| ---- | --------------- | ----------------------- |
| 主要目的 | 远程安全访问内网        | 高速科研数据传输                |
| 典型用途 | 你在家连学校内网、访问服务器  | 两个实验室/HPC 中心传大数据        |
| 性能特点 | 安全优先，可能有加密/网关瓶颈 | 性能优先，减少防火墙/中间设备瓶颈       |
| 网络位置 | 让外部用户进入内网       | 通常放在校园网边界附近，绕开普通企业防火墙   |
| 安全方式 | 加密隧道、身份认证       | ACL、防火墙例外、IDS、专用 DTN、监控 |




## **Provenance collector**

这个是你文档里的角色（3.7 节，以及 [example.md](http://example.md) 的推荐数据流）。它是 workflow / provenance control plane 里的一个组件，职责是**收集执行事实并写回权威记录**。

文档里给它的定位很具体：

- 位置在**用户 / workflow 侧**，不在网络内部 —— 因为网络系统不知道某个 flow 对应哪个文件、文件属于哪个 task、workflow deadline 是什么、campaign 为什么选这条 route；
- 它向 DTN 上的 transfer service 只读取**该 workflow 自己那个 transfer job**的 `bytes`、`startedAt`、`endedAt`、`status`，用 service account / delegated credential / transfer-job token，不需要终端用户有 DTN 登录权限或全网 telemetry 读权限；
- 拿到后更新 `WfFormat.execution.transfers`，Real throughput = `bytes × 8 / durationSeconds`；
- 如果 data mover 不给 job 级的 bytes 和时间，它必须把 Real throughput 记为 **unavailable**，不能用预计文件大小或端口总流量冒充。

一句话对比：**data mover 干活，provenance collector 记账，WfFormat.execution 是那本账。**

---



# WfFormat是否与sense api有过交互

> 从wfFormat和wfcommons等相关论文的角度？

没有。

官方 WfFormat 的定位是：

> 用统一 JSON 格式保存 workflow specification、执行记录和性能特征，供分析、生成和模拟工具读取。

它主要服务于：

```
workflow execution logs
        ↓
     WfFormat
        ↓
WfInstances / WfChef / WfGen / WfSim
```

它本身不会：

- 调用 REST API；
- 请求建立网络；
- 配置 VLAN；
- 申请带宽；
- 查询 SENSE instance。

官方当前 schema 是一个数据交换格式，不是 workflow runtime 或 network controller。[WfFormat 官方仓库](https://github.com/wfcommons/WfFormat)，[WfCommons 官方文档](https://docs.wfcommons.org/en/latest/)

更准确地说，**JSON 文件不能自己与 SENSE 交互**。必须有一个程序读取 WfFormat，然后调用 SENSE API：

```
WfFormat
   ↓ 读取
adapter / workflow management system
   ↓ HTTP request
SENSE-O Intent API
```



## 我们真正要建立的交互

因此合理的系统关系应当是：

```
原生/扩展 WfFormat
  描述文件、任务和执行事实
             +
WfCampaign
  描述本次提交的 deadline、priority、bindings
             +
WfPlatform
  描述 node、link、capacity、latency、route
             ↓
       我们新增的 adapter
             ↓
       SENSE ServiceIntent
             ↓
       SENSE 建立网络服务
             ↓
data mover / telemetry / SENSE status
             ↓
adapter 将执行事实写回扩展 WfFormat
```

这里可能构成真正的研究贡献：不是继续给 WfFormat机械增加网络字段，而是定义一个可验证的转换闭环——**workflow/science-SLA 如何生成 SENSE intent，以及网络执行事实如何回填为 workflow provenance。**

---



# Wffomat在Wf家族中是否和实际controller对接？

> Wffomat本来是一种格式，在实际中肯定会和类似sense的控制器进行交互吧？在Wf家族中，用的是什么实际的控制器？

不一定。**一种格式可以只用于保存、交换和分析数据，并不必然直接连接控制器。** WfFormat 正是这种情况。

WfCommons 家族没有一个统一的“Wf 控制器”。它把实际执行交给外部的 workflow management system（WMS）。

实际上也不存在这样的路径：

- WfFormat->WfBench/translator → Pegasus、Nextflow 等 WMS->sense API->sense o->esnet
- WfFormat->WfBench/translator → sense API->sense o->esnet?



## 实际关系

```
                         ┌─ WfChef：分析、学习 workflow 特征
workflow logs → WfFormat ├─ WfGen：生成 synthetic workflow
                         ├─ WfSim/WRENCH：模拟执行
                         └─ WfBench translator
                                  ↓
                         Pegasus / Nextflow / Makeflow...
                                  ↓
                    HTCondor / Slurm / Kubernetes...
```

这里最接近“控制器”的是 **Pegasus、Nextflow、Makeflow 等 WMS**

## Wf 家族实际使用哪些执行系统

WfCommons 当前支持或涉及的实际 WMS 包括：

- Pegasus
- Makeflow
- Nextflow
- Snakemake
- TaskVine
- StreamFlow
- Airflow
- Dask
- Parsl
- PyCOMPSs
- Swift/T

WfBench 可以把 benchmark specification 转译成这些系统能够执行的代码；WfInstances 则能从其中一些系统的执行日志反向生成 WfFormat。[WfCommons 官方介绍](https://docs.wfcommons.org/en/latest/)，[WfInstances API](https://docs.wfcommons.org/en/latest/dev_api_wfinstances.html)

原始 WfCommons 论文的真实实验主要使用：

```
WfCommons synthetic workflow
           ↓
Pegasus 或 Makeflow
           ↓
Chameleon Cloud 上实际执行
           ↓
execution logs
           ↓
转换成 WfFormat
```

其中 Pegasus 的任务执行由 **HTCondor DAGMan** 管理。

## 三个不同的controller层次


| 层次                         | 例子                        | 控制什么                         |
| -------------------------- | ------------------------- | ---------------------------- |
| Workflow controller        | Pegasus、Nextflow、Makeflow | 哪个 task 何时运行、依赖关系、数据 staging |
| Compute/resource scheduler | HTCondor、Slurm、Kubernetes | task 在哪台机器/哪个容器运行            |
| Network orchestrator       | SENSE                     | 建立网络服务、端点、带宽、VLAN、路径         |




## WfFormat 在真实运行中常见的两种位置



### 位置一：执行完成后生成记录

这是 WfCommons 最成熟的用法：

```
Pegasus / Nextflow 实际执行
            ↓
        execution logs
            ↓
       WfCommons parser
            ↓
          WfFormat
```

此时 WfFormat 是 provenance/trace，根本没有控制运行。

### 位置二：作为 benchmark 或 simulation 输入

```
WfFormat / synthetic workflow
            ↓
 WfBench translator 或 WRENCH
      ↓                   ↓
实际 WMS 执行          模拟执行
```

即使如此，也通常要先经过 translator；Pegasus 或 Nextflow 并不一定原生读取通用 WfFormat JSON。

> 所以我的理解是：wfformat有作为output和input两种路。作为output时本质是真实实验的产物，由WMS产生真实数据，通过parser得到；作为input时目前仅作为wf家族的模拟器或者benchmark的输入，没有与真实平台，比如接管esnet的sense进行交互的先例。
>
> 在我的场景下，需要这一层workflow adapter来与sense进行交互。那些wms虽然多，但都不是adapter的角色。

---



# Adapter要干的小例子

```
workflow/science 语义
        ↓ 转换
SENSE 能理解的 network intent
```



## 例子1

```
WfFormat file size
+ WfCampaign fileDeadline
→ required bandwidth
→ SENSE bandwidth.capacity
```



## 例子2

```
WfFormat endpoint role
+ WfCampaign binding
+ WfPlatform node
→ SENSE terminal URI
```



## 例子3

workflow 里可能是：

```
taskA:
  output: 500GB
  location: UCR

taskB:
  input: taskA.output
  location: ORNL
  deadline: 8PM
```

adapter 转换后可能变成：

```
{
  "src_endpoint": "UCR-DTN",
  "dst_endpoint": "ORNL-DTN",
  "bandwidth": "20Gbps",
  "start_time": "18:00",
  "end_time": "18:30",
  "route_constraint": "ESnet path",
  "priority": "high"
}
```

然后调用：

```
SENSE API → SENSE Orchestrator → ESnet/site Resource Managers
```

最后网络 ready，WMS/data mover 才开始真正传输。

## 我们需要的完整结构

```
WfFormat
  workflow 结构、文件大小、执行事实
       +
WfCampaign
  本次提交的 deadline、priority、bindings
       +
WfPlatform
  节点、地址、链路和 topology
       ↓
workflow-network adapter
  1. 解析 endpoint
  2. 推导 bandwidth
  3. 转换 route/schedule
  4. 调用 SENSE API
  5. 跟踪 SENSE instance 状态
       ↓
SENSE Orchestrator
       ↓
ESnet / site Resource Managers
       ↓
网络 ready
       ↓
WMS / data mover 执行传输
       ↓
telemetry + execution logs
       ↓
回填扩展 WfFormat
```

事实上应该是两条链：

### 计算执行链：

```
WfFormat
→ WfCommons translator
→ Pegasus / Nextflow 等 WMS
→ task 与 data mover 执行
```



### 网络配置链：

```
WfFormat + WfCampaign + WfPlatform
→ 我们的 workflow-network adapter
→ 调用 SENSE-O Intent API
→ SENSE Orchestrator
→ Resource Managers
→ ESnet / site networks
```



### 二者的协调顺序是：

```
WMS 准备执行跨站点 transfer
        ↓
调用 workflow-network adapter
        ↓
adapter 从三个 schemas 生成 SENSE intent
        ↓
SENSE-O 完成网络 provisioning
        ↓
adapter 确认 network READY
        ↓
WMS 启动 data mover
        ↓
传输结果和 telemetry 回填 WfFormat


                         ┌→ WfBench translator → WMS → data mover
三个 schemas → coordinator
                         └→ network adapter → SENSE-O → ESnet

网络 READY 后，coordinator 才允许 data mover 开始传输
```

此处coordinator**只是一个逻辑角色，不一定是新组件。**

它负责协调：

```
网络 READY → 才允许 data mover 开始
传输完成 → 通知 SENSE 释放网络
```

为了保持简单，可以直接把 coordinator 合并进 workflow-network adapter

### 分成两条链后的问题

> 此时WMS是运行在sense之上的workflow controller，sense是一个网络搭建器，只负责网络的建立、观测和记录，不管上面运行啥。

方向对了 —— 拆成两条链解决了前面那个分层错误（Pegasus 被塞到 SENSE 之下）。但有四处我会改。

**1. 两条链不是平行独立的，必须画出两个交汇点**

否则你就丢掉了 science-SLA 闭环：

- **执行前（下行）**：WfCampaign 的 bindings / route / fileDeadline 触发网络链；而且有**顺序约束** —— 网络必须先 provision 好，data mover 才能开始搬。这正是 2.0.4 里 `workflow_phased`（propagate → commit）存在的理由，co-scheduling 就落在这个交汇点上。
- **执行后（上行）**：`bytes` / `duration` 来自**计算链**的 data mover，不来自网络链。它回写 `WfFormat.execution` 算 Real throughput。

所以形状不是两条并列的竖线，而是一个环：上端 WfFormat 分叉，下端由 data mover 观测汇回 WfFormat.execution。

**2. "WMS 运行在 SENSE 之上" 这个说法我会改掉**

它暗示了依赖 —— 但 workflow 没有 SENSE 也能跑（走 best-effort 网络，只是没有带宽保证）。更准确的是：**WMS 和 SENSE 是两个对等的 control plane，adapter 是唯一的耦合点**。这也正好对应你文档 3.6 的结论：需要补的只是 [A] 那一薄层。

**3. "SENSE 负责建立、观测和记录" —— 观测这一项要打折**

按你自己审计的 2.0.4，SENSE-O 侧真正拿得到的只有：`status` / `substatus`状态字符串、`verify` 的模型 addition/reduction 验证、`GET /intent/{uuid}`的 read-back。**没有可调用的 per-transfer telemetry**（`monitor` tag 无 operation，`/logging/logs` 不是结构化 metrics 接口）。所以写成「**SENSE 负责建立 + 生命周期状态 / intent 记录**」更站得住；真正的性能观测在计算链侧。

**4. 两个小的命名/归属问题**

- **WfBench 不是 translator**。WfBench 是合成 workload 生成器；把 WfFormat 转成 Pegasus DAX / Nextflow 的是 WfCommons 的 translator 模块。这是两个不同的东西，图上最好别用斜杠合并。
- **WfPlatform 应该同时供两条链读**。它描述的是平台整体：compute node/core 供计算链做 placement，links/capacityGbps 供网络链做可行性检查。现在只挂在网络链上是漏的。



### 转换 route/schedule

把 workflow 里的高层需求，转换成网络系统/SENSE 能理解的“路径请求”和“时间预约请求”。

#### **route = 数据传输走哪条网络路径。**

比如 workflow 里只是说：

> 从 UCR 的 DTN 把 500GB 数据传到 ORNL 的 DTN。

但 SENSE/ESnet 需要知道更网络化的信息，例如：

> source endpoint = UCR-DTN  
> destination endpoint = ORNL-DTN  
> bandwidth = 20Gbps  
> path constraint = avoid congested link / use ESnet path / use VLAN X  
> required service = L2/L3 circuit or virtual network

所以 **转换 route** 的意思是：

> 把 workflow 的 source/destination/data dependency 转换成网络里的 endpoint-to-endpoint path request。

它不是你手动决定每一跳路由器怎么走，而是你给 SENSE 一个网络意图，然后 SENSE Orchestrator / ESnet / site resource managers 去 provision path。

#### **schedule = 什么时候预留网络资源、预留多久、带宽多少。**

比如 workflow 里只有：

> 这个任务 deadline 是今晚 10 点，文件大小 2TB，优先级高。

adapter 要推导：

> 需要在 18:00–20:00 之间预留 30Gbps 网络带宽，保证数据传完。

所以 **转换 schedule** 的意思是：

> 把 workflow 的 deadline / priority / execution order 转换成网络资源预约时间。

例如：

```
Workflow requirement:
  transfer input data before Task B starts
  file size = 2 TB
  deadline = 10 PM
  priority = high

Converted network schedule:
  reserve 40 Gbps from 7 PM to 7:10 PM
  source = site A DTN
  destination = site B DTN
```

---



# WMS的位置以及sense的意义



## WMS 是中心化还是分布式？

**结论：逻辑上中心化控制，物理上分布式执行。**

典型结构如下：

```
         WMS controller
      保存 DAG 与任务状态
      决定下一步运行什么
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
   worker A  worker B  worker C
   执行task  执行task  执行task
```



### Pegasus 的例子

Pegasus 通常有一个中心的 **submit host**：

```
Submit host
  ├─ Pegasus Planner
  ├─ HTCondor DAGMan
  ├─ workflow 状态与日志
  └─ 提交远程 jobs
          │
          ▼
多个 compute sites / worker nodes
```

Pegasus 官方把 submit host 定义为安装 Pegasus 和 Condor DAGMan、提交 workflow 的机器；实际计算任务和部分数据 staging job 可以在远程站点执行。[Pegasus 运行架构](https://pegasus.isi.edu/documentation/user-guide/running-workflows.html)

所以它是：

- 中心控制：DAGMan 在 submit host 维护依赖和状态；
- 分布执行：task 分散在不同 worker/compute site；
- 分布数据：input、staging 和 output site 可以是不同机器。



### 中心控制程序运行在哪里？

都可能：

1. 用户自己的工作站——适合短实验和开发。
2. HPC 的 login/submit node——常见，但受站点运行时间政策限制。
3. 专门的 workflow server——更适合长时间生产运行。
4. 云端托管服务——例如托管的 workflow control plane。

生产环境更常见的是一个稳定的 submit/service host，而不是用户个人笔记本。

在我们的设计中，推荐：

```
workflow submit/service host
  ├─ WMS controller
  └─ workflow-network adapter
           ↓
       SENSE-O API
```

adapter 不应运行在每个 worker 上，因为它需要：

- 统一管理 SENSE instance；
- 保存认证信息；
- 避免不同 workers 重复申请链路；
- 协调网络建立和释放；
- 处理失败与重试。



## SENSE 是否是一种“需要时才调用的质量保障网络”？

> 每次文件调用，或者需要网络传输时都需要调用sense接口。我的理解是，其目的在于，sense本质是一种质量保障网络，你也可以选择不调用，就走best-effort的普通网络？但如果你想要保证质量，就得按需调用，不能说保障整个网络都是高质量的。

基本正确，更准确的表述是：

> **SENSE 把某些网络资源变成可发现、可请求、可调度的服务，为选定的数据流按需配置网络，而不是把整个网络永久变成高质量专网。**



### 不调用 SENSE

```
data mover
→ 普通 IP routing
→ ESnet/campus network
→ destination
```

只要两个站点本来可达，传输仍然可以进行。通常使用现有的 best-effort 网络服务：

- 不单独预留带宽；
- 不一定有专用 VLAN/path；
- 与其他流量竞争；
- 性能可能很好，但没有针对这个 workflow 的专项配置。



### 调用 SENSE

```
adapter
→ 请求 terminals + bandwidth + schedule + path
→ SENSE 进行资源检查和 provisioning
→ 建立特定 network service
→ data mover 使用该服务传输
```

SENSE 官方定位正是让 workflow 将网络作为一类可调度资源，而不是把网络当作不可见的基础设施。[SENSE 官方介绍](https://sense.es.net/)，[SENSE Architecture](https://sense.es.net/architecture)

不过，调用 SENSE 也不自动等于“文件吞吐有完整 SLA 保证”：

- 请求可能被拒绝；
- `qos_class` 可能仍然是 `bestEffort`；
- 只能控制已接入 SENSE 的网络域；
- 未接入的 campus/DTN 段仍可能是 best-effort；
- DTN、磁盘、TCP 和 data mover 也可能成为瓶颈；
- `bandwidth.capacity` 是网络请求，不等于最终文件吞吐。

因此更准确地说：

```
不调用 SENSE：
使用网络当前提供的普通服务

调用 SENSE：
请求为特定流量创建或调整网络服务

调用成功：
说明网络侧进行了相应配置
不必然说明应用最终达到目标吞吐
```



## 通常不是每个文件调用一次

假设有 10,000 个文件都要从 ANL 搬到 ORNL：

```
ANL → ORNL
总量：36 TB
deadline：1 hour
required bandwidth：80 Gbps
```

不合理的方式是：

```
每个文件
→ 创建一个 SENSE instance
→ 传输
→ 删除 instance
```

合理方式是：

```
把这 10,000 个文件聚合成一个 transfer campaign
         ↓
创建一个 ANL–ORNL SENSE service instance
         ↓
等待 network READY
         ↓
FTS/Globus/其他 data mover 传输全部文件
         ↓
完成后释放 SENSE service
```

也就是说，SENSE service 的粒度通常是：

- 一对端点；
- 一组相近的 bandwidth/SLA；
- 一个时间窗口；
- 一批数据传输。

而不是单个文件。

## 什么时候需要新建或调整 SENSE service？

```
同一端点 + 同一时间窗口 + 相近网络要求
→ 可以共享一个 SENSE instance

端点改变
→ 通常需要另一个 instance/connection

带宽需求显著改变
→ 更新 intent 或重新 provision

时间窗口结束
→ 释放 service

发生故障或重路由
→ adapter/SENSE 协调调整
```

因此最终系统更像：

```
WMS 发现未来有一批跨站传输
        ↓
adapter 聚合这些 transfer
        ↓
判断是否值得申请 SENSE service
        ├─ 否 → 直接走普通 best-effort 网络
        └─ 是 → 调用 SENSE，等待 network READY
                         ↓
                    启动这批传输
```

你的最后一句是准确的：

> **SENSE 不是保障整个 ESnet 永远为所有流量提供高质量服务，而是针对特定端点、流量、时间窗口和网络需求，按需编排相应的网络服务。**

它的核心价值可以浓缩成一句话：

> **把网络从“默认可用但不可控的通道”，变成 workflow 能够按需申请、协调和释放的资源。**通常不是“每传一个文件调用一次 SENSE”，而是“为一批具有相同网络需求的传输建立一次网络服务”。



## WMS和Sense的关系

> WMS是作为sense内部组件的一部分？

错。标准 SENSE 架构中，WMS 位于 SENSE 之上：

```
Pegasus / Nextflow / workflow agent
              ↓
     workflow-network adapter
              ↓
       SENSE-O Intent API
              ↓
       SENSE Orchestrator
              ↓
        Resource Managers
```

因此更准确的关系是：

> WMS 是 SENSE 的上层 client，而不是 SENSE 的内部组件。

WMS 负责：

- task dependencies；
- task scheduling；
- compute execution；
- 何时需要数据传输。

SENSE 负责：

- 网络资源发现；
- 网络路径计算；
- bandwidth/VLAN 等 provisioning；
- 多个网络域之间的协调。



### 可以把 adapter 放进 WMS

这是合理的：

```
Pegasus
  └─ SENSE plugin/hook
       └─ 调用 SENSE-O API
```

此时 adapter 在部署上属于 WMS 的一部分，但 SENSE 仍然是外部网络服务。

推荐边界是：

```
WMS
 ├─ 控制 task/data movement
 └─ 通过 adapter 请求网络

Adapter
 ├─ 理解三个 schemas
 ├─ 生成 SENSE intent
 └─ 协调 network READY 与 transfer start

SENSE
 └─ 控制网络服务
```

---



# 根据wms的adapter来指导我们设计sense api的adapter？

> 所以wf家族目前有一个wfformat->WMS的adapter，不存在到sense api的adapter？但是我们可以根据wms的adapter来指导我们设计sense api的adapter？

... ...

WMS translators 不能直接告诉我们怎样处理：

- terminal URI discovery；
- bandwidth 推导；
- SENSE instance 生命周期；
- asynchronous provisioning；
- network READY；
- cancel/rollback；
- actual network telemetry。

这些是 SENSE adapter 独有的问题。

---



# 为什么主流 WMS 没有直接接 SENSE

主因：SENSE 不是普遍可用的网络后端

### 1. 两边的抽象不匹配

WMS 通常知道：

```
task A 产生 file X
task B 需要 file X
把 file X 从 site A 搬到 site B
```

SENSE 要求的是：

```
source terminal URI
destination terminal URI
bandwidth capacity
VLAN/IP configuration
path constraints
network service lifecycle
```

WMS 中的 `site A` 并不等于 SENSE 的 `terminal URI`。必须有人完成：

```
WMS site/storage ID
→ physical network attachment
→ SENSE terminal URI
```

这就是 adapter 的核心工作。

### 2. SENSE 不是普遍可用的网络后端

Pegasus、Nextflow 要支持大量环境：

- Slurm
- HTCondor
- Kubernetes
- AWS/Azure/GCP
- 各种 HPC 和 campus clusters

而 SENSE 只在已经部署 Resource Manager、端点和相关权限的站点可用。WMS 开发者很难把这种特定网络设施作为默认功能。

### 3. WMS 通常把网络视为透明 IP 基础设施

传统 WMS 的数据传输逻辑是：

```
启动 Globus/FTP/HTTP/rsync transfer
→ 等待完成
```

它们默认：

> 只要 source 和 destination 可达，底层网络自己负责。

动态申请 VLAN、bandwidth 或 path 并不是传统 WMS 的职责。

### 4. 网络 provisioning 生命周期更复杂

如果直接集成，WMS 还要处理：

```
create SENSE instance
→ 等待 READY
→ 启动 transfer
→ transfer 失败/重试
→ 更新或保留 circuit
→ transfer 完成
→ cancel circuit
```

还要协调网络失败和 workflow 失败。这不是增加一个普通 HTTP 调用就能完成的。

## 已经存在的相近方案：DMM

SENSE 团队确实为 Rucio/FTS 做过这种工作：

```
Rucio
  ↓
Data Movement Manager（DMM）
  ↓
SENSE-O
  ↓
SiteRM / NetworkRM
  ↓
FTS / XRootD 执行传输
```

DMM 的论文明确把它定义为连接 Rucio 与 SENSE 的中间接口：

- 从 Rucio 获取 source site、destination site、transfer size 和 priority；
- 转换成 SENSE 请求；
- 申请 point-to-point network service；
- 把 SENSE 管理的 IPv6 endpoints 返回给 Rucio；
- 由 FTS/XRootD 执行真实传输；
- 使用 FTS 和主机指标监控吞吐。[DMM 论文](https://arxiv.org/abs/2508.00792)

相关演示甚至只需要在 Rucio 的 FTS submission 位置增加一个小 hook：

```
new_endpoints = query_dmm(rule_id)
transfer.replace(current_endpoints, new_endpoints)
transfer.submit_to_fts()
```

[CERN DMM 演示](https://indico.cern.ch/event/1338689/contributions/6010883/attachments/2952078/5189610/CHEP24_DMM.pdf)

这恰好证明：

> 即使 Rucio 已经非常了解数据传输，它仍然需要 DMM 作为 workflow/data-management→SENSE adapter。

---



# 潜在敌人：Rucio

> rucio也是一种WMS，如果是的话，在我们的场景下，似乎就不需要Wfformat/platform/campaign了？直接用rucio的workflow表示格式，用rucio来作为WMS不就好了吗，刚好也sense网络兼容？

不是。**Rucio 不是完整的 WMS，而是 Distributed Data Management（DDM）系统。**

它管理：

- 数据集和文件标识；
- 数据副本位于哪些存储站点；
- replication rules；
- source/destination RSE；
- transfer priority；
- 调用 FTS 等组件完成传输。

它不管理：

- workflow task DAG；
- task 之间的依赖；
- 计算任务何时、在哪里运行；
- task deadline；
- GPU/CPU 资源；
- workflow execution provenance。

简单区分：

```
Pegasus / TaskVine / Nextflow
= 计算 workflow 管理系统

Rucio
= 数据生命周期和跨站复制管理系统

FTS
= 实际文件传输服务

SENSE
= 网络服务编排系统
```

因此完整结构可以是：

```
WfFormat/WfCampaign/WfPlatform
              ↓
       Pegasus / TaskVine
              ↓ 需要跨站数据
            Rucio
              ↓
             DMM
       ┌──────┴──────┐
       ↓             ↓
     SENSE          FTS
   配置网络       传输文件
```

三个 schemas 与 Rucio 有部分重叠，但不能被它完全取代：


| 信息                                   | Rucio 能否表达 |
| ------------------------------------ | ---------- |
| 文件/数据集标识与大小                          | 能          |
| source/destination storage site      | 能，以 RSE 表示 |
| replication/transfer request         | 能          |
| transfer priority                    | 部分能        |
| task DAG 和计算依赖                       | 不能         |
| science task/file deadline           | 不能完整表达     |
| workflow endpoint role/binding       | 不能         |
| compute node/GPU 信息                  | 不能         |
| network links、capacity、latency、route | 不能         |
| 完整 workflow provenance               | 不能         |


如果我们的目标只是做一个“把数据从 A 搬到 B，并通过 SENSE 申请网络”的 demo，那么确实可以简化成：

```
Rucio → DMM → SENSE + FTS
```

这种情况下不需要先实现完整的三个 schemas adapter。

但如果目标是：

> 根据 science workflow 的任务、文件、deadline、平台绑定和 topology，自动决定何时、为谁申请怎样的网络，

那么三个 schemas 仍然是上游语义来源，Rucio/DMM 只是执行后端：

```
三个 schemas
→ 转换成 Rucio rule
→ DMM
→ SENSE
```

这条路线的好处是我们不必从零实现全部 SENSE 生命周期，只需实现较薄的一层：

```
WfFormat file
+ WfCampaign deadline/priority/bindings
+ WfPlatform node
→ Rucio dataset/RSE/rule/priority
```

另外，“Rucio 与 SENSE 兼容”目前准确说是：**已有 DMM 原型实现 Rucio–SENSE interoperation**，并非安装标准 Rucio 后就能直接使用；仍需要 DMM、Rucio patch、SENSE-enabled endpoints 和相应权限。[DMM 论文](https://arxiv.org/abs/2508.00792)

所以最准确的判断是：

> Rucio不能替代 WMS 和三个 schemas，但可以作为我们的 data-management backend；DMM 则可能帮助我们复用现有的 SENSE adapter。



## rucio如何使用Sense

> rucio作为一种分布式数据管理系统，是如何使用Sense的。或者说，有哪些场景需要用到sense？只有数据备份、迁移、数据库级别的访问、修改吗

不是数据库级别的访问或修改。**Rucio 只有在某项数据管理规则最终产生真实的跨站点 WAN 数据流时，才可能使用 SENSE。**

三者分工是：

```
Rucio：决定哪些数据应该出现在哪些存储站点
DMM：把选中的 Rucio transfer 转换成网络请求
SENSE：配置承载该 transfer 的网络服务
FTS/Globus：真正搬运文件
```



### Rucio 如何使用 SENSE

以“把数据集复制到另一个站点”为例：

```
1. 用户创建 Rucio replication rule
   “确保 dataset X 在 ORNL 有一份副本”

2. Rucio 检查
   ORNL 当前没有该副本

3. Rucio 创建 transfer requests
   source RSE = ANL
   destination RSE = ORNL
   bytes = 36 TB
   priority = 5

4. DMM 发现新的 Rucio rule
   读取 source、destination、bytes、priority

5. DMM 调用 SENSE
   查找两端可用的 SENSE endpoints
   计算应分配的 bandwidth
   请求建立 point-to-point circuit

6. Rucio 在提交 FTS 前询问 DMM
   DMM 返回由 SENSE 管理的 endpoints

7. Rucio 将 transfer 提交给 FTS
   FTS/XRootD 真正传输文件

8. DMM 监控 FTS 和网络吞吐
   必要时修改 bandwidth 或 transfer concurrency

9. Rucio rule 完成
   DMM 释放 endpoints
   circuit 暂时降到很低带宽以便复用，随后拆除
```

这是 DMM 论文描述的实际流程 dmm.pdf。

Rucio 官方文档也说明：replication rule 只描述希望维持的副本状态；Rucio 根据规则生成 transfer request，真正的数据移动由 FTS 或 Globus 等外部 TransferTool 完成。[Rucio replica workflow](https://rucio.github.io/documentation/started/concepts/replica_workflow/)，[Rucio transfers](https://rucio.github.io/documentation/operator_transfers/transfers-overview/)

### 哪些操作可能使用 SENSE？


| Rucio 操作                    | 是否需要 SENSE   | 原因                                                  |
| --------------------------- | ------------ | --------------------------------------------------- |
| 查询文件、数据集和副本元数据              | 否            | 只有数据库/API 查询，没有大量数据流                                |
| 修改文件标签或 metadata            | 否            | 不搬运文件                                               |
| 创建 replication rule，但目标已有副本 | 否            | 不会生成 transfer                                       |
| 创建 replication rule，目标缺少副本  | **可能**       | 会产生站点间传输                                            |
| 将数据集预置到未来计算站点               | **可能**       | 大规模 WAN data staging                                |
| 将数据从一个 RSE 迁移到另一个 RSE       | **可能**       | 产生跨站点 transfer                                      |
| 为容灾增加异地副本                   | **可能**       | 本质是大规模 replication                                  |
| 多站点分发实验数据                   | **可能**       | 会产生多个数据流，但当前 DMM 仅处理单 source/destination 的 P2P rule |
| 删除 replication rule/副本      | 通常否          | 删除存储数据不需要 WAN；但会触发已有 SENSE circuit 的释放              |
| 用户读取数据库中的记录                 | 否            | 与数据文件传输无关                                           |
| 应用直接读取远程文件                  | 当前 DMM 通常不处理 | 除非先转化为 Rucio-managed transfer/cache population      |
| 同一个站点内部复制                   | 通常否          | 不需要 SENSE 管理的 WAN service                           |




### “备份”不是最准确的说法

Rucio 的 replication 可以用于容灾和冗余，因此看起来像备份，但其核心语义是：

> 在指定的一组 RSE 中持续保证一定数量的数据副本。

例如：

```
dataset X
copies = 2
rse_expression = "tier=1"
lifetime = 30 days
```

Rucio 会根据规则决定是否需要创建新副本、从哪个源复制、目标放在哪里。[Rucio replication rules](https://rucio.github.io/documentation/started/concepts/replica_management/)

因此可使用 SENSE 的场景不只是备份和迁移，还包括：

- 实验数据向多个计算中心分发；
- 计算前将数据预置到目标站点；
- 高优先级数据集的紧急传输；
- 数据湖的副本重平衡；
- 大规模结果归档到异地设施；
- 为后续 workflow stage 填充远程 cache；
- 多个大流同时竞争端口容量时按 priority 分配带宽。



### 也不是所有 Rucio transfer 都调用 SENSE

DMM 原型中有类似这样的判断：

```
if rule_needs_sense():
    使用 DMM/SENSE endpoints
else:
    按原来的普通方式提交给 FTS
```

当前原型的限制包括：

- 只处理单 source、单 destination 的 point-to-point rule；
- 两个站点都必须有 SENSE-enabled endpoint；
- 主要面向高吞吐、跨 WAN 的科学数据流；
- 普通 transfer 可以继续走非 SENSE 路径；
- 当前仍是 controlled testbed/prototype，不是所有 Rucio 部署的默认功能。

所以最简洁的理解是：

> **Rucio 的 metadata/rule 操作本身不使用 SENSE；只有规则产生了值得优化的真实跨站点数据传输时，DMM 才调用 SENSE，为 FTS/XRootD 即将产生的数据流配置网络。**

---

# What SENSE-O has no field for

> · file / task identity, deadlines  
> · science-SLA and its evaluation  
> · measured throughput, RTT, bytes  
> **These objects set additionalProperties: false — no extra fields allowed.**
>
> 如何理解这三条？如何理解**additionalProperties: false？能否新增字段？能够通过回填的形式从DTN的recorder传递到collector来实现**measured throughput, RTT, bytes？

这三条的核心意思是：

> **SENSE-O 只描述和管理网络服务，不负责理解 workflow，也不负责保存文件传输的完整执行记录。**

## 1. `file / task identity, deadlines` 是什么？

假设 workflow 中有：

```
task: preprocess-01
file: detector-output
size: 36 TB
fileDeadline: "2026-08-29T10:00:00Z"
```

adapter 可以根据文件大小和 deadline 算出需要 80 Gbps，然后向 SENSE 提交：

```
connections:
  - name: anl-ornl
    terminals:
      - uri: urn:...:anl
      - uri: urn:...:ornl
    bandwidth:
      capacity: "80000"
```

SENSE 只看到：

```
ANL endpoint
ORNL endpoint
80 Gbps
```

它不知道：

- 这是哪个 file；
- 由哪个 task 产生；
- 哪个 task 将消费它；
- 文件必须什么时候传完；
- 它属于哪个 science workflow。

这些信息应保存在：

```
WfFormat：file/task identity
WfCampaign：deadline、priority、submission SLA
```

可以使用 SENSE 的 `alias` 或 `Connection.name` 放一个关联 ID，但它只是标签，不会让 SENSE 理解 file/task/deadline 的语义。

## 2. `science-SLA and its evaluation` 是什么？

例如 science-SLA 是：

```
detector-output 必须在 10:00 前到达 ORNL
```

adapter 推导出：

```
required bandwidth = 80 Gbps
```

SENSE 的职责只是尝试提供请求的网络服务。它不能判断完整的 science-SLA 是否完成，因为即使网络成功配置为 80 Gbps，文件也可能因为以下原因迟到：

- 源端磁盘读取慢；
- DTN 性能不足；
- FTS 并发数不合适；
- TCP 没有充分利用链路；
- 目标端写入慢；
- transfer 启动晚；
- task 本身执行晚。

因此 SLA evaluation 应由我们的 collector/evaluator 完成：

```
WfCampaign.fileDeadline
          +
实际 transfer end time
          ↓
deadline met / missed
```

例如：

```
slaEvaluation:
  targetDeadline: "2026-08-29T10:00:00Z"
  actualCompletedAt: "2026-08-29T10:06:40Z"
  status: missed
  latenessSeconds: 400
```

这不是 SENSE-O 的原生字段。

## 3. `measured throughput, RTT, bytes` 是什么？

SENSE 请求里的：

```
bandwidth:
  capacity: "80000"
```

表示请求 80 Gbps，不表示实际测到了 80 Gbps。

实际传输结束后可能得到：

```
bytes: 36000000000000
durationSeconds: 4000
averageThroughputGbps: 72
rttMs:
  p50: 3.8
  p95: 4.7
  p99: 5.2
```

这些属于观测结果：

- `bytes`：FTS、Globus或 data mover 的实际传输记录；
- `durationSeconds`：实际开始和结束时间之差；
- `throughput`：由 `bytes × 8 / duration` 计算；
- `RTT`：TCP socket、eBPF、perfSONAR 或网络 telemetry 的采样结果。

SENSE-O 2.0.4 没有标准化的 typed fields 来提交或读取这些结果。

## 如何理解 `additionalProperties: false`？

假设 schema 是：

```
Connection:
  type: object
  properties:
    name:
      type: string
    terminals:
      type: array
    bandwidth:
      type: object
  additionalProperties: false
```

那么下面合法：

```
name: anl-ornl
terminals: [...]
bandwidth:
  capacity: "80000"
```

下面不合法：

```
name: anl-ornl
terminals: [...]
bandwidth:
  capacity: "80000"
fileId: detector-output       # schema 未声明
measuredThroughputGbps: 72    # schema 未声明
```

`additionalProperties: false` 的意思是：

> 在这个 object 中，除了 `properties` 明确列出的字段以外，不允许出现其他字段。

注意它只对所在的 object 生效。例如 `Connection.additionalProperties: false` 禁止在 `Connection` 内增加字段；嵌套的 `bandwidth`、`terminal` 也可能各自有自己的限制。

## 能否直接新增字段？

对于当前 SENSE-O 2.0.4 请求，**不能随意新增**：

```
connections:
  - measuredThroughputGbps: 72   # 不应这样提交
```

即使我们在本地修改 YAML schema，真实 SENSE-O server 没有升级，仍可能拒绝该请求。

正式增加有三种方法：

1. SENSE 团队发布新的 API/schema 版本。
2. SENSE schema 正式增加类似 `extensions` 的可扩展对象。
3. 新增独立的 telemetry ingestion/query API。

对于我们的实验，最合理的是第三种思想，但 telemetry API 可以属于我们自己的 collector，不必修改 SENSE。

## DTN recorder → collector 能否实现回填？

**可以，而且这是推荐方案。** 但应该回填到我们的 execution/provenance 数据，而不是塞进 SENSE `Connection`。

```
WMS/adapter
  生成 transferId、fileId、senseInstanceId
             ↓
data mover 开始传输
             ↓
DTN recorder / FTS / telemetry
  记录 bytes、start/end、RTT samples
             ↓
collector
  聚合、关联、计算 throughput
             ↓
扩展 WfFormat.execution.transfers[]
             ↓
SLA evaluator
  与 WfCampaign deadline 比较
```

例如回填为本组扩展的 WfFormat：

```
execution:
  transfers:
    - transferId: transfer-001
      file: detector-output
      task: preprocess-01

      source: anl-dtn-01
      destination: ornl-dtn-01

      sense:
        serviceInstanceId: sense-instance-123
        connectionName: anl-ornl

      startedAt: "2026-08-29T09:00:00Z"
      completedAt: "2026-08-29T10:06:40Z"
      durationSeconds: 4000
      bytes: 36000000000000

      measured:
        averageThroughputGbps: 72
        rttMs:
          p50: 3.8
          p95: 4.7
          p99: 5.2
```

## Recorder 需要注意数据来源

一个 DTN recorder 不一定能独立获得所有指标：


| 指标                 | 最可靠来源                                    |
| ------------------ | ---------------------------------------- |
| 文件 identity        | WMS/data mover 提供的 `transferId`、`fileId` |
| 实际 bytes           | FTS/Globus/data mover job record         |
| start/end/duration | data mover job record                    |
| 平均 throughput      | collector 用 bytes 和 duration 计算          |
| 单个 TCP flow RTT    | socket TCP info、eBPF                     |
| 端到端 path RTT       | perfSONAR或专门的 telemetry                  |
| 整个网卡流量             | DTN interface counters                   |
| SENSE provision 状态 | SENSE-O status API                       |


只有网卡计数器时，通常无法区分：

```
哪些 bytes 属于 detector-output
哪些 bytes 属于其他用户的 transfer
```

所以必须让 WMS/adapter、data mover 和 recorder共享一个 `transferId`。

## 能否把观测结果反馈给 SENSE？

可以形成反馈控制，但不是向 `Connection` 增加 measured 字段：

```
collector 发现实际 throughput 只有 40 Gbps
              ↓
policy/controller 判断需要调整
              ↓
adapter 使用 SENSE 已有操作更新 network intent
              ↓
SENSE 调整 bandwidth/path
```

也就是：

```
观测数据保存在 collector/WfFormat
控制决策通过已有 SENSE API 发送
```

最终边界是：

```
SENSE-O：
保存和执行 requested network intent

DTN/FTS/telemetry：
产生实际观测

collector：
关联并聚合观测

WfFormat：
保存 workflow execution provenance

WfCampaign：
保存 science-SLA

SLA evaluator：
判断 SLA 是否满足
```

所以，`additionalProperties: false` 不会阻碍 DTN recorder→collector→WfFormat 的回填闭环；它只意味着：**不能把这些观测字段未经 API 设计就直接塞进 SENSE-O 2.0.4 的对象。**

