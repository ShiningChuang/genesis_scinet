# SENSE-O Intent API 2.0.4 × workflow/science-SLA

> 状态：Exp2 调研进行中。本文是本次调研的唯一主产物；未完成复核的判断会明确标为“待验证”。

## 研究问题

SENSE-O Intent API 2.0.4 如何描述建立 virtual network link 所需的网络条件？本组 workflow/science-SLA 模型中的概念，哪些可以直接复用现有字段，哪些应由 adapter 推导，哪些确实需要最小扩展，哪些不属于 network intent API 的职责？

## 待验证假设

SENSE-O Intent API 2.0.4 已覆盖大部分网络侧原语；本组主要需要 workflow/science-SLA → network intent 的薄适配层，只应扩展经逐字段审计确认真正缺失的部分。

## 证据与优先级

1. SENSE-O Intent API 2.0.4 官方 OpenAPI/Swagger、官方文档和官方示例：决定 API 字段事实。
2. `resources/How to Describes a Workflow.pptx`：决定本组 workflow/science-SLA 模型；与下项不一致时以此为准。
3. `/Users/lxzhong/Documents/GitHub/paper_reader/knowledge/20260820_wfcommons.md`：补充设计理由和字段细节。



## 1. 当前结论摘要

第一轮 schema 审计得到的**阶段性观察**：

- SENSE-O 2.0.4 已直接提供 virtual network connection 的端点、带宽上限/QoS 类、连接时段、VLAN/IP 参数和路径 include/exclude 约束。
- 它没有声明 latency constraint，也没有 typed throughput/RTT telemetry response。
- `bandwidth.capacity` 的官方语义是 **bandwidth limit in Mbps**；在确认 `guaranteedCapped` 等 QoS class 的实现语义前，不能把它直接解释成 science-SLA 的“最低保证带宽”。
- 因此当前最可能的 harmonization 形态是：endpoint/route/部分 bandwidth 与 schedule 直接映射；role binding、file size + deadline → network request 由 adapter 完成；latency、精确 deadline 语义和执行 telemetry 暂列待确认缺口。

这些仍是第一次审计结果，尚未经过第二次覆盖复核，不能标为 ✅有效。

## 2. Science-SLA 侧基线（来自 PPT）

这张表先固定“我们需要表达什么”，暂不假定 SENSE-O 如何表达。


| 概念                           | 权威归属                                                | 本轮对接问题                                                |
| ---------------------------- | --------------------------------------------------- | ----------------------------------------------------- |
| link capacity                | `WfPlatform.links.capacityGbps`                     | SENSE-O 是否已有带宽/容量字段，其单位和方向性是什么？                       |
| link latency                 | `WfPlatform.links.latencyMs`                        | SENSE-O 是否接受 latency 约束，还是只返回/观测 latency？             |
| endpoint role                | `WfFormat` 文件的 `origin` / `destination` role        | role 不应直接冒充网络地址；由谁完成 role → node/port 映射？             |
| concrete endpoint binding    | `WfCampaign.bindings`                               | SENSE-O intent 需要哪种 endpoint 标识符？                     |
| placement                    | `WfCampaign.submissions[].placement`                | placement 是 intent 输入、adapter 输入，还是 network API 职责外？  |
| route choice                 | `WfCampaign.submissions[].route`                    | 能否复用 SENSE-O 的 route/path/topology 约束？                |
| workflow deadline / priority | `WfCampaign.submissions[].sla`                      | 是原样传递、用于 adapter 排序，还是推导网络时段/带宽？                      |
| task deadline                | `WfCampaign.submissions[].sla.taskDeadlines`        | 是否只在 workflow scheduler 内消费？                          |
| file deadline                | `WfCampaign.submissions[].sla.fileDeadlines`        | 如何与文件大小共同推导最低传输速率及最迟启动时间？                             |
| observed throughput          | `WfFormat.execution.transfers` 的 `bytes / duration` | SENSE-O response/telemetry 能提供哪些可读回事实？                |
| observed RTT                 | `WfFormat.execution.transfers.rttMs`                | SENSE-O response/telemetry 能提供哪些可读回事实？                |
| actual endpoints/path        | `WfFormat.execution.transfers`                      | intent 的 planned path 与 execution 的 actual path 如何关联？ |




