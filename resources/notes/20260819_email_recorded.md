## 2. SciNet、SENSE 与 ESnet 的职责边界

邮件最重要的背景澄清是：SciNet 不负责底层网络工程。三者的职责应分为：

- **SciNet**：理解科学 workflow 的数据传输需求，将端点、数据量、时间窗口、带宽、优先级和 SLA 等信息转换为网络服务意图；比较 SENSE 返回的可行方案；监测网络服务状态；评估网络服务对科学任务结果的影响。
- **SENSE**：接收服务意图，判断可行性，协调多个网络域及其 Resource Manager，协商服务条件，并管理跨域虚拟电路的创建、修改、查询和释放。
- **ESnet 与各网络域运营方**：掌握网络拓扑、路径工程、域内策略、实际设备配置、故障保护和最终运行权限。

整体关系为：

科学 workflow → SciNet 科学意图层 → SENSE 跨域服务编排层 → ESnet/各网络域执行层。

“将 SciNet 的边界 northbound”意味着 SciNet 位于网络控制层之上。SciNet 提出“科学任务需要什么网络服务”，但不决定具体路径，也不直接配置路由器、P4 设备或 SmartNIC。

这项责任边界来自项目方的明确说明；邮件中更细的组件划分仍属于 AI 给出的架构建议，需要后续与合作方确认。

## 3. PydanticAI、DBOS 与 PostgreSQL 的分工

邮件最终建议在 Phase 1 使用 `PydanticAI core + DBOS Python + PostgreSQL`。三者不是并列的 agent，而是分别承担推理、流程执行和状态存储。

### PydanticAI：薄的类型化推理层

PydanticAI 只负责必须使用 LLM 的 Science Intent Adviser：

- 将 workflow 需求转换为结构化的 `ScienceWorkflowIntent`；
- 提出 `SenseServiceIntent`；
- 比较 SENSE 返回的方案；
- 输出置信度和解释。

它输出受 Pydantic 数据模型约束的结构化对象，而不是直接产生网络命令。授权、配额、状态管理、重试和网络控制不由 PydanticAI 决定。

### DBOS：权威的服务生命周期引擎

DBOS 负责从需求进入到服务释放的完整流程：

验证 → 生成意图 → SENSE 协商 → 等待结果 → 审批 → commit → 监测 → 修改/释放 → 记录结果。

DBOS 将流程拆成可恢复的 workflow 和 step，并将检查点保存到数据库。服务崩溃或重启后，可以从已完成步骤继续。因此，服务当前处于提议、协商、待批准、已提交、已开通还是已释放状态，应以 DBOS 记录为准，而不是以 LLM 对话历史为准。

外部写操作仍须使用幂等请求标识，防止系统在不确定请求是否成功时重复创建服务。

### PostgreSQL：持久流程账本

PostgreSQL 保存 workflow 输入、步骤输出、服务状态、SENSE 请求标识、审批结果、等待事件和恢复信息。它在该架构中不是向量数据库，也不用于存储大型科学数据，而是 DBOS 的可靠状态存储。

简化理解：

- PydanticAI 决定“建议申请什么”；
- DBOS 保证“申请流程可靠走完”；
- PostgreSQL 记住“流程已经走到哪里”。

明确 SciNet 位于 SENSE 之上后，真正需要 LLM 推理的核心任务较少，因此 Phase 1 没有明显理由采用复杂的多智能体框架。

## 4. 端到端控制流程

邮件架构图描述的是控制面，而不是科学数据的数据面。FastAPI、DBOS 和 PydanticAI 处理 workflow 元数据、服务意图、审批和状态；真正的科学数据通过 SENSE 建立的虚拟电路在仪器、DTN、存储和 HPC 之间传输。

完整控制流程为：

