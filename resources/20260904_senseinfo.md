# SENSE-O Intent API 2.0.4 能提供哪些网络信息

## 证据边界

当前依据是 [SENSE-O Intent API 2.0.4 SwaggerHub](https://app.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4) 及其[原始 OpenAPI 定义](https://api.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)。

需注意：

- 2.0.4 是 SwaggerHub registry 的默认版本；
- 最后修改时间为 **2023-01-19**；
- registry 元数据标记为 `X-Published=false`；
- 因此它只能证明公开 schema 声明了什么，不能证明 2026 年实际部署完全相同。

## 1. Discovery API 明确返回的信息

`GET /discover` 返回全局已知 domain，以及每个 domain 的 edge points 和 peer points。

### Domain（网络域）

- `domain_uri`
- `domain_name`

`GET /discover/domains` 也可单独列出所有已知 domain。

### Edge point（边界端点）

`edge_point` 是一个 domain 对外暴露的服务边界端点，可以作为网络连接的起点或终点。

例如，它可能对应：

- 服务器或 DTN 的网络接口
- 校园网面向科研网络的接入口
- 数据中心对外提供的逻辑端口
- 可以终结 VLAN、L2VPN 或 L3VPN 的服务端点

当 workflow 请求“在站点 A 和站点 B 之间建立连接”时，通常用两个 edge point 的 URI 指定连接两端，SENSE 再计算中间经过哪些 domain 和链路。

```
"edge_points": [
        {
          "vlan_pool": "3600-3619",
          "ep_uri": "urn:ogf:network:maxgigapop.net:2013:s0:1_3:180-134.research.maxgigapop.net:eth1",
          "ipv4_pool": "172.16.2.0/30,172.17.2.0/30,172.18.2.0/30,172.19.2.0/30,172.31.6.0/24,172.31.7.0/24,172.31(...)",
          "ep_name": "n/a",
          "capacity": "100000"
        }
      ]
```



#### `ep_uri`

该端点在 SENSE/NML 模型中的唯一标识，例如：

```
urn:ogf:network:maxgigapop.net:2013:s0:1_3:180-134.research.maxgigapop.net:eth1
```

它用于 API 请求和模型关联。虽然 URI 中可能包含 domain、设备和端口信息，但程序最好将完整 URI 当作不透明的唯一 ID，不要依赖拆分字符串来理解它。

#### `ep_name`

端点的人类可读名称，主要用于界面显示、日志和人工识别。

它可能是 `n/a`、可能重名，也可能发生变化，因此程序引用端点时应优先使用 `ep_uri`。

#### `vlan_pool`

该 edge point 可以用于网络服务的 VLAN tag 范围，例如：

```
3600-3619
```

它表示在该端点建立二层连接时，可以从哪些 VLAN ID 中选择或申请标签。

这通常是端点公布的 VLAN 资源范围，不一定表示其中所有 VLAN 此刻都没有被占用。实际可用性还可能受到以下因素影响：

- 已有 reservation
- 请求的服务时间
- SiteRM 本地策略
- 路径其他端口的 VLAN 能力



#### `ipv4_pool`

与该端点关联的 IPv4 地址或前缀池，例如：

```
172.16.2.0/30,172.17.2.0/30
```

这些是可能分配或建议给服务使用的地址资源，不代表已经分配给当前 service instance。最终使用的地址需要从 intent response 或 manifest 中确认。

#### `capacity`

该 edge point 在 SENSE 资源模型中公布的容量。

这里需要谨慎：`discover` schema 将它定义成字符串，却没有提供对应的单位字段。因此不能仅凭这个字段确定它表示：

- 物理端口速率
- 可预约总容量
- 经过策略限制后的服务容量
- 当前剩余容量

其他 SENSE intent 中的 bandwidth capacity 使用 Mbps，但不能因此直接断定这里也一定是 Mbps。它更不能直接当作实时流量、实时利用率或实时可用带宽。

### Domain peer connection（域间对接）

`peer_points[]` 描述当前 domain 与相邻 domain 之间的对接关系。

这里的 peer 不一定是 BGP peer。它更一般地表示：

> 当前 domain 的一个边界端口，与另一个 domain 的边界端口在拓扑模型中相连。

例如，从 Domain A 的角度看：

```
Domain A                              Domain B
port_uri ───── inter-domain link ───── peer_uri
```

`port_*` 描述本 domain 一侧，`peer_*` 描述相邻 domain 一侧。SENSE 利用这些连接关系，将多个 domain 的局部拓扑拼成跨域路径。

`GET /discover/{domainID}/peers` 可查询某个 domain 与相邻 domain 的连接点。

```
"peer_points": [
        {
          "peer_vlan_pool": "3600-3619",
          "port_vlan_pool": "3610-3629",
          "peer_uri": "urn:ogf:network:es.net:2013::wash-cr5:6_1_1:+",
          "port_uri": "urn:ogf:network:maxgigapop.net:2013:s0:1_1:wash-cr5",
          "peer_name": "n/a",
          "port_name": "n/a",
          "peer_capacity": "5000",
          "port_capacity": "10000"
        }
      ]
```



#### `port_uri`

当前 domain 一侧互联端口的 SENSE/NML URI，也就是跨域连接的本地端。

#### `port_name`

当前 domain 一侧端口的人类可读名称。

它主要用于展示和诊断；程序关联资源时应优先使用 `port_uri`。

#### `peer_uri`

与 `port_uri` 对接的、相邻 domain 一侧端口的 URI。

`port_uri ↔ peer_uri` 这组关系告诉 SENSE 两个 domain 在什么位置相连。

#### `peer_name`

相邻 domain 一侧端口的人类可读名称，作用与 `port_name` 类似。

#### `port_vlan_pool`

当前 domain 一侧互联端口能够承载的 VLAN tag 范围。

#### `peer_vlan_pool`

相邻 domain 一侧互联端口能够承载的 VLAN tag 范围。

两侧的 VLAN pool 不一定相同。例如：

```
port_vlan_pool: 3610-3629
peer_vlan_pool: 3600-3619
```

这可能意味着：

- 两侧可用 VLAN 范围不同
- 互联处支持 VLAN translation
- 两个 domain 分别维护自己的标签空间
- 模型公布的是策略允许范围，而不是相同的物理 VLAN

因此，不能简单假设一项跨域服务在所有 domain 中都使用相同 VLAN ID。

#### `port_capacity`

当前 domain 一侧端口公布的容量。

#### `peer_capacity`

相邻 domain 一侧端口公布的容量。

两侧容量可能不同，因为它们可能受到不同设备能力、资源模型或本地策略的限制。

例如：

```
port_capacity: 10000
peer_capacity: 5000
```

即便单位相同，这段连接能够提供的有效容量也不会超过较小的一侧；完整端到端服务还会受到路径上其他端口、已有预约、时间窗口和 SiteRM 策略的共同约束。

与 `capacity` 一样，OpenAPI schema 没有在这些字段旁明确给出单位，也没有明确说明它们是物理速率、可预约容量还是剩余容量，因此不能直接将它们当作实时 available bandwidth。

### Discovery API 的信息边界

公开 API 至少描述以下信息：

```
有哪些 network domains
每个 domain 有哪些边界端点
哪些边界端点连接到其他 domain
端点/对等端口的标识符
可使用的 VLAN/IP address pools
端点或 peer port 的 capacity 字段
```

但它不是一张完整的内部 link-by-link topology graph：`DomainDescription` 没有普通内部 node、link、link adjacency 或 route sequence 的 typed schema。换句话说，`DomainDescription` 这个 API 返回类型只明确规定了 domain、edge points 和 peer points，没有规定一套结构化字段来完整描述 domain 内部拓扑，也没有规定一条计算路径必须以哪些 hop、按什么顺序返回。（这不代表 SENSE 内部没有这些信息，只代表 `DomainDescription` 的公开 OpenAPI 返回格式没有承诺把它们提供出来。）

#### 内部节点未纳入 typed schema

这里的内部 node 是 domain 内部参与拓扑或资源建模的节点，可能包括：

- 路由器
- 交换机
- 光网络设备
- 服务器
- DTN
- 计算集群
- 存储系统
- 虚拟交换机
- 其他被建模的网络或端系统资源

例如，一个 domain 的真实内部结构可能是：

```
Edge Point A
     │
Access Switch
     │
Core Router
     │
Border Router
     │
Peer Point
```

如果还包含计算和存储资源，可能是：

```
Compute Node ── ToR Switch ── Core Router ── Border Router
Storage Node ──────┘
```

但是 `DomainDescription` 没有类似下面这样的 typed 字段：

```
{
  "nodes": [
    {
      "uri": "...",
      "name": "...",
      "type": "router"
    },
    {
      "uri": "...",
      "name": "...",
      "type": "storage"
    }
  ]
}
```

因此，`/discover` 返回的 `DomainDescription` 不能直接列出 domain 内所有路由器、交换机、计算节点和存储节点。

#### 内部链路和邻接关系未纳入 typed schema

主要是在说内部连接，但也包括完整表达跨域连接所需的显式拓扑对象。`link` 是一段明确建模的连接，例如：

```
Switch A port 1 ───── Switch B port 7
```

一个结构化的 link 通常可能包含：

- link URI
- 两端端口
- 容量
- VLAN 能力
- latency
- direction
- layer/type
- operational state

假设 domain 内部有：

```
Edge Point ── Switch A ── Router B ── Border Router
```

完整拓扑需要分别表达：

```
Edge Point ↔ Switch A
Switch A ↔ Router B
Router B ↔ Border Router
```

但 `DomainDescription` 没有类似这样的字段：

```
{
  "links": [
    {
      "source": "switch-a:port-1",
      "destination": "router-b:port-2",
      "capacity": "100000"
    }
  ]
}
```



##### Peer connection 不等于完整的 link 对象

`peer_points[]` 确实提供了跨 domain 的边界连接关系：

```
Domain A 的 port_uri ↔ Domain B 的 peer_uri
```

但它仍然不是一个完整的、结构化的 link 对象。它主要告诉我们：

- 本 domain 的哪个边界端口连接出去
- 对端是哪个端口
- 两侧公布的 VLAN pool
- 两侧公布的 capacity

它没有完整描述：

- 这条连接的显式 link URI
- 链路方向
- 链路时延
- 链路状态
- 两端之间是否经过其他设备
- 链路的所有拓扑和性能属性

假设有一条连接：

```
port-A ───────── port-B
```

仅知道 A 和 B 相连，只能回答“拓扑上能不能到达”。要判断这条 link 能不能承载某项 workflow，还需要更多信息。

###### 1. Link URI：链路标识

`link_uri` 是链路的唯一标识，例如：

```
urn:ogf:network:es.net:link:denv-wash-1
```

它的作用是区分链路并建立稳定引用。

例如，A 和 B 之间可能不止一条链路：

```
        ┌── Link-1：100 Gbps ──┐
Node A ─┤                      ├─ Node B
        └── Link-2：400 Gbps ──┘
```

如果只有：

```
{
  "source": "A",
  "destination": "B"
}
```

就无法知道选中了 Link-1 还是 Link-2。

Link URI 可用于：

- 在路径中引用具体链路
- 查询链路属性
- 关联监控指标
- 记录 reservation
- 报告具体故障对象
- 表达 include/exclude path constraint
- 将不同系统中描述的同一条链路关联起来

例如：

```
{
  "link_uri": "link-2",
  "source": "A:port-2",
  "destination": "B:port-7"
}
```

这样才能明确服务使用的是哪条链路。

###### 2. 链路方向

链路可能是：

- 双向链路
- 单向链路
- 两个方向能力不同的链路
- 由两条单向 link 合成的双向连接

例如：

```
A ──100 Gbps──→ B
A ←──10 Gbps──── B
```

虽然物理上 A 和 B 相连，但两个方向的容量不同。

链路方向用于判断：

- A 是否能到达 B
- B 是否能到达 A
- 双向 service 是否可行
- 每个方向分别能预约多少带宽
- 回程路径是否可能不同
- 路由是否存在非对称性

对于数据传输，方向很重要。例如：

```
Storage A → Compute B：需要 100 Gbps
Compute B → Storage A：只需要少量控制流量
```

这种 workflow 的正向和反向需求并不相同。若模型只给出“A 与 B 相连”，就无法判断正向 100 Gbps 是否可用。

###### 3. 链路状态

拓扑中存在一条 link，不代表它当前可用。

链路状态可能包括：

- `UP`：正常工作
- `DOWN`：不可用
- `DEGRADED`：性能下降
- `MAINTENANCE`：维护中
- `UNKNOWN`：无法确认
- `ADMIN_DOWN`：管理员主动关闭

还可能区分两类状态：

- Administrative state：管理配置是否允许使用
- Operational state：设备实际检测到的运行状态

例如：

```
Administrative state: UP
Operational state: DOWN
```

表示管理员允许启用，但链路实际上已经断开。

链路状态用于：

- 路径计算时排除不可用链路
- 发现 provision 失败的原因
- 故障后重新计算路径
- 判断服务是否仍满足要求
- 避免将新任务调度到维护中的链路

如果没有状态信息，控制器可能在静态拓扑上算出一条路径，但这条路径实际上已经断了。

不过，状态也有时效性。几小时前的 `UP` 并不能证明现在仍然正常，因此状态字段通常还需要时间戳。

###### 4. 拓扑与适配属性

“拓扑属性”是指用于描述这条 link 在网络结构中扮演什么角色的信息，例如：

- source port 和 destination port
- 所属 domain
- 网络层次：光层、以太网层、IP 层
- link 类型：物理链路、逻辑链路、隧道
- VLAN 支持范围
- MTU
- encoding/encapsulation
- shared-risk group
- 是否支持 label switching
- 是否与其他 link 共享底层资源

这些信息决定两个问题：

1. 这条 link 能否与前后 link 拼接？
2. 它能否承载所请求的服务类型？

- 示例：VLAN 不兼容

```
Link A 支持 VLAN 100–200
Link B 支持 VLAN 300–400
```

即使拓扑上它们连续，也可能无法建立一个要求端到端保留同一 VLAN tag 的 L2 service，除非中间设备支持 VLAN translation。

- 示例：MTU 不足

```
Workflow 要求 MTU 9000
Link A MTU = 9000
Link B MTU = 1500
```

路径在拓扑上可达，但不能满足 jumbo-frame 要求。

- 示例：网络层次不兼容

一个 IP link、一个 optical link 和一个 VLAN switching link 不能仅凭“端点相连”就直接拼接。系统还必须知道中间是否存在合适的 adaptation，例如：

```
IP interface
→ Ethernet service
→ Optical wavelength
```



###### 5. 性能与容量属性

性能属性用于描述链路的传输能力和质量，可能包括：

- 总容量
- 可预约容量
- 当前利用率
- latency
- packet loss
- jitter
- error rate
- queue occupancy
- congestion state

这些属性具有不同语义。

- Capacity：链路最多能够承载的总流量。

例如：

```
capacity = 100 Gbps
```

- Reservable capacity：考虑已有预约和策略后，还能为新服务预约的容量。

例如：

```
physical capacity   = 100 Gbps
already reserved    = 70 Gbps
reservable capacity = 30 Gbps
```

它仍然不一定是实时空闲容量。

- Utilization：当前实际经过链路的流量。

例如：

```
current utilization = 45 Gbps
```

它是实时或时间序列测量，与 reservation 不同。链路可能预约了 70 Gbps，但当前只传输了 45 Gbps。

- Latency：流量通过链路所需的时间。

端到端路径时延通常近似为各段传播、传输、排队和处理时延的组合。

- Packet loss：链路上的数据包丢失情况。

即使带宽足够，高丢包也可能严重降低 TCP 或 GPU-to-GPU 数据传输性能。

- Jitter：时延的波动程度。

它对实时应用更直接，但也可能反映拥塞和队列变化。

这些性能属性用于：

- 判断路径是否满足 SLA
- 在多条可行路径中择优
- 找出瓶颈链路
- 检测性能退化
- 触发重新路由或任务调度调整

但需要区分：

```
静态/模型属性：capacity、reservable capacity
实时测量属性：utilization、RTT、loss、jitter
```

SENSE 当前公开的模型证据更偏向前一类，不能自动当作后一类。

###### 6. 物理链路与抽象链路

看到：

```
A ↔ B
```

并不一定意味着 A 和 B 之间只有一根物理线缆。

它可能表示三种不同粒度。

- **1. 物理直连**

```
A:port-1 ───── cable/fiber ───── B:port-2
```

A 和 B 是物理相邻设备。

- **2. 多跳但被抽象成一条逻辑 link**

```
A ── Switch X ── Router Y ── Optical Network ── B
```

上层模型可能将整段路径抽象成：

```
A ═════════ logical link ═════════ B
```

这种 link 可能代表：

- MPLS tunnel
- VLAN circuit
- optical circuit
- VPN
- 跨越一个 opaque domain 的逻辑连接
- **3. 经过未知的内部网络**

一个 domain 可能只公布入口和出口：

```
Ingress ── [domain internal topology hidden] ── Egress
```

对外部 orchestrator 来说，它是一个抽象 link；具体经过哪些设备只有该 domain 的本地控制器知道。

知道它是否经过其他设备有以下用途：

- 判断故障影响范围
- 判断两条路径是否真正独立
- 确认性能属性是单段还是聚合值
- 找到实际瓶颈所在设备
- 判断是否跨越多个管理或安全边界
- 避免把逻辑相邻误认为物理相邻

例如，两条逻辑 link 看起来独立：

```
A ══ Logical Link 1 ══ B
A ══ Logical Link 2 ══ B
```

但它们可能都经过同一根底层光纤：

```
             ┌─ Logical Link 1 ─┐
A ── Fiber X ┤                  ├─ B
             └─ Logical Link 2 ─┘
```

Fiber X 一旦中断，两条逻辑 link 会同时失败。因此，只看上层 link 无法证明路径具有物理冗余。

更重要的是，即使知道所有跨域 peer connection，也仍然不知道每个 domain 内部如何从入口走到出口。

例如：

```
Domain A                       Domain B
EP-A ── ??? ── port-A ║ peer-B ── ??? ── EP-B
```

`peer_points[]` 可以描述中间的：

```
port-A ║ peer-B
```

但 `DomainDescription` 没有描述两个 `???` 中的内部路径。

#### Route sequence 未纳入 typed schema

`route sequence` 是一条路径中经过的节点、端口或链路的有序序列，也就是逐跳路径。

例如，从端点 A 到端点 B，SENSE 可能计算出：

```
EP-A
→ Switch-A port 1
→ Switch-A port 8
→ Router-A port 3
→ Domain-A border port
→ Domain-B border port
→ Router-B port 5
→ Switch-B port 2
→ EP-B
```

如果用 link 表达，则可能是：

```
Link 1 → Link 2 → Inter-domain Link → Link 4 → Link 5
```

这里的“顺序”很重要。只有一组无序的端口或节点，无法确定：

- 流量先经过谁
- 从哪个入口进入 domain
- 从哪个出口离开
- 哪些 link 真正属于所选路径
- 哪一段是潜在瓶颈

`DomainDescription` 没有定义类似下面这样的返回字段：

```
{
  "route": {
    "hops": [
      {
        "sequence": 1,
        "node": "switch-a",
        "ingress_port": "port-1",
        "egress_port": "port-8"
      },
      {
        "sequence": 2,
        "node": "router-a",
        "ingress_port": "port-3",
        "egress_port": "port-7"
      }
    ]
  }
}
```

因此，仅通过 `DomainDescription`，应用无法恢复一条完整的逐跳路径。

## 2. 资源名称和 URI 解析

`GET /discover/lookup/{name}` 声明可以根据以下信息查找 domain_name，domain_uri，edge_points，peer_points：

- NML resource name
- tag
- `mrs:NetworkAddress`
- FQDN

`GET /discover/lookup/{uri}/rooturi` 可以查询一个资源所属的 root domain/topology URI。

这对 workflow adapter 很有价值：

```
workflow 中的站点或节点名称
            ↓ lookup
SENSE terminal URI
            ↓
用于创建 network connection
```

不过，`lookup` 的文档说返回 URI list，OpenAPI response schema 却引用 `DomainDescription`，两者不一致，实际返回格式需要实测。

## 3. 已有网络服务及其状态

`GET /discover/service/instances` 可以列出已有 service instance，包括：

```json
"instances": [
    {
      "type": "Dynamic Network Connection",
      "intents": [
        {
          "id": "a8848755-39cc-44db-a0ab-dc99f9daffcc",
          "json": "string",
          "provisioned": true,
          "creation_time": "Jun 21, 2021, 1:59:01 PM",
          "serviceInstanceUUID": "59e9624b-48e0-48dd-95b9-8c020046dffa",
          "serviceDeltaUUID": "875ceb85-7a03-4799-a8dd-23d7b883d527"
        }
      ],
      "alias": "DNC Pilot",
      "referenceUUID": "59e9624b-48e0-48dd-95b9-8c020046dffa",
      "state": "CANCEL - COMMITTING",
      "owner": "admin",
      "lastState": "PROPAGATED",
      "verification": "INIT",
      "timestamp": "2021/06/21 17:59:01",
      "archived": true
    }
  ]
```

此外：

- `GET /instance/{siUUID}/status`：返回完整状态字符串；
- `GET /instance/{siUUID}/substatus`：返回后端子状态；
- `GET /intent/{uuid}`：读回此前提交的 intent JSON，以及是否成功 provision；
- `GET /instance/{siUUID}/verify`：返回模型 addition/reduction 的验证结果。

这些是 **service lifecycle / provisioning 状态**，不是网络性能 telemetry。

## 4. 可以提交给 SENSE 的网络条件

以下字段是用户向 SENSE 提交的 intent，不是 SENSE 对当前网络状态的观测. 通过：

```
POST /instance/{siUUID}
```



### 提交完整 intent

首先取得一个新的 service instance UUID：

```
GET /instance
```

返回：

```
3b7d41e1-b37f-4c64-84d2-d307b5e47370
```

然后提交具体网络条件：

```
POST /instance/3b7d41e1-b37f-4c64-84d2-d307b5e47370?sync=true&proceed=false
Content-Type: application/json
Authorization: Bearer <token>
```

请求体是 `ServiceIntent`

```
ServiceIntent
├── service
├── alias
└── data
    ├── type
    └── connections[]
        ├── name
        ├── terminals[]
        │   ├── uri
        │   ├── vlan_tag
        │   ├── ipv4_prefix_list
        │   ├── assign_ip
        │   └── mac_address_list
        ├── bandwidth
        │   ├── capacity
        │   └── qos_class
        ├── schedule
        │   ├── start
        │   ├── end
        │   └── duration
        └── path_tprofile
            ├── inclusion_list[]
            └── exclusion_list[]
```

- 连接类型：
  - `Multi-Path P2P VLAN`
  - `Multi-Point VLAN Bridge`
  - `Multi-Point L3VPN`
- terminal URI
- VLAN tag
- IPv4 prefix
- MAC address
- bandwidth capacity
- QoS class：
  - `guaranteedCapped`
  - `softCapped`
  - `anyAvailable`
  - `bestEffort`
- connection start、end、duration
- included/excluded Path URI

其中 `bandwidth.capacity` 的明示语义是 **bandwidth limit in Mbps**。不能仅凭字段名把它解释成：

- 当前可用带宽；
- 剩余带宽；
- 实际分配带宽；
- 最低保证带宽；
- 实测 throughput。



#### JSON 文件的提交

JSON 文件作为 `POST /instance/{siUUID}` 的 HTTP request body 提交，不是单独的上传接口。

例如：

```
curl -X POST \
  "https://<SENSE-host>/instance/<siUUID>?sync=true&proceed=false" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  --data @intent.json
```

其中 `--data @intent.json` 就是提交本地 JSON 文件。

### Provision

在 combined workflow 中，intent 计算成功后，一般还要调用：

```
PUT /instance/{siUUID}/provision?sync=true&intent=last
```

也就是通用操作接口：

```
PUT /instance/{siUUID}/{action}
```

其中 `action` 可以是：

```
provision
cancel
reprovision
propagate
release
reinstate
commit
rollback
verify
...
```

因此通常流程是：

```
GET /instance
    ↓
获得 siUUID
    ↓
POST /instance/{siUUID}
    ↓
提交 intent、验证并计算服务
    ↓
PUT /instance/{siUUID}/provision
    ↓
实际下发网络配置
```

如果使用 two-phase workflow，则可能使用：

```
propagate → commit
```

而不是一次性 `provision`。这样更适合多个网络和计算资源的协同调度。

### 修改已有服务

如果 service instance 已经存在，希望修改带宽、时间或其他条件，使用：

```
POST /instance/{siUUID}/modify
```

请求体仍然是 `ServiceIntent`，例如将带宽改为 20 Gbps：

```
{
  "service": "dnc",
  "alias": "science-transfer-a-to-b",
  "service_profile_uuid": "456225c4-c549-4ca0-a585-a84247541315",
  "queries": [
    {
      "ask": "edit",
      "options": [
        {
          "data.connections[0].bandwidth.capacity": "20000"
        }
      ]
    }
  ]
}
```



## 5. 对初步结论的进一步核验

核验目标是确认完整 topology、selected path 或 allocated resources 是否存在于未类型化的 model JSON 或其他官方接口中。

最初仅检查 SENSE-O Intent API 2.0.4 的 OpenAPI schema 时，只能确认 `/discover`、service intent 和 lifecycle API 明确声明的字段。随后继续检查了官方 Python client、workflow 示例以及 manifest/SPARQL 查询模板。

进一步调查修正了部分初步判断：有些信息虽然没有独立的 typed REST endpoint，但可以通过通用 Intent Query 或 service manifest 获得；另一些信息在现有公开证据中仍未得到支持。

当前证据包括：

- [SENSE-O Intent API 2.0.4 OpenAPI](https://api.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)
- [SENSE 官方 Python client](https://github.com/sdn-sense/sense-o-py-client)
- [官方 workflow_interact.py](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/util/workflow_interact.py)
- [官方 sense_util.py](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/util/sense_util.py)
- [Workflow design 文档](https://github.com/sdn-sense/sense-o-py-client/blob/f306b49342fd812e866c438ca353e99dee34f95a/workflow_examples/docs/workflow_design.md)

这些证据仍然来自公开规范和官方代码，没有在具体的 2026 SENSE deployment 上完成端到端实测。因此，“官方代码支持”和“当前账户在实际部署中可以调用”仍需区分。

### 5.1 进一步核验后已经确认的能力



#### 5.1.1 查询指定时间窗口内的端到端最大可预约带宽

最初只检查 OpenAPI schema 时，没有找到专门的 available-bandwidth endpoint，因此不能确认 SENSE 是否能返回当前可用带宽。

官方 Python client 表明，创建 service instance 时可以在 `ServiceIntent.queries[]` 中提交：

```
{
  "ask": "total-block-maximum-bandwidth",
  "options": [
    {
      "name": "Connection 1",
      "start": "now",
      "end-before": "+1h"
    }
  ]
}
```

官方示例将这个操作描述为：

1. 为指定 terminal 计算一条可行路径；
2. 查询该路径在给定时间段内最多可以预约多少带宽；
3. 从以下路径读取查询结果：

```
$.queries[*].results[*].bandwidth
```

官方 client 将返回值除以 `1,000,000` 后显示成 Mbps，说明示例中的 query result 看起来以 bit/s 表示。

该查询用于判断给定端点和时间窗口内是否存在可行的端到端路径，并返回该路径最多可以预约的带宽。结果属于编排模型中的可预约容量，不是实时流量测量。

#### 5.1.2 获取 service instance 采用的部分路径资源

OpenAPI 没有定义类似 `selected_route.hops[]` 的 typed response，但官方 `sense_util.py` 提供：

```
--troubleshoot path-bandwidth -u <service-instance-uuid>
```

该操作为指定 service instance 创建 manifest，并查询其路径中的：

```
nml:BidirectionalPort
```

查询结果包括：

- 路径涉及的端口 URI；
- 端口的 `mrs:reservableCapacity`；
- capacity unit；
- 端口下的 VLAN sub-port；
- VLAN ID；
- VLAN sub-port 的 bandwidth/capacity。

SENSE 没有在普通 typed response 中返回完整 route，但可以通过 service manifest 查询该 service instance 路径涉及的端口和相关资源。因此，能够获得的是部分 selected-path 信息，而不是完整路径。

这些信息可支持部分路径分析，例如：

- 服务经过了哪些 modeled ports；
- 哪些端口可能构成容量瓶颈；
- 哪些 VLAN sub-port 属于该服务；
- 路径端口上还有多少模型容量。

但它仍不是完整且有序的物理 route，具体限制见 5.2。

#### 5.1.3 读取计算或 provision 后的 allocated service resources

SENSE 支持针对 service instance 提交 manifest template。Manifest template 使用 SPARQL 查询该服务的语义模型，并将结果整理为 JSON。

官方示例显示可以读取：

- service terminals；
- switching subnet；
- bidirectional ports；
- VLAN tag；
- IPv4 address；
- host port 和 alias；
- QoS 类型；
- `mrs:availableCapacity`；
- bandwidth unit；
- service start time；
- service end time。

例如：

```
?terminal nml:hasService ?bw_svc.
?bw_svc mrs:type ?qos_type.
?bw_svc mrs:availableCapacity ?bw_available.
?bw_svc mrs:unit ?bw_unit.
```

可以查询 terminal 关联的带宽服务、QoS 类型、available capacity 和单位。

```
?subnet nml:existsDuring ?lifetime.
?lifetime nml:start ?start.
?lifetime nml:end ?end.
```

可以查询该 service instance 的预约时间。

计算或 provision 后的部分服务资源可以通过官方支持的 manifest/SPARQL 机制读取，不必直接解析未定义的 `ServiceIntentResponse.model` 字符串。

这里的 allocated resources 主要指该 service instance 在语义模型中的服务资源，例如 terminal、VLAN、IP、subnet、端口、带宽元数据和时间范围。

#### 5.1.4 检查路径端口的模型容量和 VLAN allocation

`path-bandwidth` troubleshooting 查询首先读取路径端口的：

```
mrs:reservableCapacity
mrs:unit
```

然后读取各 VLAN sub-port 的：

```
mrs:reservableCapacity
mrs:unit
```

官方 client 将不同单位换算成 bit/s，并计算：

```
Remaining Capacity
    = Port Capacity
    - 路径端口上各 VLAN sub-port allocation
```

因此，在 service-instance 范围内，可以获得：

- modeled port capacity；
- VLAN sub-port allocation；
- client 计算的 remaining capacity。

由此可以查看 service-instance 范围内的部分路径资源分配。

但这里的 remaining capacity 是根据 SENSE 模型中的 capacity 和 allocation 计算出来的，不是从路由器端口 counter 直接测量出的实时剩余带宽。

#### 5.1.5 区分 orchestration state 与 configuration state

SENSE 可以返回 service instance 的 orchestration/lifecycle 状态，例如：

```
CREATE - COMMITTED
READY
```

当前官方 client 还会检查 configuration state，例如：

```
UNKNOWN
EXPIRED
STABLE
```

因此，可以判断：

- intent 是否成功编译；
- service 是否成功 provision；
- 数据平面配置是否达到 `STABLE`；
- service 是否已经过期；
- verification 是否成功。

这些状态可用于判断网络服务是否完成编译和部署。

但 `STABLE` 只表示配置状态稳定，并不证明实际吞吐、RTT 或 packet loss 达到了 workflow 要求。

#### 5.1.6 未类型化的 `model` 字符串不适合作为稳定接口

`ServiceIntentResponse.model` 在 OpenAPI 中只是一个没有内部 schema 的字符串。官方 CLI 默认还会删除该字段，只有 verbose 模式才保留：

```
if not args.verbose and "model" in response:
    response.pop("model")
```

没有在官方 client 示例中发现稳定解析该字段，并将其当作应用级 topology/path/resource API 的做法。

`model` 可能携带内部模型，但它没有稳定的结构承诺。读取 service model 时，应优先使用官方 manifest/SPARQL 机制，而不是让 workflow 直接解析 `model` 字符串。

verification response 中的以下字段也属于未类型化的模型字符串：

```
verified_reduction
verified_addition
unverified_reduction
unverified_addition
```

它们用于说明模型变更是否验证成功，不是网络性能 telemetry。

### 5.2 进一步核验后仍未确认的能力



#### 5.2.1 完整的全局内部 topology API

进一步检查 manifest 后，可以确认 service instance 相关的端口和资源能够被查询，但仍没有发现一个稳定的 Northbound typed API，可以一次返回：

- 所有 domain 内部 node；
- 所有内部 port；
- 所有内部 link；
- link 两端关系；
- 完整 adjacency graph；
- node/link 的统一类型和属性；
- 跨越全部 domain 的全局拓扑图。

`GET /discover` 返回 domain、edge point 和 peer point 摘要，Manifest 查询特定 service instance 的模型；两者都不能用于下载 SENSE 当前掌握的完整 node-link topology graph。

官方 client 另有直接读取 SiteRM model 的接口，但这是 SiteRM 层级的 API，不是 SENSE-O Intent API 2.0.4 对 workflow application 明确提供的统一 Northbound topology 接口。其权限、部署范围和跨域完整性尚未确认。

#### 5.2.2 完整、有序的 selected route

`path-bandwidth` manifest 能够返回 service instance 路径涉及的 ports，但现有查询没有提供明确的：

- hop sequence；
- ingress/egress 顺序；
- 相邻 port 之间对应的 link；
- 每一跳所属的 node；
- 从 source 到 destination 的严格顺序；
- 正向与反向 route；
- 底层物理光路或设备序列。

也就是说，目前能够获得的更接近：

```
该服务路径涉及的一组 modeled ports
```

而不是：

```
Hop 1 → Hop 2 → Hop 3 → ... → Hop N
```

SPARQL 示例也没有使用明确的 `ORDER BY`、sequence number 或 path-position 属性来恢复逐跳次序。

目前可以确认路径相关端口可见，但没有证据表明可以获得完整、有序且可稳定解析的 selected route。

#### 5.2.3 逻辑路径对应的完整物理路径

即使 manifest 返回了若干端口，也不能确认两个 modeled ports 之间是否：

- 物理直连；
- 经过未公开的内部交换机；
- 经过 MPLS tunnel；
- 经过 optical circuit；
- 穿越 opaque domain；
- 与其他逻辑路径共享同一底层光纤或设备。

因此，目前无法仅依靠 Northbound Intent API 判断两条逻辑路径是否真正物理独立，也无法直接得到 Shared Risk Link Group、底层光路或完整 failure domain。

这会限制以下用途：

- 判断路径冗余是否真实；
- 做精确故障定位；
- 计算共享风险；
- 判断两条备份路径是否会被同一物理故障同时影响。



#### 5.2.4 实时链路 utilization

目前没有找到 Northbound typed endpoint 返回：

- 当前发送速率；
- 当前接收速率；
- link utilization；
- interface counters；
- queue occupancy；
- congestion level；
- counter timestamp；
- utilization time series。

`mrs:reservableCapacity`、`mrs:availableCapacity` 和 client 计算的 `Remaining Capacity` 都属于资源模型或 reservation 语义，不能直接视为实时 utilization。

例如：

```
Physical capacity: 100 Gbps
Reserved capacity: 70 Gbps
Current traffic: 25 Gbps
```

这三个值表达不同信息。SENSE 当前证据能够支持前两类模型信息的一部分，但没有证明 Northbound API 能返回第三类实时测量。

#### 5.2.5 RTT、latency、packet loss 和 jitter

没有在 SENSE-O Intent API 2.0.4 的 Northbound endpoints、typed response 或 manifest 示例中找到稳定返回以下指标的接口：

- one-way latency；
- RTT；
- packet loss；
- jitter；
- packet reordering；
- error rate；
- time-series performance measurements。

官方 client 中存在直接调用 SiteRM Debug API 的代码，支持的动作名称包括：

```
rapid-ping
rapid-pingnet
traceroute
iperf-client
iperf-server
tcpdump
```

这些能力仍不能视为 Northbound telemetry，原因是：

- 它们属于 SiteRM Debug API，不是 SENSE-O Northbound Intent API；
- 每个 SiteRM 可以动态决定支持哪些 action；
- workflow application 是否拥有直接访问权限尚未确认；
- debug result 的统一数据格式尚未确认；
- 单次 ping、traceroute 或 iperf 不是持续 telemetry；
- 多个 domain 是否都允许执行这些操作尚未确认。

因此，不能据此声称 SENSE-O Northbound API 已经提供统一的 latency/loss/throughput telemetry。

#### 5.2.6 实际端到端 throughput

最大可预约带宽表示模型认为该路径在指定时间范围内最多还能预约多少资源；它不表示应用通过该路径实际能够传输多少数据。

实际 throughput 会受到很多不在 reservation 模型中的因素影响，例如：

- DTN 或 GPU NIC 性能；
- PCIe 或内存带宽；
- TCP congestion control；
- RTT；
- packet loss；
- MTU；
- parallel stream 数量；
- host CPU；
- storage read/write speed；
- 应用的数据块大小；
- 中间设备的实时排队和拥塞。

因此，SENSE 返回 100 Gbps reservable bandwidth，并不意味着 workflow 一定能测得 100 Gbps throughput。

#### 5.2.7 Discovery 中 capacity 字段的精确语义

`edge_points[].capacity`、`peer_points[].port_capacity` 和 `peer_points[].peer_capacity` 在 OpenAPI 中都是字符串，但没有对应的：

- unit；
- measurement timestamp；
- update frequency；
- physical/reservable/available 分类；
- direction；
- confidence；
- source。

因此仍然不能确定这些值究竟表示：

- 物理端口速率；
- 可预约总容量；
- 策略允许容量；
- 当前剩余预约容量；
- 某个历史时间点的模型值。

Intent 中的 `bandwidth.capacity` 明确定义为 Mbps，但不能据此自动推断 discovery 中所有 capacity 字段也使用 Mbps。

#### 5.2.8 实际 deployment 的接口与权限

公开 OpenAPI 2.0.4 最后修改于 2023 年，并标记为未正式发布；较新的官方 Python client 又出现了 OpenAPI 中没有完全体现的接口形式，例如 manifest 的 `/json` 变体和 SiteRM APIs。

因此还需要在实际部署上确认：

- 使用哪个 base URL；
- 实际 API 版本；
- OAuth/Keycloak role；
- workflow account 可以访问哪些 profile；
- 是否允许自定义 manifest/SPARQL；
- 是否允许查询 path ports；
- 是否允许直接访问 SiteRM；
- 各 SiteRM 支持哪些 debug actions；
- query result 和 manifest 的真实 JSON 格式；
- capacity 的单位和更新时间；
- topology 是否因授权范围而被裁剪。

在这些问题实测前，官方 client 的存在只能证明代码提供了相应调用方式，不能证明当前用户在所有部署中都能调用。

### 5.3 最终能力边界


| 网络信息                                   | 进一步调查后的结论                                        |
| -------------------------------------- | ------------------------------------------------ |
| Domain、edge point、peer point           | 已确认，由 Discovery API 提供                           |
| Terminal URI、VLAN/IP pool              | 已确认                                              |
| 指定时间窗口的端到端最大可预约带宽                      | 已确认，可通过 `total-block-maximum-bandwidth` query 获取 |
| 是否存在可行路径                               | 已确认，Intent Query 会进行可行路径计算                       |
| Service terminals、VLAN、IP、QoS、schedule | 已确认，可通过 manifest 查询                              |
| Service path 涉及的 modeled ports         | 已确认，可通过 `path-bandwidth` manifest 查询             |
| 路径端口的模型容量与 VLAN allocation             | 已确认                                              |
| Provisioning/configuration state       | 已确认                                              |
| 完整 domain 内部 topology                  | 尚未确认                                             |
| 完整、有序的 route sequence                  | 尚未确认                                             |
| 逻辑路径对应的底层物理路径                          | 尚未确认                                             |
| Discovery capacity 的单位和精确语义            | 尚未确认                                             |
| 实时 link utilization                    | 尚未确认                                             |
| Queue occupancy 和 congestion telemetry | 尚未确认                                             |
| RTT、one-way latency、loss、jitter        | Northbound API 中尚未确认                             |
| 实际端到端 throughput                       | Northbound API 中尚未确认                             |
| 统一的 time-series telemetry              | 尚未确认                                             |
| SiteRM Debug API 的跨站点可访问性              | 仍需部署实测                                           |


