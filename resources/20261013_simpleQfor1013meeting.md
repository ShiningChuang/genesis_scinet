> “一位与会者（按内容可能为 Harvey）强调，想到 agent 不应立即等同于从头解决所有问题。Monitoring 已有许多工具，包括 John 之前提到的能力；实现应组合这些现有功能，agents 主要通过 API 使用它们。  
> 这样也能利用 DOE 组织（如 ESnet）已有工作，并借助 NRP。Mariam 认可 agents 的工具层主要会调用这些 APIs。”
>
> 我有些没分清楚，ESnet、NRP和SENSE都是同级别的网络管理平台吗？都有各自的API？

**不是同级别的三个网络管理平台。它们分别是网络设施、科研资源平台和编排软件。** 我前面把它们并列写成“这些 APIs”，确实容易让人混淆。


| 名称                                   | 它是什么                                                   | API 属于哪里                                     |
| ------------------------------------ | ------------------------------------------------------ | -------------------------------------------- |
| **ESnet** — Energy Sciences Network  | DOE 的科研广域网设施，同时有运营、研发团队，连接实验室与科研设施                     | 接口属于其具体服务，例如 OSCARS、SENSE；不是一个统一的“ESnet API” |
| **NRP** — National Research Platform | 分布式科研计算平台，提供 CPU、GPU、存储和服务；主要集群 Nautilus 使用 Kubernetes | 管理任务和资源主要通过 Kubernetes API；监控、LLM 等服务还有各自的接口 |
| **SENSE**                            | 跨网络、跨站点的资源编排软件，将应用需求转成端到端网络服务配置                        | 有明确的 SENSE Orchestrator API，供应用请求网络服务、查询状态等  |