1. Workflow 或仪器系统提交端点、数据量、时间窗口、deadline 和优先级等元数据。
2. FastAPI 完成格式验证、身份认证、请求编号分配，并将请求交给 DBOS。
3. DBOS 创建持久 workflow，记录 received、validated、negotiating、awaiting approval、committing、active 和 released 等状态。
4. 普通程序执行端点、时间、配额、授权和数值计算等确定性检查。
5. PydanticAI 仅处理语义理解、方案排序和解释，并输出结构化建议与置信度。
6. 最终方案在 commit 前经过策略检查和必要的人工批准。
7. Typed SENSE adapter 将内部数据模型转换成 SENSE API 请求，并处理认证、超时、幂等键和结构化响应。
8. 协商阶段只检查可行性和调整方案；commit 阶段才开始实际 provisioning。
9. DBOS 等待回调或查询状态，在服务 active 后通知 workflow，并在结束时修改或释放服务、记录科学任务结果。

关键安全边界是：

PydanticAI 可以建议，但不能审批或直接 provisioning；commit 必须发生在确定性策略和人工审批之后。

需要向合作方核实邮件的具体 API 层次。SENSE 论文中的 pull model、propagate delta 和 commit delta 主要是 Orchestrator–Resource Manager 接口；SciNet 作为上层应用，更可能调用 SENSE Orchestrator 的 northbound service API，而不是直接调用各域 RM。

## 5. Agent 边界：只保留 Science Intent Adviser

邮件建议 Phase 1 从一个 agent 开始，而不是构建多 agent swarm。这里的 agent 专指包含 LLM 推理、输出存在不确定性的组件，而不是所有软件模块。

唯一的初始 agent 是 **Science Intent Adviser**，负责：

- 将 workflow 需求转换成结构化的 `ScienceWorkflowIntent`；
- 提出 `SenseServiceIntent`；
- 对 SENSE 返回的可行方案排序；
- 输出置信度和解释。

Adviser 只能提出建议。其输出还必须经过 schema 验证、确定性约束、授权与配额检查，以及必要的人工批准。模型置信度不能被当作安全证明，只能用于决定是否升级模型、请求人工判断或拒绝继续。

以下功能必须是确定性软件：

- Circuit Lifecycle Manager：DBOS 状态机；
- 授权和配额：普通 Python 与明确策略；
- 异常阈值：确定性监测；
- SENSE 提交和查询：幂等 DBOS steps；
- 网络保护和恢复：SENSE、ESnet 与各域运营方；
- 需求预测：首先使用常规机器学习模型。

系统可以包含很多组件，但不代表每个组件都应成为 agent。只有语义理解、模糊偏好提取和多方案解释确实需要 LLM。

邮件提出以后可以增加可选的 Outcome Evaluator。但应先用实际吞吐量、完成时间、deadline、SLA violation 和 GPU 等待时间等确定性指标评估结果；只有需要跨证据生成解释时，才考虑加入 LLM evaluator。

## 6. SENSE typed tool surface

邮件建议 Phase 1 只通过窄的 typed functions 与 SENSE 交互：

1. `pull_resource_model`：取得 SENSE 按策略向调用方公开的抽象资源模型；不代表 SciNet 获得完整拓扑或底层路径控制权。
2. `propagate_service_delta`：提交候选资源变更供 SENSE 验证和协商；可以接受、拒绝或返回修改方案，但不实际 provisioning。
3. `commit_service_delta`：在确定性检查和审批完成后，要求 SENSE 实际配置已协商的资源。该操作通常是异步的，必须携带幂等请求 ID 并保存 commit receipt。
4. `query_service_status`：查询 provisioning、active、failed 或 released 等状态，也用于 SciNet 恢复后与 SENSE 进行状态 reconciliation。
5. `modify_service`：修改现有服务，但仍应经过可行性检查、策略验证和必要审批。
6. `release_service`：释放服务及资源；操作必须可安全重试并保留审计记录。
7. `record_workflow_outcome`：记录吞吐量、完成时间、deadline、SLA violation 和 GPU 等待时间等结果。它更可能是 SciNet 自身功能，而不是 SENSE 控制 API。

Phase 1 建议使用 HTTPX 实现窄的 typed client，而不是在特权 SENSE 接口外包装 MCP。原因是操作集合固定、权限较高、状态转换严格，需要明确 schema、审批、幂等性、审计和错误处理。MCP 并非天然不安全，但其动态工具发现和模型驱动选择在当前场景没有明显必要，并会增加部署与攻击面。

