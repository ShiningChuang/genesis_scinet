# Network Agent 实现计划

逐步实现:每一步 = 一小块代码 + pytest + 讲解,用户看懂后再进入下一步。
运行测试:`.venv/bin/python -m pytest src/lib/network_agent/tests`

设计来源:`resources/slides/Agent Orchestration.pptx`、`resources/notes/20261014_networkagent.md`(三张图)、
`resources/meetings/20261015_network_agent_prototype.md`(与 KK 的修订)。

## 来自 10/15 会议的修订

| 会上的意见 | 代码里怎么落实 |
|---|---|
| `hold` 改叫 `reserve`(KK) | 代码统一用 `reserve`,注释对应 slides 的 `hold` |
| accept 之后容量在哪里扣减 | ledger 独立成模块,pending → confirm / rollback 显式写回 |
| validate 失败没有出口 | validate 失败直接 `respond(error)` → END |
| deviation 包括拥塞、逐渐变慢,要找出哪一跳 | 拓扑和 ledger 按单条链路建账(不按 slide 23 的 (src,dst) 对) |
| 多路径增容(path1 50 → 需要 100,加 path2) | 单独一步(第 8 步) |
| learning 先归因再校准,保留历史 | 图 C 顺序:join → attribute → calibrate |
| 工具和小 agent 可被多张图复用 | 逻辑写在普通模块里,图节点只做编排 |

## 步骤与进度

| # | 内容 | 产出 | LangGraph | 目标 | 状态 |
|---|---|---|---|---|---|
| 0 | 环境与骨架:venv、依赖、包结构、参数加载 | `config.py`、`tests/test_step0_smoke.py`、`env/pip/` | 否 | 10/20 前 | ✅ 2026-10-17 |
| 1 | 消息 schema(仅 planning 闭环):TransferRequest、QuoteRequest/Response、Offer、Reserve/Commit 请求与回执、Commitment、EndpointBinding、ErrorResponse。其余消息在首次用到的步骤再加 | `schemas.py`、`tests/test_step1_schemas.py` | 否 | 10/20 前 | ✅ 2026-10-18 |
| 2 | 拓扑与容量账本:站点/链路/路径;逐链路逐时间槽 observed/own/available;pending/confirm/rollback 事务 | `topology.py`、`ledger.py`、`tests/helpers.py`(demo 拓扑 APS→ANL→ESnet→ORNL + 虚构的第二条 transit 路径)、`tests/test_step2_topology_ledger.py`;config 加 `max_paths` | 否 | 10/20 前 | ✅ 2026-10-18 |
| 3a | Telemetry 一侧:模拟网络(他人占用、链路中断)、TelemetrySource 接口与 mock、LinkSample schema;账本改为 `apply(samples)` 写入 observed,观测值带过期时间 | `sim.py`、`telemetry.py`、`tests/test_step3a_telemetry.py` | 否 | 10/20 前 | ✅ 2026-10-19 |
| 3b | SENSE 一侧:SenseAdapter 接口(两阶段 propagate → commit,cancel;modify 移到 5b)与 mock(对照模拟网络准入、VLAN 分配、可注入失败);模拟网络分开存"他人占用"与"我们的预留";schema 补 Terminal、ServiceIntent、ServiceState | `sense.py`、`sim.py`、`tests/test_step3b_sense.py` | 否 | 10/20 前 | ✅ 2026-10-19 |
| 4 | 图 A quote 分支:validate_bundle → refresh_if_stale → find_placements → estimate_finish → respond;复现 slide 7 的 a1/a2/a3 | `graphs/protocol.py` | 是 | 10/20 前 | ⏳ 下一步 |
| 5a | 图 A reserve/commit:validate_op → recheck → place_on_circuit → compile_intent → ledger_pending → sense_call → confirm/rollback | 同上 | 是 | 10/20 前 | |
| 5b | modify/release(含 SENSE modify)、TTL 到期回收、重复请求幂等 | 同上 | 是 | 可延后 | |
| 6 | 端到端 demo:mock scheduling agent 驱动 quote → 选 offer → reserve → commit,两个 workflow 争用,打印 ledger 表(走 `run_experiment.py`) | `configs/` + `src/experiments/{tag}/` | 是 | 10/20 展示 | |
| 7 | 图 B Runtime:区分故障/拥塞/渐慢 → 逐跳扫描 → triage → 本地修复(复用第 5 步指令)→ repaired / at_risk | `graphs/runtime.py` | 是 | 之后 | |
| 8 | 多路径增容:找额外路径、拆分速率、增补方案;transport 侧留接口 | `multipath.py` | 是 | 之后 | |
| 9 | 图 C Learning:join_records → attribute_cause → calibrate(带状态标签)→ plan_adjustments → apply | `graphs/learning.py` | 是 | 之后 | |
| 10 | 第一个 LLM 接入点(可替换 policy 后):有证据的诊断 + 选下一次 probe,与规则版对比 | `policies/` | 是 | 之后 | |
| 11 | 与 Mininet / Telemetry Agent(另一位同学)对齐真实接口 | adapter | — | 之后 | |

## 待决

- slide 7 的 a1 算术疑似笔误:50 TB 以 40 Gbps 自 09:00 起传需 10000 s,应在 11:47 完成,slide 写 13:47(a2 = 13:07、a3 = 14:34 均吻合)。第 4 步复现时按算术结果。
- ~~observed 口径~~ 已在 3a 定为接口契约:observed = 不算我们自己预订时的可用容量(`schemas.LinkSample`)。接真实 SENSE / telemetry 时,由其 adapter 负责换算(例如 SENSE `maxReservableGbps` 若已扣掉我们的预留,需加回)。
- SENSE 的 `path_tprofile.inclusion_list` 语义待确认(Exp2 遗留问题):mock 把它当作强制路径;若真实 SENSE 只当偏好、实际走了别的路径,逐链路账本会与实际不符。
- 一个 ServiceIntent 只有一个带宽值;多段速率的 commitment 怎么落到 intent/circuit 上(拆成多个 intent、取最大值,或复用 warm circuit),在 5a 的 place_on_circuit / compile_intent 决定。
- mock SENSE 的 VLAN 池是全局一个,真实情况是每个端点各有可用 VLAN,两端需同时空闲。
- 路径枚举目前穷举所有无环路径,只适合 demo 规模;拓扑变大后换 Yen k 最短路径。
- 第 6 步 demo 走入口时需要一个实验 tag,届时 `docs/current_experiment_plan.md` 需从 Exp2 切换(换实验由用户决定)。