### 2.1 PPT 优先后的解释口径

- link capacity/latency 是 platform 能力；实际 throughput/RTT 是 execution 事实。
- 面向具体文件的“所需 bandwidth/latency”不是另一个独立事实源，而应由 file size、deadline、候选拓扑等条件推导。
- WfFormat 的 endpoint 是角色；WfCampaign 才把角色绑定到具体 node；execution 记录实际 source/destination/path。
- 每个决策尽量同时保留“输入时的计划值”和“执行后的观测值”，但两者不能混为同一字段。



## 3. SENSE-O 2.0.4 官方资料范围



### 3.1 锁定的 schema

- 官方页面：[SENSE-O Intent API 2.0.4](https://app.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)
- 官方 Registry API 原始定义：[OpenAPI YAML](https://api.swaggerhub.com/apis/xi-yang/SENSE-O-Intent-API/2.0.4)
- 本 run 固化副本：`[sense_o_intent_api_2.0.4.yaml](sense_o_intent_api_2.0.4.yaml)`
- 下载时间：2026-08-26（America/Los_Angeles）
- Registry `Last-Modified`：2023-01-19 22:49:03 UTC
- 本地副本 SHA-256：`ec030cb314f69cf0577fc44ef0f208e5ae286c66f6fc7dec6511a733218b8a45`

该定义自报 `openapi: 3.0.2`、`info.version: 2.0.4`、title 为 `SENSE-O Northbound Intent API`。

### 3.2 与建链直接相关的生命周期


| 顺序  | API                                          | 作用                                                    | 与本轮关系                                                          |
| --- | -------------------------------------------- | ----------------------------------------------------- | -------------------------------------------------------------- |
| 1   | `GET /instance`                              | 生成 service instance UUID                              | 可作为一次 network service 的关联 ID                                   |
| 2   | `POST /instance/{siUUID}`                    | 用 `ServiceIntent` 创建 instance 或向已有 instance 添加 intent | 提交 virtual network connection 的主入口                             |
| 3   | `PUT /instance/{siUUID}/{action}`            | `provision` / `propagate` / `commit` / `cancel` 等操作   | 支持单阶段或适合 co-scheduling 的 two-phase workflow                    |
| 4   | `GET /instance/{siUUID}/status`、`/substatus` | 返回状态字符串                                               | 可轮询 provisioning 状态，但不是性能 telemetry                            |
| 5   | `GET /intent/{uuid}`                         | 读取已存 intent                                           | 返回关联 UUID、`provisioned` 和 JSON 字符串，可用于 intent read-back        |
| 6   | `GET /instance/{siUUID}/verify`              | 返回 verification model 字符串                             | 能证明模型 addition/reduction 的验证状态；schema 未提供 typed throughput/RTT |




### 3.3 官方客户端实例提供的补充证据

[SENSE 官方 Python client 的 workflow examples](https://github.com/sdn-sense/sense-o-py-client/tree/f306b49342fd812e866c438ca353e99dee34f95a/workflow_examples)（审计时 HEAD `f306b49`）实际使用：

- `data.connections[0].terminals[0|1].uri` 指定端点；
- `data.connections[0].bandwidth.capacity: 1000` 指定带宽；
- profile + `edit_template` 覆盖具体字段；
- 一个 service 的 manifest 输出可作为另一个 service 的 VLAN/IP 输入，说明 workflow tool 在 API 外还有一层编排与绑定。

这支持“本组 adapter/campaign 层负责角色绑定与多 service 组合”的方向，但不证明任何未写入 OpenAPI 的运行语义。

### 3.4 如何整体理解 SwaggerHub 页面



#### Instance 与 intent

- **service instance**：一项有生命周期的网络服务。例如“为 APS 与 ANL 建立一条 DNC”。它有稳定的 `siUUID`、状态和操作（provision、commit、cancel 等），也可以经历后续修改。
- **intent**：某次对该 instance 提交的“期望配置”。第一次 intent 可以创建它，后续 intent 可以修改它。因此一个 instance 可以关联多个 intents。
- **service delta**：SENSE-O 根据某次 intent 计算出的模型变化；`serviceDeltaUUID` 用来关联这次变化。

简化关系：

```text
一个长期存在的 service instance
    ├── intent 1：初始 APS ↔ ANL，80 Gbps
    ├── intent 2：修改为 60 Gbps
    └── intent 3：增加 ORNL terminal
```



#### 左侧标签不是不同的数据类型

SwaggerHub 左侧的 `workflow_combined`、`instance` 等是 OpenAPI `tags`，用于把 HTTP operations 分组。同一个 operation 可以同时出现在多个分组；例如 `POST /instance/{siUUID}` 同时标记为 `instance`、`workflow_combined`、`workflow_phased`，但它仍是同一个 endpoint。


| 左侧标签                | 含义                                                                             | 普通 workflow 用户是否会调用                                   |
| ------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `workflow_combined` | 单阶段、较少 provisioning 步骤的工作流视图；主要动作是 provision/cancel/reprovision                | 是；它是对相关 endpoints 的便捷分组                               |
| `workflow_phased`   | two-phase commit 工作流，适合 co-scheduling；主要动作是 propagate/release/reinstate/commit | 是；需要把“准备资源”和“正式提交”分开时使用                               |
| `instance`          | service instance 的 UUID、创建、状态、修改、验证和生命周期操作                                     | 是；这是建链的核心分组                                           |
| `profile`           | 可复用的 service-intent 模板及其许可；调用时只覆盖可编辑字段                                         | 会，尤其是基于管理员准备好的 profile 创建服务时                          |
| `intent`            | 按 UUID 读取某次已提交 intent                                                          | 会；主要用于审计和 read-back                                   |
| `discover`          | 查询 domain、edge point、peer、capacity、URI 和已有 service instance                    | 会；adapter 可用它把 node/role 解析成 SENSE URI                |
| `service`           | schema 声明为 service workflow methods                                            | 2.0.4 没有 operation 实际使用这个 tag；更像预留分类                  |
| `monitor`           | schema 声明为 monitoring methods                                                  | 2.0.4 没有 operation 实际使用这个 tag，不能视为已有可调用 telemetry API |
| `notify`            | 其他 SENSE 组件向 SENSE-O 回调 model/delta event                                      | 通常不是 science workflow 主动调用；更偏内部 callback receiver     |
| `logging`           | 查询或配置服务端日志、归档日志                                                                | 通常是运维/管理员接口，不是表达网络需求的接口                               |




#### 中间 YAML 与左侧 GET/POST/PUT/DELETE 的关系

中间的 `sense_o_intent_api_2.0.4.yaml` 是整份 **OpenAPI 接口契约的源文件**，主要有两部分：

```yaml
paths:                         # 定义“可以调用什么”
  /instance/{siUUID}:
    post:                      # 左侧显示的 POST /instance/{siUUID}
      requestBody:
        schema:
          $ref: '#/components/schemas/ServiceIntent'

components:
  schemas:                     # 定义“请求和响应里面长什么样”
    ServiceIntent:
      ...
    Connection:
      ...
```

所以两者不是两套东西：

```text
中间 OpenAPI YAML
   ├── paths                 → SwaggerHub 左侧生成 GET/POST/PUT/DELETE 目录
   └── components/schemas    → 每个 operation 的 request/response 数据结构
```

- `GET`：读取 UUID、状态、profile、intent 或 topology 等。
- `POST`：提交新 profile、service instance/intent 或 manifest。
- `PUT`：修改资源或触发生命周期 action，例如 provision/commit/cancel。
- `DELETE`：删除 profile 或 service instance。

science application 并不直接把配置发给交换机。完整链路是：

```text
WfFormat/WfCampaign
      ↓ 本组 adapter 生成 ServiceIntent JSON
SENSE-O Northbound API（POST /instance/{siUUID}）
      ↓ SENSE Orchestrator 解析 intent、生成 service delta
各 domain 的 Resource Manager
      ↓
实际网络设备/控制器
```

因此，左侧 operation 是“怎么把请求交给 SENSE-O”；`components/schemas` 中的 `ServiceIntent`、`Connection` 等是“请求中具体写哪些网络条件”。

### 3.5 `components` 的四类可复用定义

`components` 是 OpenAPI 的定义库，不是可以调用的 API。它里面的对象只有在 `paths` 或其他 component 通过 `$ref` 引用时才生效。

| component | 类比 | SENSE-O 2.0.4 中的作用 |
|---|---|---|
| `securitySchemes` | “怎么验明身份”的规则 | 定义名为 `oAuth2Keycloak` 的 OAuth 2.0 authorization-code 登录方式及 authorization/token URL；文件顶层 `security: - oAuth2Keycloak: []` 表示默认所有 operations 使用它 |
| `requestBodies` | 可复用的“请求表格” | 定义 `ServiceRequest`：必填的 `application/json` body，其内容遵循 `ServiceIntent` schema |
| `responses` | 可复用的“回复模板” | 定义 `Error`：供许多 `500` response 通过 `$ref` 共用；2.0.4 中它只有通用错误描述，没有结构化 error body schema |
| `schemas` | 数据类型/JSON 结构定义 | 定义 `ServiceIntent`、`DNCSchema`、`Connection`、`Path`、`Intent`、`VerificationResult` 等，并可层层引用 |

以 `POST /instance/{siUUID}` 为例，operation 与 components 的关系是：

```text
securitySchemes.oAuth2Keycloak
    └── 决定调用者如何认证

POST /instance/{siUUID}
    ├── request body → schemas.ServiceIntent
    │                       └── schemas.DNCSchema
    │                              └── schemas.Connection
    │                                     └── schemas.Path
    ├── 200 response → schemas.ServiceIntentResponse
    └── 500 response → responses.Error
```

四者的差别可以压缩为：

```text
securitySchemes：谁可以调用
requestBodies：请求整体怎么包装
responses：服务器可能怎么回复
schemas：请求/回复里面的数据对象长什么样
```

当前 2.0.4 有一个实现细节：`components.requestBodies.ServiceRequest` 虽然被定义了，但没有任何 path 通过 `$ref` 使用它；`POST /instance/{siUUID}` 是直接引用 `components.schemas.ServiceIntent`。这不影响理解，只表示作者建立了一个尚未复用的 request-body 模板。

### 3.6 SENSE 已有哪一层 adapter

“adapter”需要按方向区分：

```text
本组三个 schema
  WfFormat + WfPlatform + WfCampaign
              ↓
  [A] workflow/science-SLA adapter        ← 本组当前要定义
              ↓
  SENSE-O ServiceIntent / Northbound API
              ↓
  SENSE Orchestrator
              ↓
  [B] domain-specific Resource Managers   ← SENSE 已有
              ↓
  网络控制器、交换机、DTN 等本地资源
```

- **[B] SENSE 南向适配/执行链已经存在。** [SENSE 官方架构](https://sense.es.net/architecture)说明 Orchestrator 接收用户或应用请求、选择并协调 Resource Managers；各 RM 面向特定管理域或技术，负责配置和管理本地资源。[SiteRM 官方说明](https://sdn-sense.github.io/)也把 SiteRM 定义为全局 intent 与站点内可执行动作之间的连接层。
- **[A] 面向本组三个 schema 的 adapter 尚未见现成实现。** 当前核对的 SENSE-O 2.0.4 schema 与官方 Python workflow tool 都从 SENSE 自己的 profile、terminal URI、connection、bandwidth 等概念开始；没有读取 WfFormat/WfPlatform/WfCampaign，也没有实现 `file size + deadline → bandwidth/schedule` 或 role → terminal URI 的本组语义。
- **SENSE 官方 workflow tool 是客户端编排工具，但不是 [A]。** 它能用 profile、`edit_template` 和前一 service 的 manifest 输出组合多个 SENSE services；这可以被本组 adapter 调用或借鉴，但不会自动理解我们的 science-SLA。

所以本组不需要重做“如何把 intent 配到交换机”；需要补的是较薄的一层：把 science workflow 的角色、文件、deadline、placement 和 route 决策翻译为已有的 SENSE-O `ServiceIntent`，并保存 UUID/read-back 对应关系。

### 3.7 WfFormat 放在哪里、谁有权写 execution

WfFormat 是数据格式，不天然规定存储位置。建议的权威副本位于用户侧的 workflow/provenance control plane，而不是网络内部：

```text
用户 / workflow author
    └── 写 WfFormat.specification

workflow controller / provenance collector
    ├── 读 WfFormat.specification + WfCampaign
    ├── 调 SENSE-O 建立网络服务
    ├── 调 transfer service 启动文件传输
    ├── 用该 transfer job 的凭据读取完成事件、bytes、起止时间
    └── 写 WfFormat.execution

SENSE-O / Resource Managers
    ├── 管理网络服务和网络域内部资源
    └── 只返回获准暴露的 service state / network telemetry
```

这里的 data mover/transfer service 通常运行在 DTN 或 end host 上，属于数据传输执行层，不等于交换机、路由器等网络内部设备。终端用户不需要登录 DTN 或读取全网计数器；workflow controller 可以用 service account、delegated credential 或 transfer-job token，只读取本次 job 的状态与统计。

权限与所有权应分开：

| 数据 | 推荐权威来源 | 谁写入 WfFormat |
|---|---|---|
| 文件逻辑角色、预计大小 | workflow specification | 用户/workflow author |
| campaign binding、deadline、route decision | campaign manager | campaign manager 或 provenance collector |
| 实际 per-file bytes、startedAt、endedAt | transfer service 的 job record | workflow provenance collector |
| SENSE service/intent UUID 与状态 | SENSE-O API | adapter/campaign manager 写关联记录 |
| 端口计数、链路利用率、设备 telemetry | 获授权的 SiteRM/network telemetry | telemetry collector；作为网络侧证据，不冒充 per-file goodput |

如果 transfer service 不向 workflow controller 暴露 job 级 `bytes` 或时间，则本次 Real throughput 就是“不可观测”，应在 execution 中留空并记录缺失原因，不能用 WfFormat 预计文件大小或网络端口总流量伪造实际 per-file throughput。

网络内部可以保存自己的 telemetry，并可向 workflow provenance service 发布经过授权、最小化的观测摘要；但不建议让网络系统维护 WfFormat 的 canonical copy，因为它既不拥有 workflow specification，也通常不知道 file/task identity 和 campaign SLA 的完整语义。

## 4. Virtual network link 字段事实表

以下 JSON path 按 DNC 示例使用的 `data.connections[*]` 写法表示。


| JSON path                                | 类型 / 必填性                  | 2.0.4 明示语义                                                          | 审计备注                                                                                  |
| ---------------------------------------- | ------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `service`                                | string；`ServiceIntent` 必填 | service type；DNC 为 `dnc`                                            | 选择 DNC service                                                                        |
| `alias`                                  | string；`ServiceIntent` 必填 | instance label                                                      | 可读标签，不等于结构化 workflow ID                                                               |
| `service_profile_uuid`                   | string；可选                 | 链接到 profile UUID                                                    | 可复用既有 profile/template                                                                |
| `data.type`                              | enum；DNC 必填               | `Multi-Path P2P VLAN`、`Multi-Point VLAN Bridge`、`Multi-Point L3VPN` | 定义连接形态                                                                                |
| `data.connections`                       | array；DNC 必填              | service connections                                                 | 一个 intent 可含多条 connection                                                             |
| `data.connections[*].name`               | string；必填                 | connection label                                                    | 仅标签                                                                                   |
| `...terminals`                           | array；必填                  | connection terminals                                                | schema 未声明 `minItems`，不能仅凭 schema 断言必须恰好两个                                            |
| `...terminals[*].uri`                    | string；每个 terminal 必填     | terminal URI                                                        | concrete network endpoint 的核心字段                                                       |
| `...terminals[*].vlan_tag`               | string；可选，默认 `any`        | terminal VLAN tag                                                   | 可让 SENSE 分配或指定 tag                                                                    |
| `...terminals[*].ipv4_prefix_list`       | string；可选                 | IPv4 prefix list                                                    | 字符串格式未进一步结构化                                                                          |
| `...terminals[*].assign_ip`              | boolean；可选                | schema 标为 `TODO: clarification`                                     | 不应自行赋予更具体语义                                                                           |
| `...terminals[*].mac_address_list`       | string；可选                 | MAC address list                                                    | 逗号分隔并带 regex                                                                          |
| `...bandwidth.capacity`                  | string；可选，默认 `1024`       | bandwidth **limit in Mbps**                                         | 不是已证明的 minimum guarantee；类型为 string                                                   |
| `...bandwidth.qos_class`                 | enum；可选，默认 `bestEffort`   | network QoS priority                                                | `guaranteedCapped`、`softCapped`、`anyAvailable`、`bestEffort`；各 class 的保障细节未在 schema 定义 |
| `...schedule.duration`                   | string；可选                 | connection duration                                                 | pattern/example 不能提供足够精确的时区和时间语义                                                      |
| `...schedule.start`                      | string；可选                 | scheduling window start                                             | 示例是日期 `08/20/1998`，不是带时区的 timestamp                                                   |
| `...schedule.end`                        | string；可选                 | scheduling window end                                               | “window end”是否是最迟开通、连接撤销时间或两者之一，schema 未澄清                                            |
| `...path_tprofile.inclusion_list[*].uri` | Path URI array；对象存在时列表必填  | included paths                                                      | 字段名为 `path_tprofile`，内部注释却写 `path_profile`；description 仍为 TODO                        |
| `...path_tprofile.exclusion_list[*].uri` | Path URI array；对象存在时列表必填  | excluded paths                                                      | 可以表达显式 include/exclude，不能直接表达抽象 latency bound                                         |
| `suggest_ip_range[*].start/end`          | string；可选                 | IP range suggestion                                                 | 可用于 L3 地址建议                                                                           |




### 4.1 Discovery 与 read-back

- `GET /discover` 和 `/discover/{domainID}` 返回 domain、edge points、peer points、URI、VLAN/IP pools 与 `capacity`。
- discovery 中各 capacity 仍是 string，`DomainDescription` 没有声明单位；不能未经确认就与 connection 的 Mbps 等同。
- `GET /discover/lookup/{name}` 可按 resource name / network address / FQDN 查 URI，适合作为 role/node → terminal URI adapter 的一个候选步骤。
- `ServiceIntentResponse` 明确返回 `service_uuid` 和 `intent_uuid`；后者可通过 `GET /intent/{uuid}` 读回存储的 intent JSON。
- API 虽声明 `monitor` tag，但 2.0.4 schema 中没有任何带 `monitor` tag 的 path；verification response 也只有 model JSON 字符串，没有 typed bytes、duration、throughput 或 RTT。



### 4.2 Schema 自身需要保留的疑点

- `ServiceIntent.data` 的 `$ref` 指向 `DNCSchema`，而 `DNCSchema` 自身又包含顶层 `service` 和 `data`；这与官方 workflow example 使用的 `data.connections[...]` edit path 表面不一致。实际 request nesting 应以可运行 profile/manifest 或 SENSE 团队确认结果为准。
- `Connection`、`bandwidth`、`schedule`、terminal 和 path object 多处设置 `additionalProperties: false`；不能假设可随意塞入 workflow deadline、campaign ID 等字段。
- `ServiceIntent` 根对象没有明确写 `additionalProperties: false`，但“schema 没禁止”不等于部署实现承诺接收扩展字段。



## 5. Harmonization crosswalk

每个 science-SLA 概念只允许落入以下一种主分类：

- **A — 直接复用**：SENSE-O 现有字段已表达同一语义。
- **B — adapter 推导**：不扩 API；由 workflow/campaign 输入计算成 SENSE-O 现有字段。
- **C — 真正缺失**：现有字段与可靠推导均不足，才提出最小扩展。
- **D — 职责外**：只在 workflow scheduler、campaign manager 或 execution record 中保留。



### 5.1 第一轮分类


| Science-SLA / workflow 概念               | 初步分类                         | SENSE-O 2.0.4 对接方式                                            | 当前判断边界                                                                 |
| --------------------------------------- | ---------------------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------- |
| concrete endpoint binding               | A — 直接复用                     | `terminals[*].uri`                                            | WfFormat role 不能直接填入；URI 来自 WfCampaign binding / discovery             |
| endpoint role                           | B — adapter 推导               | role → bound node → SENSE resource URI                        | role 本身留在 WfFormat                                                     |
| VLAN / IP 条件                            | A — 直接复用                     | terminal 的 VLAN/IP 字段和 `suggest_ip_range`                     | `assign_ip` 语义仍待澄清                                                     |
| connection topology mode                | A — 直接复用                     | `data.type`                                                   | 已覆盖 P2P VLAN、multipoint L2/L3                                          |
| link/connection bandwidth               | A/B — 有条件复用                  | `bandwidth.capacity` + `qos_class`                            | 字段是 limit；minimum guarantee 需先确认 QoS class 语义                          |
| file size + file deadline               | B — adapter 推导               | 推导所需速率与时间窗口，再写入 bandwidth/schedule                            | 公式还需计入协议开销、并发和可用窗口；不能把 file deadline 原样冒充 connection end               |
| campaign route                          | A/B — 有条件复用                  | 转成 `path_tprofile` include/exclude Path URI                   | 抽象 route/site 名需先解析成 SENSE Path URI                                    |
| workflow/task priority                  | B 或 D — adapter policy / 职责外 | 可能按策略映射到 `qos_class`                                          | 两者不是天然同一枚举，禁止无策略直接等同                                                   |
| workflow/task deadline                  | B 或 D                        | 用于 adapter/scheduler 决定何时请求、请求多久                              | SENSE schedule 的 end 语义不足以直接等同 deadline                                |
| latency constraint                      | C — 候选缺口                     | DNC Connection 无 latency 字段                                   | 是否必须扩展，取决于路径选择是否需要显式 latency bound；尚未复核                                |
| planned/actual correlation              | A/B                          | `service_uuid`、`intent_uuid` + 本组 campaign/submission mapping | 可先在 adapter 外维护映射，不一定需要扩 API                                           |
| observed throughput / RTT / actual path | C 或 D — 候选缺口 / 职责外           | 2.0.4 无 typed telemetry path                                  | 需确认 SENSE model/其他 telemetry API 能否提供；当前不能声称 Northbound Intent API 已覆盖 |




### 5.2 当前最重要的语义分界

`file deadline` 不是 `schedule.end` 的同义词。前者是“数据必须在何时到达”的 science-SLA；后者在 schema 中只叫 scheduling window end。adapter 至少需要知道预计 bytes、可用传输时间和 bandwidth/QoS 语义，才能把上层 deadline 转成合法网络请求。

## 6. 真正缺失的最小扩展

第一次审计后只有以下**候选缺口**，均未通过第二次复核：

1. **Latency constraint**：DNC Connection 没有 latency bound；但若 bandwidth + schedule + path policy 已足以满足本轮 SLA，则不应为了“字段对称”而扩展。
2. **明确、可机器比较的时间语义**：schedule 使用普通 string，未声明 ISO 8601、时区，也未澄清 start/end/duration 的组合约束。优先考虑澄清/收紧现有字段契约，而不是另起一套 deadline 字段。
3. **Typed execution telemetry/read-back**：Northbound 2.0.4 没有 typed throughput/RTT/actual-path response。它可能属于独立 telemetry 接口而非 intent 扩展，需先查 SENSE model/monitor 能力。
4. **Bandwidth guarantee semantics**：当前缺的可能只是 `qos_class` 的官方语义说明，而不是新字段。只有当 `capacity + qos_class` 无法表达最低带宽或方向性时，才讨论扩展。

workflow ID、campaign ID、submission ID、task/file deadline 和 workflow priority 暂不列为 SENSE-O 网络 schema 的必加字段：可先由本组 adapter 维护与 `service_uuid` / `intent_uuid` 的关联，并把上层 SLA 转成现有网络原语。

## 7. APS → ANL → ORNL 端到端例子

具体例子单独维护在 `[example.md](example.md)`：

- [Example 1：Bandwidth capacity request 与 Real throughput 的完整闭环](example.md#example-1bandwidth-capacity-request-与-real-throughput-的完整闭环)
- [Example 2：同一 transfer 的三种 latency](example.md#example-2同一-transfer-的三种-latency)
- [Example 3：同一 workflow 的两层 SLA](example.md#example-3同一-workflow-的两层-sla)
- [Example 4：Endpoints 从三个 schema 映射到 SENSE-O terminals](example.md#example-4endpoints-从三个-schema-映射到-sense-o-terminals)
- [Example 5：把 transfers 投影到 links，得到 Spatial distribution](example.md#example-5把-transfers-投影到-links得到-spatial-distribution)
- [Example 6：把每条 link 的负载展开到时间桶，得到 Temporal distribution](example.md#example-6把每条-link-的负载展开到时间桶得到-temporal-distribution)



## 8. 边界与待确认项

- `guaranteedCapped` 是否表示对 `capacity` 的最低保证、上限，还是两者兼有？其他三种 QoS class 的 admission/保障语义是什么？
- `schedule.start/end/duration` 的确切格式、时区、组合规则和 lifecycle 语义是什么？
- 官方 OpenAPI 的 `ServiceIntent.data → DNCSchema(data, service)` 嵌套是否为 schema 错误，实际 POST body 应采用哪一层结构？
- `path_tprofile` 是否为稳定字段名；Path URI 指的是必须经过的路径、候选路径，还是某种预定义 policy/profile？
- verification model 或其他未列入 2.0.4 的接口，能否读回 actual path、allocated bandwidth、throughput 和 RTT？
- bandwidth 是否支持方向性、每 terminal/branch 不同容量，以及 multipoint 场景的 per-pair SLA？
- discovery `capacity` 的单位及其与 request `bandwidth.capacity` 的关系是什么？



## 9. 复核记录

- **2026-08-26，第一次审计**：逐段检查官方 2.0.4 OpenAPI 的 instance/intent/discover/verify paths，以及 `ServiceIntent`、`DNCSchema`、`Connection`、`Path`、`ServiceIntentResponse`、`Intent`、`DomainDescription`、`VerificationResult` schemas；并用官方 Python client workflow example 交叉检查实际 edit paths。
- **尚未完成**：独立第二次覆盖检查。关键缺口只有两次审计一致后才标记为 ✅有效。