这些函数名属于邮件的架构建议，并不证明合作方已提供同名接口。特别是 pull model、propagate delta 和 commit delta 在 SENSE 论文中主要属于 Orchestrator–Resource Manager 协议。实现前必须确认 SciNet 实际获得的是 SENSE-O northbound service API 还是 model/delta API。

## 7. 其余推荐工具的职责与引入条件

邮件中的工具表不是要求一次性安装所有组件。

### 核心服务组件

- Pydantic v2：定义和验证 `ScienceWorkflowIntent`、`SenseServiceIntent`、审批结果和状态等结构化合同。
- JSON Schema：将数据合同暴露给其他语言、API 客户端和文档工具。
- FastAPI：提供 workflow 请求、状态查询、人工审批和 SENSE callback 的 HTTP 入口。
- HTTPX：实现调用 SENSE 的底层 HTTP 客户端；typed 能力来自外层 Pydantic adapter，而不是 HTTPX 本身。
- DBOS 与 PostgreSQL：执行并持久化服务生命周期。

Schema 验证只能检查字段和类型，不能代替身份认证、授权、配额或网络策略。

### 条件性语义模型组件

RDFLib 用于处理 RDF graph，pySHACL 用于验证 graph 是否符合 SHACL 约束。只有合作方让 SciNet 直接读取或生成 MRML/RDF resource model 或 model delta 时才需要它们。如果 SciNet 只调用高层 JSON northbound API，应避免把 SENSE 内部语义模型引入 SciNet。

### 身份与可观测性

- 人类用户通常使用现有 OIDC。
- SciNet 调用 SENSE 使用合作方指定的服务凭据和授权机制。
- OpenTelemetry 追踪 FastAPI、DBOS、模型调用、SENSE 请求和 callback。
- 优先接入已有 Prometheus/Grafana/Tempo，不为 Phase 1 单独建设大型监控平台。



### 测试

- pytest：确定性代码与状态转换。
- Hypothesis：自动生成边界输入，验证未审批不得 commit、重复 release 安全等系统属性。
- Pydantic TestModel：用可控假模型测试 agent 调用流程。
- Pydantic Evals：通过固定数据集评估真实模型的 intent 提取、方案排序、置信度和解释。
- SENSE stub：模拟协商、拒绝、异步 provisioning、重复 callback、响应丢失和恢复等情况。

TestModel 验证代码流程，不证明真实 LLM 的质量；真实模型质量必须通过 eval 数据集验证。

### 分析与预测

- Polars/Pandas + DuckDB：离线分析 workflow 到达、数据量、吞吐量、deadline、provisioning latency 和 GPU 等待时间。
- scikit-learn/XGBoost：建立需求预测的简单基线。
- PyTorch：仅在简单模型确实失败、数据充足且复杂模型有可测收益时引入。
- 默认使用小型 hosted LLM、低置信度时升级强模型只是初步策略，必须验证 confidence 校准、模型收益和数据合规性。

Phase 1 最小实现可先限于：

Pydantic + FastAPI + DBOS + PostgreSQL + HTTPX typed SENSE client + pytest + SENSE stub + 基础 OpenTelemetry。

其他工具由已经确认的接口和研究需求触发，不应仅因邮件列出就全部加入。

## 8. Phase 1 暂不引入的组件

邮件的 “Do not add initially” 表示这些组件当前没有对应的已确认需求，并非永远禁止使用。

- Microsoft Agent Framework、LangGraph、CrewAI：单个 Science Intent Adviser 不需要多 agent 编排；普通 DBOS workflow 已足以表达确定的生命周期。
- PydanticAI 通用 Harness：SciNet 只需要窄的 typed adviser，不需要 shell、文件系统、通用研究工具、动态工具发现或子 agent。
- MCP：特权 SENSE 接口操作集合固定且副作用明显，typed HTTP client 更容易约束权限、顺序、审批和幂等性。
- Kafka、Redis：DBOS + PostgreSQL 已覆盖 Phase 1 的持久 workflow、事件、等待和重试；只有出现实测吞吐瓶颈或独立事件流需求时再引入。
- Neo4j、向量数据库：当前没有图数据库或 RAG 需求，也不应复制 SENSE 的拓扑与资源模型。
- 专用 Kubernetes：不应仅为这个小型应用建设编排集群；如果合作方已有 Kubernetes，则可沿用。
- 完整 topology-level digital twin：可以使用合作方已有 NDT、SENSE negotiation 或局部 stub，但不应在责任边界尚未确认时重建完整网络镜像。
- 自托管 LLM：只有已有 GPU 和推理运维能力时才考虑；hosted model 仍需核实数据合规性。
- LLM-controlled provisioning/recovery：禁止让 LLM 直接 commit、配置设备或执行故障切换。LLM 只能提出建议，执行必须经过确定性策略、审批、DBOS、SENSE 和网络运营方。