定位依据：[ESnet 官方介绍](https://www.es.net/about/)、[NRP 官方文档](https://nrp.ai/documentation/)、[SENSE 官方介绍](https://www.es.net/network-r-and-d/sense/)。具体接口可见 [OSCARS 文档](https://www.es.net/engineering-services/oscars/how-it-works/)与 [SENSE Northbound API 文档](https://nrp.ai/SENSE.pdf)。

**NRP 和 SENSE 可以一起使用。** 例如，你在 NRP 的两个节点上运行计算任务，再通过 SENSE 请求连接它们的网络路径。NRP 官方就有这样的操作指南：先通过 SENSE 创建 L2 路径，再用 Multus 把该连接接入 Kubernetes Pod。[NRP 的 SENSE/Multus 指南](https://nrp.ai/documentation/admindocs/cluster/sense-multus/)

对你们的 agent，可以按“要做什么”区分接口：

- **启动计算任务、查看 Pod 状态** → Nautilus 的 **Kubernetes API**。
- **查看利用率、吞吐量等运行指标** → 对应的 **监控系统 API**；NRP 有 Grafana/Prometheus 等监控设施。[监控文档](https://nrp.ai/documentation/userdocs/running/monitoring/)
- **请求端点之间的网络连接** → **SENSE API**，由它进一步与下层 Resource Managers 对接。[SENSE 架构与接口](https://nrp.ai/SENSE.pdf)

所以，会上“利用 ESnet 已有工作、借助 NRP”的意思是：**复用 ESnet 团队开发的网络软件与工具，同时利用 NRP 提供的计算资源和现有服务。** 具体调用哪个 API，要落到某个软件或服务，而不能只按机构名字决定。

---

> 所以我的理解是：NRP是计算、任务和存储管理平台，SENSE是网路管理平台，某种意义上二者是同一个level。ESNet是底层的网络设施，NRP管理的计算节点都可以接入ESNet。然后SENSE和NRP都可以基于ESnet来跑。对吗？

**作为粗略的功能分工，大体对；但“都基于 ESnet”这部分需要修正。**

**1. NRP 和 SENSE 可以视为你们 agent 要对接的两类能力。**

- **NRP/Nautilus**：提供计算、存储资源，用 Kubernetes 管理任务。
- **SENSE**：编排端到端网络连接。

所以在你们的架构里，两者可以并列。不过严格说，NRP 包含实际硬件、服务和管理系统；SENSE 是编排软件。与 SENSE 更接近的管理组件是 **Nautilus 的 Kubernetes 控制面**。[NRP 官方定位](https://nrp.ai/about/)、[SENSE 官方定位](https://www.es.net/network-r-and-d/sense/)

**2. ESnet 是底层网络设施之一，不是 NRP 唯一的底层网络。**

NRP 的节点分布在不同机构，各自通过校园网、区域科研网等接入；跨站点通信可能涉及 CENIC、Internet2、ESnet 等多个网络。不能默认每个 NRP 节点都直接接入 ESnet。通过网络互联与 ESnet 上的站点通信，也不等于该节点归 ESnet 管理。[NRP 网络要求](https://nrp.ai/documentation/admindocs/participating/network/)、[NRP/SENSE 网络介绍](https://media.nrp.ai/6nrp-slides/Thurs%202pm%20Tom%20Lehman%20et%20al%20-%20SmartNIC%20Panel%20-%20January%2030%2C%202025.pdf)

**3. SENSE 可以编排经过 ESnet 的路径，也可以涉及其他网络。**

它通过各个网络或站点的 **Resource Manager** 协调资源。因此：

```
你们的 SciNet agent
  ├─ 调用 Kubernetes API → 在 NRP 节点上运行计算任务
  └─ 调用 SENSE API      → 协调站点和广域网资源，建立网络连接
                              └─ 可能涉及 ESnet、Internet2 等
```

这是概念上的调用关系。SENSE 能控制哪些资源，取决于哪些网络和站点接入了它、提供了什么能力及权限；并非网络可达就能控制。[SENSE 架构说明](https://www.es.net/assets/Uploads/76kkEi9wqPrVdrGK4bSFdg.pdf)

---

> "有人询问 UCR 团队是否能把已有的基础 agentic framework 分享出来，哪怕第一版只是 dummy agents、agent 的空骨架或接口。
>
> 请求的重点包括：
>
> - 有一个可插入 agents 的基础结构。
> - 不让 Mariam 重复处理 MCP servers 的搭建。
> - 复用 inference engines 与 agent 系统的连接。
> - 即使 agent 本体暂时没有完整逻辑，也可以先共享组织方式和可运行底座。"
>
> 1. MCP server是啥，在我们项目中的作用是什么
> 2. inference engines是啥

这两个组件分别解决 agent 的两种连接：**怎么调用模型，以及怎么调用外部工具。**

**1. MCP server：把外部能力提供给 agent 的程序**

MCP 全称是 **Model Context Protocol（模型上下文协议）**。MCP server 按统一协议告诉 agent 程序：“我提供哪些工具、参数是什么”，并接收工具调用、返回结果。这里的 *server* 指软件程序，可以在本地运行，也可以部署到远程机器。[MCP 官方架构](https://modelcontextprotocol.io/docs/learn/architecture)

在你们项目中，**一种可能的设计**是把已有 API 包装成 MCP 工具：


| MCP 工具示例                      | 内部实际调用                 |
| ----------------------------- | ---------------------- |
| `get_link_telemetry(link_id)` | 监控系统 API，读取链路状态        |
| `request_network_path(...)`   | SENSE API，请求网络连接       |
| `get_job_status(job_id)`      | Kubernetes 或其他任务系统 API |


这些工具名是示意。MCP server 负责把调用翻译给实际系统；**“何时查状态、是否申请新路径”仍由 agent 的规则或模型判断。**

你之前看到的 `APITool` 是普通 Python 函数包装。将这些功能通过 MCP 协议发布出去，才形成 MCP server。好处是多个兼容 MCP 的 agent 程序可以复用同一套工具接口。[MCP 工具发现与调用机制](https://modelcontextprotocol.io/docs/learn/architecture)

**2. Inference engine：实际运行模型、计算输出的软件**

*Inference* 就是“推理”：使用已经训练好的模型，根据输入生成输出。

例如：

- **模型**：Qwen、Llama 的模型权重。
- **推理引擎**：加载权重，在 CPU/GPU 上执行计算、生成 tokens 的软件，例如 vLLM。
- **推理服务**：在引擎外提供 API，让 agent 程序提交输入、取得模型输出。Ollama 也提供这类模型运行与 API 服务。[vLLM 服务文档](https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/)、[Ollama API](https://docs.ollama.com/api/introduction)

放在一起，就是：

```
Agent 运行程序
  ├─ 调用模型接口 → 推理服务 / 引擎 → 在 GPU 上运行 LLM
  └─ 通过 MCP client → MCP server → 监控、SENSE、任务系统 API
```

例如，agent 先经 MCP 查询链路状态，再把状态交给推理服务中的 LLM；模型提出调用某个网络工具，agent 程序再经 MCP 执行，并把执行结果交回模型。

所以会上请求共享基础框架，主要是在问：**能不能把“已经接好模型、已经接好工具、能运行这个调用循环”的程序骨架给 Mariam，让她和其他人专注补充各 agent 的业务逻辑。** 这段会议没有确定具体采用哪个推理引擎，也没有确认已有 MCP servers 的完整功能。

---

> "将这些功能通过 MCP 协议发布出去，才形成 MCP server"
>
> 用简单例子说明功能是怎么被发布出去的。

这里的“发布”就是：**把函数注册为工具，启动 MCP 服务，让连接过来的客户端能发现并调用它。**

例如，把下面代码保存成 `server.py`（返回的是演示数据）：

```
from mcp.server import MCPServer

server = MCPServer("SciNet Telemetry")

@server.tool()
def get_link_telemetry(link_id: str) -> dict:
    """查询指定链路的吞吐量和丢包率。"""
    return {
        "link_id": link_id,
        "throughput_mbps": 800,
        "loss_rate": 0.01
    }
```

关键是 `@server.tool()`。SDK 会把这个函数登记成一个工具，并从代码提取：

- **工具名**：`get_link_telemetry`
- **用途说明**：函数里的 docstring
- **输入参数**：`link_id`，类型为字符串

这些信息使客户端知道“有什么工具、什么时候用、怎么传参数”。不需要手写整套协议处理代码。[官方 Python SDK 示例](https://github.com/modelcontextprotocol/python-sdk)

安装对应 SDK 后，启动这个服务：

```
mcp run server.py --transport streamable-http
```

客户端连接它，再发现、调用工具：

```
import asyncio
from mcp import Client

async def demo():
    async with Client("http://localhost:8000/mcp") as connection:
        # 发现服务器提供的工具及参数说明
        print(await connection.list_tools())

        # 请求服务器执行那个 Python 函数
        reply = await connection.call_tool(
            "get_link_telemetry",
            {"link_id": "link-A"}
        )
        print(reply.structured_content)

asyncio.run(demo())
```

这时实际发生的是：

```
客户端请求调用 get_link_telemetry("link-A")
    → MCP server 找到注册的函数
    → 执行函数
    → 将吞吐量和丢包率返回客户端
```

**接入真实 telemetry 时，只需把函数体改成调用监控 API。** Agent 程序可以把发现的工具描述提供给 LLM；模型提出工具调用后，再由程序通过 MCP 客户端执行。上面这个客户端例子直接指定了工具，尚未加入 LLM 决策。

---

> “
>
> 1. 框架选型之前先明确功能
>
> Rafael 建议先为希望 agents 完成的事情开发和定义 skills。明确 skill 后，再组装 agents、连接服务，或接入不同 harness 会更容易。
>
> 他提到存在多种 harness/框架选择，包括转写可能对应 Codex、Claude 和 Academy 的例子；具体列举名称有明显误识别，不能据此认定团队已选用其中任何一种。
>
> 这一建议针对的是功能与框架的解耦：先知道 agents 要做什么，而不是首先争论底座名字。会上没有定出 skill schema、skill database 格式或通用调用协议。”
>
> 1. skill是不是就是md文件编写的东西，有规定/固定的格式吗？用简单例子带我了解。
> 2. rafael想做的事已经是在考虑agent和llm的交互问题了，我认为不对。我认为应该先弄清楚agent的rule based规则有哪些，然后先实现这部分，比如容量记录、格式接口等等。对吗？

**你提出“先实现确定性核心”的顺序是合理的，但 Rafael 的“先定义 skills”不一定与它冲突。** 关键在于他所说的 skill 是“能力规格”，还是已经面向 LLM 的操作说明。

**1. Skill 是不是 Markdown 文件？**

在 Codex 的 **Agent Skills** 机制里，一个 skill 通常是一个目录，以 `SKILL.md` 为入口，还可以附带 Python 脚本、参考资料和模板。

格式上有基本要求：开头是 YAML 元数据，至少包含 `name` 和 `description`；后面是 Markdown 指令，正文标题和步骤没有统一的固定模板。[OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)

例如，下面是一个**示意 skill**，假设相关工具已经实现：

```
---
name: inspect-transfer
description: 在用户要求检查数据传输进度时，查询状态并报告风险。
---

步骤：
1. 获取用户指定的 transfer_id。
2. 调用 get_transfer_status，取得最新状态和观测时间。
3. 调用 evaluate_transfer_progress，取得规则判定结果。
4. 报告进度、判定结果、触发的规则和依据。
5. 数据缺失时报告 unknown，不自行补造。
```

这里，`SKILL.md` 告诉模型**如何组织操作与汇报**；真正查询状态、计算风险的是工具代码。规则计算也可以放在 skill 附带的脚本里。[OpenAI 官方说明](https://developers.openai.com/plugins/build/skills)

但**会议没有确认 Rafael 所说的 skills 就是这种** `SKILL.md`。他也可能泛指：“先列清楚每个 agent 能做什么、需要什么输入、产生什么输出。”

**2. 是否应该先实现 rule-based 部分？**

我赞成先建立一个**不依赖 LLM、能明确验证行为的核心**。不过你举的几项还可以再区分：


| 内容                    | 属于什么    |
| --------------------- | ------- |
| 容量记录、预约记录、传输状态        | 状态管理    |
| 字段格式、单位、ID、API 转换     | 数据与接口契约 |
| 何时告警、何时拒绝请求、何时升级处理    | 规则与决策策略 |
| 根据明确规则调用网络 API、确认执行结果 | 确定性执行流程 |




这些都应落实成代码和明确的数据语义。例如，“容量”要先分清**配置容量、已预约容量、当前吞吐量、可分配容量**；它们不能直接混用。

而 Rafael 的建议可以与这套顺序兼容。例如先定义一项能力：

```
能力：检查传输是否偏离计划
输入：计划、最新进度、观测时间
输出：normal / at_risk / unknown，以及判定依据
实现：先使用明确规则，不调用 LLM
```

这已经是在“定义 skill”，却还没有涉及 LLM 交互。

所以，**如果他要求先写 prompts、搭 harness，却还没明确状态、接口和规则，你的质疑成立；但仅凭“先定义 skills”，还不能判断他在跳过这些工作。** 更合适的起步顺序是：先明确能力的输入、输出和规则，再实现确定性版本；之后有具体问题需要 LLM 时，再决定如何接入。

---

> “
>
> 1. Mariam 希望收到 end-to-end 图
>
> Mariam 请 Harvey 提供 HEP workflow 示例。Harvey指出实际 workflows 是多步骤、包含人的工作过程，并询问这里需要什么参数。  
> Mariam 说明可以先画图，表示某个 actor/步骤之后发生什么、数据流向哪里，给出一个代表性的端到端过程，再请 Rafael 把它表达为可用 workflow。Harvey 表示自己正在做，但同时有许多其他工作。
>
> ”
>
> HEP workflow是啥？不是已经有workflow的example了吗？

**HEP 是 High-Energy Physics，即高能物理。HEP workflow 就是高能物理实验的数据处理或分析流程。** 它描述科学任务怎样衔接，例如一个简化的分析流程：

```
读取粒子碰撞事件数据
  → 筛选事件、计算物理量
  → 生成直方图
  → 建立统计模型并做推断
  → 得到分析结果
```

Harvey 提到的 **Analysis Grand Challenge（AGC）** 就提供了这类端到端分析参考，包含事件筛选、直方图和系统误差处理等内容。[AGC 官方介绍](https://iris-hep.org/analysis-grand-challenge.html)

**确实已经有 workflow examples，但它们不是 HEP 示例：**


| 已有示例                        | 用途                      |
| --------------------------- | ----------------------- |
| **Hello World / fork-join** | 简单的任务依赖示例，便于先把系统跑通      |
| **1000 Genome**             | 基因组分析 workflow，可用于开发和测试 |
| **待补充的 HEP workflow**       | 对应高能物理场景，用于项目的代表性科学演示   |


按会议口径，Mariam 先选了前两个让大家开始开发，并没有把它们确定为最终 demo。[会议记录](/Users/lxzhong/Documents/GitHub/genesis_scinet/resources/meetings/20261013_scinet_agent_[implementation.md](http://implementation.md))

所以她请 Harvey 提供的，是**符合 HEP 场景的具体任务流程和数据需求**。例如：数据在哪个站点、哪个步骤要读它、计算在哪里执行、需要传多少数据、有哪些先后依赖。Rafael 再帮助把这些领域描述转换成系统能读取的 workflow 表达。

**已有示例足够让 agent 开发起步；补 HEP 示例是为了让后续演示对应项目承诺的科学场景。** AGC 当时只是参考，尚未确定就是最终采用的 HEP workflow。

---

>