从这些限制可以推导出一个最小 PoC：

一个 workflow 样例 → typed adviser → 确定性验证 → SENSE stub 协商 → 方案排序 → 审批 → DBOS 模拟 commit/异步状态 → 结果记录。

该 PoC 是对邮件架构的推导，不是已经确认的 SciNet 任务。实施前仍需核实 SENSE API、测试环境、workflow 输入和 Phase 1 的交付目标。

## 9. DBOS 与 Temporal 的阶段性取舍

DBOS 和 Temporal 都解决 durable workflow 问题，包括检查点、重试、等待、消息和崩溃恢复。邮件选择 DBOS 不是因为 Temporal 能力不足，而是因为 Phase 1 的 Python PoC 可能不值得承担独立 workflow 平台的运维成本。

DBOS 作为库运行在 FastAPI/PydanticAI Python 进程内，并使用 PostgreSQL 保存 workflow 和 step 状态。它已经能够支持 SENSE callback、人工审批、异步 provisioning、失败重试和进程重启恢复。

Temporal 通常需要独立的 Temporal Service、persistence 和 visibility store。自托管生产环境还需要负责部署、TLS、认证授权、namespace、监控、升级、归档和故障恢复。它更适合多集群恢复、多语言 worker、高级 workflow visibility 和独立多站点运行。

关键例外是：如果合作方已经运行一个正式、受支持、可供 SciNet 使用的 Temporal 服务，复用它的边际成本可能低于自行部署 DBOS + PostgreSQL，此时应立即评估 Temporal。

以下需求本身不足以证明必须使用 Temporal，因为 DBOS 也能处理：

- 长时间 workflow；
- 等待人工批准；
- 等待异步 callback；
- API 超时和重试；
- 进程崩溃恢复；
- 持久状态。

Phase 2 迁移也不是修改一个配置。DBOS 与 Temporal 的 workflow、step/activity、消息、重试和部署模型不同。应将 `ScienceWorkflowIntent`、`SenseServiceIntent`、`ApprovalReceipt`、`CommitReceipt` 和 `WorkflowOutcome` 等领域合同与具体执行引擎解耦，以降低未来迁移成本。

当前决策顺序是：

1. 先确认合作方是否已有可正式使用的 Temporal 服务。
2. 如果没有，Phase 1 默认使用 DBOS + PostgreSQL。
3. Phase 2 只有出现多集群恢复、跨语言 worker、高级 visibility 或独立多站点运营需求时，才重新评估 Temporal。



## 10. 旧 MAF + Temporal 方案的修订过程

邮件后半部分保留了旧架构的推理历史。AI 最初从 SciNet slides 中推断 SciNet 会负责 predictive scheduling、digital-twin verification 和 P4/SmartNIC/DPU execution，因此推荐：

Microsoft Agent Framework + Temporal + digital twin + OPA policy gate + deterministic action broker + P4Runtime/gNMI。

该设计依赖一个关键假设：SciNet 从科学需求一直负责到底层网络设备控制。

Harvey 随后澄清：网络工程由 ESnet 负责，跨域虚拟电路通过 SENSE 创建。这使 SciNet 的边界上移为 SENSE 之上的 science-intent 和 service-lifecycle 层。路径工程、设备控制、provisioning、保护切换和网络运行权限不再属于 SciNet。

AI 在第一次回应澄清时仍说 MAF recommendation stands，但邮件顶部更晚的 Revised verdict 进一步将方案收缩为：

PydanticAI core + DBOS + PostgreSQL。

因此，以下旧建议已被最终方案取代：

- MAF 是 Phase 1 最佳 harness；
- Temporal 是默认 lifecycle runtime；
- SciNet 直接调用 P4Runtime/gNMI；
- SciNet 需要网络 action broker；
- 完整拓扑 digital twin 是 commit 前的必经门；
- 每个功能都应成为独立 agent；
- 第一个 PoC 必须采用 MAF → twin → P4Runtime。

OPA 也不是最终方案的必需组件；最终方案只要求 approval/policy gate，Phase 1 可能用普通 Python 规则即可实现。

以下旧原则仍然有效：

- agent 只能生成 typed proposal，不能输出或执行网络命令；
- LLM 推理与确定性执行必须分开；
- commit 前必须有策略和审批门；
- 服务生命周期必须支持崩溃恢复、等待、重试和审计；
- 快速故障检测和保护切换不能依赖 LLM；
- PoC 必须覆盖崩溃、拒绝、重复 callback、commit 失败和安全释放等异常路径。

旧对话中的 ≤5 秒检测、≤30 秒恢复、HPE 10× latency improvement 和 quantitative gates 是 AI 对 slides 的转述。它们不能仅凭本邮件作为项目事实引用，必须回到原始 slides 或向项目方核实。

## 11. 邮件内容的证据等级

应将邮件内容分成四类。

### A. 项目边界事实

Harvey 明确说明：网络工程由 ESnet 负责，跨域虚拟电路通过 SENSE 创建。由此可以确认 SciNet 位于 SENSE 上方，不直接负责路径工程、设备控制、provisioning 和网络保护。

但邮件尚未确认 SciNet 具体调用哪个 SENSE API、由谁运行 SENSE-O、怎样认证，以及可以读取和控制哪些服务状态。

### B. 官方资料支持的技术能力

官方资料支持以下能力：

- SENSE 使用 Orchestrator 和 Resource Manager 分层协调跨域资源，区分无实际 provisioning 的协商阶段与实际 commit 阶段。
- PydanticAI 存在 DBOS durable execution 集成；DBOS 可以使用数据库检查点恢复 workflow。
- Temporal 是包含 server、persistence 和 visibility 的独立 durable workflow 平台，自托管需要承担安全、监控、升级和恢复等运维工作。

这些事实只能证明工具具备相应能力，不能证明它们已被 SciNet 采用或一定是最佳选择。

### C. AI 架构建议

PydanticAI + DBOS + PostgreSQL、单一 Science Intent Adviser、FastAPI、HTTPX typed client、approval gate、小模型路由、测试工具、传统预测模型，以及暂不使用多 agent、MCP、Kafka、Kubernetes和完整 twin，全部属于候选设计，不是项目决定。

### D. 待确认事项

实现前至少需要确认：

1. SciNet 相对于 SENSE-O 的独特功能是什么。
2. Science Intent Adviser 是否真的需要 LLM，而非 deterministic mapper。
3. 实际 SENSE 接口属于 northbound service API 还是 model/delta API。
4. API schema、认证、callback、幂等、错误和测试环境。
5. 真实 workflow 输入、字段、调用方和模糊信息。
6. Phase 1 的可测成功指标。
7. 合作方已有 Temporal、PostgreSQL、Kubernetes、OIDC、监控、LLM、SENSE stub 和 NDT 中的哪些组件。
8. commit、modify 和 release 的权限与人工审批规则。
9. 合作方 digital twin 在 PoC 中的具体接口和角色。
10. 邮件所称九个月 Phase 1 与当前六个月加速阶段之间的时间表差异。

这封邮件最适合被视为：明确 ESnet/SENSE 责任边界后形成的 Phase 1 候选软件架构，而不是已批准方案或实验结论。

它最有价值的原则是分开 LLM 推理、确定性验证、人工/策略审批、durable lifecycle 和 SENSE/ESnet 网络执行。它尚未回答的核心研究问题是：

Science Intent Adviser 相比确定性程序究竟增加了什么可测价值？

## 12. 合作方会议的首要问题

在讨论 agent harness 前，应先问：

> Can you walk us through one concrete Phase 1 workflow—from the metadata available before a transfer, through the exact SENSE request SciNet is expected to produce, to the measurable scientific outcome—and identify which decision cannot be handled reliably by deterministic rules today?

这个问题要求合作方明确：

1. 输入：谁产生 workflow metadata、实际格式和字段是什么、哪些信息明确、哪些需要推断。
2. 输出：SciNet 调用哪个 SENSE endpoint、提交什么 schema、是否涉及 negotiation/reserve/commit/callback。
3. 当前 baseline：目前由谁完成转换、哪些步骤已经自动化、常见错误和人工修改是什么。
4. 智能位置：真正困难的是语义理解、需求预测、方案排序，还是可靠生命周期执行。
5. 成功指标：字段准确率、操作员修改次数、deadline 满足率、GPU 等待时间、恢复成功率或其他主要结果。

可能出现四种不同的问题类型：

- 模糊科学描述 → 评估 LLM adviser 相对 deterministic mapper 的收益。
- 明确需求但未来数据量未知 → forecasting 问题。
- SENSE 返回多个替代方案 → ranking/optimization 问题。
- intent 已明确但执行容易失效 → durable workflow 和状态一致性问题。

主问题回答后，再依次确认：

1. SENSE 实际 API、schema、sandbox、callback 和幂等语义。
2. commit 权限、人工审批、认证授权和数据合规。
3. network digital twin、SENSE stub 和测试路径。
4. 已有 Temporal、PostgreSQL、OIDC、OpenTelemetry、Kubernetes 和模型基础设施。
5. Phase 1 交付目标、UCR 模块、验收指标和六个月/九个月时间表差异。

正确顺序是：

真实 workflow → 输入输出 → 当前失败点 → 可测指标 → 判断需要规则/优化/ML/LLM/durable workflow → 最后选择框架。

因此，邮件之后最值得推进的不是立即实现 PydanticAI + DBOS，而是取得一个真实 workflow 样例和对应的 SENSE 接口合同。

## 13. OpenClaw 在邮件中的角色

OpenClaw 是 Harvey 用来阅读 SciNet slides、向 AI 提问、调用工具和导出对话的个人 AI agent 环境。它说明这份建议怎样产生，不是邮件最终建议部署到 SciNet 中的运行组件。

OpenClaw 管理模型、agent loop、工具、workspace、session 和消息渠道。邮件最终运行架构则是：

Workflow metadata → FastAPI → DBOS/PostgreSQL → PydanticAI adviser / validation / approval / typed SENSE adapter → SENSE → ESnet。

其中没有 OpenClaw。OpenClaw 的 session 和工具调用不能替代 DBOS 的 authoritative lifecycle、PostgreSQL 的持久状态、typed SENSE client 或 SENSE 的网络编排。

需要区分三类系统：

- Agent harness：围绕 LLM 运行推理和工具调用，例如 OpenClaw、PydanticAI、MAF。
- Durable workflow engine：可靠执行长期业务流程，例如 DBOS、Temporal。
- Network service orchestrator：协调跨域网络服务，例如 SENSE。

OpenClaw 以后理论上可以作为只读查询、结果总结或候选请求入口，但这需要单独评估。它不应直接获得 SENSE commit 权限，权威状态和执行仍应位于正式 SciNet 服务、DBOS和 SENSE中。

邮件后半段含有 Activity、工具调用、角色标签、调试文字、重复段落和未完成的文件生成说明，表明它是较原始的 AI session 导出，而非经过人工审定的正式架构文档。因此顶部 Revised verdict 应作为最终建议阅读，后半段只用于理解推理演化；关键事实仍需回原始项目材料核实。

## 14. 一页总结与判断

这封邮件建议将 SciNet 定位为 SENSE 之上的科学意图理解与服务生命周期层：

科学 workflow/instrument metadata
→ FastAPI
→ DBOS + PostgreSQL
→ deterministic validation / PydanticAI adviser / approval gate
→ typed SENSE adapter
→ SENSE Orchestrator
→ Resource Managers / ESnet。

SciNet 理解科学需求、生成服务意图、比较替代方案、跟踪服务状态并评估 workflow outcome。SENSE 负责可行性、协商和跨域服务生命周期；ESnet及各域负责路径工程、设备配置、保护恢复和网络运行权。

Phase 1 候选栈为 PydanticAI core + DBOS Python + PostgreSQL。PydanticAI 只作为单一 Science Intent Adviser；授权、配额、生命周期、异常阈值、SENSE调用和恢复均为确定性组件。Agent 只能生成 typed proposal，不能批准或执行 provisioning。

Microsoft Agent Framework + Temporal + digital twin + P4Runtime 是旧责任边界下的方案，已被顶部 Revised verdict 取代。Temporal 只在已有合作方服务，或 Phase 2 出现多集群恢复、跨语言 worker、高级 visibility和独立多站点运行需求时重新评估。

该方案的分层、安全边界和最小化思路合理，但它仍是候选架构，不是已批准项目方案。尚未确认实际 workflow输入、SENSE API、commit权限、digital twin接口、成功指标和 UCR交付模块。

最关键的未决问题是：

Science Intent Adviser 相比 deterministic mapper、优化器或传统预测模型，究竟增加了什么可测价值？

在选择 harness 前，应取得一个真实 Phase 1 workflow，明确输入、预期 SENSE输出、当前 baseline、失败点和可测科学结果。

---

# 这封邮件是否提到了刻画workflow的方法或者工具？

有提到，但只有高层思路和候选工具，没有给出一套可执行的 workflow characterization 方法。

具体来说，邮件把“刻画 workflow”隐含为：

```
Workflow / instrument metadata
        ↓
理解和预测科学需求
        ↓
提取 endpoints / timing / bandwidth / SLA / priority
        ↓
形成 typed ScienceWorkflowIntent
        ↓
转换成 SenseServiceIntent
```

邮件提到的刻画维度包括：

- 源端点和目标端点；
- 传输时间或时间窗口；
- 所需带宽；
- SLA；
- 科学任务优先级；
- 预测的未来需求；
- 网络服务与 workflow outcome的关联。

这些内容见邮件对 SciNet职责的描述：[原文 (line 263)](/Users/lxzhong/Documents/GitHub/genesis_scinet/resources/20260819_email.md:263)。

提到的候选工具有：


| 用途            | 邮件建议                                       |
| ------------- | ------------------------------------------ |
| 将需求转换成结构化表示   | PydanticAI `Science Intent Adviser`        |
| 定义 intent数据结构 | Pydantic v2 + JSON Schema                  |
| workflow特征分析  | Polars或 Pandas + DuckDB                    |
| 初始需求预测        | scikit-learn或 XGBoost                      |
| 更复杂预测         | 简单基线失败后才考虑 PyTorch                         |
| 评估 adviser    | Pydantic Evals、TestModel、pytest、Hypothesis |


相关工具表见[邮件第 54 行起 (line 54)](/Users/lxzhong/Documents/GitHub/genesis_scinet/resources/20260819_email.md:54)，`ScienceWorkflowIntent`见[第 74 行起 (line 74)](/Users/lxzhong/Documents/GitHub/genesis_scinet/resources/20260819_email.md:74)。

但是，邮件没有说明以下关键内容：

- workflow metadata具体来自哪里；
- `ScienceWorkflowIntent`有哪些字段；
- workflow是否表示成 DAG、事件序列或阶段状态机；
- 怎样从 workflow推导数据量、deadline和带宽；
- 使用哪些 telemetry和历史数据；
- feature具体怎样计算；
- forecasting的标签、时间尺度和模型输入；
- 如何验证 characterization是否正确；
- LLM方法相对于规则方法的 baseline是什么。

所以准确结论是：

> 邮件提出了“metadata → typed intent → SENSE intent”的概念框架，并列出了特征分析、预测和 schema工具，但没有给出真正的方法论、数据模型或算法。

而且 DBOS、Temporal、FastAPI主要用于执行和管理服务生命周期，不是 workflow characterization工具。邮件仍然没有回答最关键的问题：如何把一个真实科学 workflow系统地刻画成可测、可验证的网络需求。

