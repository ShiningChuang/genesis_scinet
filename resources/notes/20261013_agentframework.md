> 介绍一下这个仓库是啥：  
> [https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama)

这个仓库是一个 **用本地 LLM 实现“多个角色分工处理文本”的小型 Python 示例应用**。它通过 Ollama 调用 `llama3.2:3b`，用 Streamlit 提供网页界面，示例任务集中在医学文本摘要、文章写作和数据脱敏。[仓库 README](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama)

它的运行方式比较直观：


| 用户选择的任务 | 程序执行的流程                        |
| ------- | ------------------------------ |
| 医学文本摘要  | 摘要 agent → 检查摘要的 agent         |
| 文章写作    | 写作 agent → 润色 agent → 评价 agent |
| 医疗数据脱敏  | 脱敏 agent → 检查脱敏结果的 agent       |


这些步骤由 Python 代码按固定顺序调用，结果显示在页面上。[应用代码](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/app.py)

**这里的不同 agent，主要是同一个模型配上不同的 prompt。** 例如摘要角色被要求概括文本，validator 角色被要求比较原文与摘要、给出评价。它们没有分别训练不同模型。代码结构也很简单：

- `AgentBase`：统一封装 Ollama 调用、日志和失败重试。
- 各 agent 的 `execute()`：组织自己角色的 prompt，再调用模型。
- `AgentManager`：用一个字典保存 agent，按名字取出；调用顺序由 `app.py` 决定。[基础类](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/agents/agent_base.py)、[管理器](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/agents/__init__.py)

因此，它展示的是**角色封装和固定的多步 LLM 流程**。我检查的代码里没有动态选择工具的循环、MCP 接入、持久记忆、跨 agent 协商或网络控制接口。Validator 也只是让模型生成评价文字，程序没有根据评价自动决定重做或停止。[应用代码](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/app.py)、[摘要检查代码](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/agents/summarize_validator_agent.py)

还有一个具体实现问题：`call_llama()` 接收 `temperature` 和 `max_tokens` 参数，但调用 `ollama.chat()` 时没有传进去，所以各角色设置的这些参数实际上没有生效。[基础类代码](https://github.com/AIAnytime/AI-Agents-from-Scratch-using-Ollama/blob/main/agents/agent_base.py)

**放到 SciNet 的语境里，我的判断是：它适合帮助 Mariam 理解如何组织 agent 类、连接本地模型、串联几个角色。** 但你们需要的“读取 telemetry → 根据规则或 LLM 判断 → 调用网络 API → 观察执行效果”这条闭环，仍需要自行实现；仅把这里的角色改名为 network、telemetry、scheduling，并不会得到这些能力。我本次只阅读了代码，没有安装或运行。

---

> 继续介绍一下这个仓库
>
> **[https://github.com/bhatti/agentic-ai-tutorial](https://github.com/bhatti/agentic-ai-tutorial)**

这个仓库是一个 **用 Ollama、LangChain 和 LangGraph 教你搭建 agent 的教程项目**。它以股票分析为示例，把“模型选择工具、检索文档、执行工具、组织流程”拆成几个模块，提供 Streamlit 界面和 CLI。[README](https://github.com/bhatti/agentic-ai-tutorial)

相比前一个仓库，它展示了更多 agent 的实际运行机制：


| 模块              | 实现了什么                                           |
| --------------- | ----------------------------------------------- |
| **ReAct**       | 模型输出要执行的工具和参数，Python 执行工具，把结果交回模型，再决定下一步        |
| **RAG**         | 文档切块 → 本地 embedding → FAISS 检索 → 将相关内容放进提示词生成回答 |
| **Tool System** | 定义工具名称、参数、描述，支持注册、查找、执行和执行历史                    |
| **Workflow**    | 用 LangGraph 定义带共享状态的多步骤流程                       |


对应代码是 [react_agent.py](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/react_agent.py)、[rag_engine.py](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/rag_engine.py)、[tool_system.py](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/tool_system.py) 和 [workflow.py](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/workflow.py)。

**最值得理解的是 ReAct 部分。** 前一个仓库主要由程序固定调用“生成 → 检查”；这里允许模型在一个有限的工具集合中决定下一步：

```
提出问题
  → 模型选择工具与参数
  → Python 执行工具
  → 把执行结果交给模型
  → 继续调用工具，或生成最终回答
```

它用文本格式和正则表达式解析模型输出，默认最多循环 10 步。可用工具包括行情查询、计算、搜索和情绪分析。不过，工具选择仍受 Python 注册的函数集合约束。[ReAct 实现](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/react_agent.py)

它还用 LangGraph 定义了一个股票分析流程：先取行情，再分出技术分析、情绪分析和 RAG 三条支路，随后接 ReAct 和报告生成。**流程结构由代码定义，模型在部分节点内参与判断**。[流程实现](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/workflow.py)

读这个仓库时，有几处需要区分“教程展示”与“完整能力”：

- **“MCP-style”是工具接口风格。** 当前实现是本地 Python 工具注册与调用，没有实际的 MCP client/server 协议接入。[工具代码](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/tool_system.py)
- **数据混合了真实来源和模拟内容。** 行情通过 `yfinance` 获取；网页搜索、SQL 查询是 mock；RAG 默认加载的是代码里编写的示例文档。[工具代码](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/tool_system.py)、[RAG 代码](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/rag_engine.py)
- **部分分析结果仍是占位实现。** Workflow 中情绪分数和几个因素是写死的，confidence score 也是简单规则计算，不能把它们当成经过验证的评价指标。[流程代码](https://github.com/bhatti/agentic-ai-tutorial/blob/main/src/workflow.py)

**对 SciNet，我认为它更适合作为“agent 如何调用工具并利用反馈”的学习参考。** 可以借鉴工具封装方式，把行情查询换成 telemetry 查询，把其他工具换成网络 API；但规则与 LLM 的职责划分、调度协商、执行后验证、故障恢复仍需你们设计实现。

这里的 `workflow.py` 管理的是 **agent 自身的分析步骤**；它还没有实现你们所说的、包含计算任务和数据传输依赖的科学 workflow 调度。我本次阅读了代码，没有安装或运行。

---

> 用代码作为例子简单说明“借鉴工具封装方式，把行情查询换成 telemetry 查询，把其他工具换成网络 API”

意思是：**保留“工具描述 → agent 选择 → Python 调用 → 返回结果”这套结构，把工具内部的功能替换成网络系统操作。**

下面沿用仓库的 `BaseTool` 和 `ToolRegistry`，写一个通用 API 包装器。`read_telemetry`、`request_path` 代表你们为真实系统写的适配函数；这里仅示意接口。

```python
from src.tool_system import (
    BaseTool, ToolSchema, ToolParameter, ToolCategory, ToolRegistry
)

class APITool(BaseTool):
    def __init__(self, name, description, parameters, call_api):
        self.schema = ToolSchema(
            name=name,
            description=description,
            category=ToolCategory.API_INTEGRATION,
            parameters=parameters,
            returns="API 返回的数据"
        )
        self.call_api = call_api

    def get_schema(self):
        return self.schema

    def execute(self, **kwargs):
        self.validate_input(**kwargs)
        return self.call_api(**kwargs)


tools = ToolRegistry()

# 原来的 stock_data 工具 → 查询链路状态的工具
tools.register(APITool(
    name="get_link_telemetry",
    description="查询链路的吞吐量、丢包率和状态",
    parameters=[
        ToolParameter(name="link_id", type="string",
                      description="链路标识")
    ],
    call_api=read_telemetry
))

# 新增工具：通过已有网络系统请求一条路径
tools.register(APITool(
    name="request_network_path",
    description="请求指定端点之间、满足带宽要求的网络路径",
    parameters=[
        ToolParameter(name="src", type="string", description="源端点"),
        ToolParameter(name="dst", type="string", description="目的端点"),
        ToolParameter(name="bandwidth_mbps", type="number",
                      description="请求带宽，单位 Mbps")
    ],
    call_api=request_path
))
```

真正与外部系统交互的是这两个适配函数：

```python
def read_telemetry(link_id):
    # 调用现有监控系统的 API，并整理字段
    ...
    # 例如返回：
    # {"link_id": ..., "throughput_mbps": ..., "loss_rate": ..., "up": ...}

def request_path(src, dst, bandwidth_mbps):
    # 将参数翻译为 SENSE 等系统实际支持的请求，并调用 API
    ...
    # 例如返回：
    # {"request_id": ..., "status": ..., "path": ...}
```

于是，agent 原来选择“查询股票行情”，现在可以选择“查询链路状态”。模型负责提出**工具名和参数**，Python 负责执行真实 API，把结果作为 observation 交回模型。

**这里的** `request_path` **是我们定义的适配层接口，具体如何映射到 SENSE，需要按其真实 API 实现。** 另外，注册进 `ToolRegistry` 后，还需要把工具描述和调用入口接到仓库的 ReAct agent，才能由模型选择调用。

---

> LangChain是啥


| 名称            | 主要作用                    |
| ------------- | ----------------------- |
| **vLLM**      | 运行 LLM，计算并生成输出          |
| **LangChain** | 帮你编写调用模型、使用工具的 agent 应用 |
| **LangGraph** | 用状态和流程图组织更复杂的执行步骤       |


**vLLM 是推理引擎。** 例如，把 Qwen 模型权重加载到 GPU，接收输入、生成回答，并处理多个推理请求、管理显存、提供模型 API。这些属于 vLLM 的工作。[vLLM 官方文档](https://docs.vllm.ai/en/latest/)

**LangChain 是应用开发框架。** 它提供现成组件，让你连接模型、组织提示词和消息、注册工具，以及执行“调用模型 → 调用工具 → 把结果交回模型”的循环。[LangChain 官方文档](https://docs.langchain.com/oss/python/langchain/overview)

在你们项目中，一种组合可以是：

```
你们的 agent 程序（用 LangChain 编写）
  ├─ 调用 vLLM 提供的 API → 运行 Qwen，取得模型判断
  └─ 调用工具 / MCP      → 查询 telemetry、请求 SENSE 网络服务
```

**LangGraph** 则适合把流程明确画出来，例如“查询状态 → 规则判断 → 必要时咨询模型 → 执行动作 → 验证结果”，并管理各步骤之间传递的状态。[官方框架定位](https://docs.langchain.com/oss/python/langchain/overview)

按你前面提出的起步顺序，**容量记录、接口转换和 rule-based 判断都可以先用普通 Python 实现**；这些基础功能并不要求先采用 LangChain，也不要求先部署 vLLM。

---

> LangChain 是不是SCINET最应该学习和利用的AGENT框架？我的理解是它本质就是ReAct架构的框架化？这正是SCINET需要的东西？能否用一个简单的代码例子解释LangChain是怎么用的？

**LangChain 值得重点学习，但目前还不能认定它就是 SciNet 最合适的框架。** 它能替你们处理模型接入和工具调用循环；容量管理、调度策略、接口语义与恢复规则，仍需要你们自己实现。

你对 ReAct 的理解**抓住了它的一个核心用途**：LangChain 的 `create_agent()` 封装了“调用模型 → 执行工具 → 将结果交回模型 → 继续或结束”的循环。但 LangChain 的范围更广，也提供模型、工具、状态等抽象；并不要求模型输出教程中那种字面的 `Thought/Action/Observation` 文本。[官方 agent 文档](https://docs.langchain.com/oss/python/langchain/agents)

对于你们“**确定性规则为主，必要时调用 LLM**”的设计，LangGraph 也值得了解：它允许明确规定哪些步骤必须执行、哪些分支才进入模型判断。[LangGraph 官方定位](https://docs.langchain.com/oss/python/langgraph/overview)

下面用一个**容量检查**例子说明 LangChain 怎么用。假设 Ollama 已运行，并加载了支持工具调用的模型；代码使用当前 `create_agent` 接口，数据全部是演示数据，未执行。

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama

@tool
def check_capacity(link_id: str, requested_mbps: float) -> dict:
    """检查指定链路能否容纳新增带宽请求，单位为 Mbps。"""

    # 演示：同一预约时段内的容量记录
    records = {
        "link-A": {"capacity_mbps": 1000, "reserved_mbps": 800}
    }
    link = records[link_id]

    # 确定性规则：由 Python 计算，不让 LLM 估计
    available = link["capacity_mbps"] - link["reserved_mbps"]
    return {
        "available_mbps": available,
        "can_allocate": 0 < requested_mbps <= available
    }

agent = create_agent(
    model=ChatOllama(model="gpt-oss:20b", temperature=0),
    tools=[check_capacity],
    system_prompt=(
        "回答容量问题时先调用工具。"
        "依据工具结果回答，不自行猜测容量。"
    ),
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "link-A 能再分配 300 Mbps 吗？"
    }]
})

print(result["messages"][-1].content)
```

其中模型接入方式来自 [ChatOllama 官方文档](https://docs.langchain.com/oss/python/integrations/chat/ollama)。

预期过程是：

```
用户问：能再分配 300 Mbps 吗？
    ↓
模型提出调用：
check_capacity(link_id="link-A", requested_mbps=300)
    ↓
LangChain 执行 Python 函数：
返回 available_mbps=200，can_allocate=False
    ↓
LangChain 把结果交回模型
    ↓
模型回答：该时段剩余 200 Mbps，无法满足新增 300 Mbps 的请求。
```

**你写的是工具和容量规则；LangChain 替你写的是模型与工具之间的调用循环。** 这里的 `@tool` 注册的是程序内部工具，没有启动 MCP server。

这个例子也说明：**采用 LangChain，并不意味着把 rule-based 部分交给 LLM。** 容量计算仍由代码决定。若要求“容量检查必须发生”，就应由固定流程或执行接口强制检查；示例中的 prompt 只是对模型的指令。

---

> langgraph是什么？和LangChain的关系是什么？用简单代码例子说明。

**LangGraph 是把程序流程写成“可执行状态图”的框架。** 你明确规定有哪些步骤、共享哪些数据、什么条件下进入哪个分支；步骤内部可以是普通 Python，也可以调用 LLM。[官方介绍](https://docs.langchain.com/oss/python/langgraph/overview)

它的三个核心概念是：


| 概念        | 含义          | SciNet 示例          |
| --------- | ----------- | ------------------ |
| **State** | 各步骤之间传递的数据  | 请求带宽、可用容量、处理结果     |
| **Node**  | 执行一步工作的函数   | 查询容量、检查规则、调用网络 API |
| **Edge**  | 决定下一步执行哪个节点 | 容量足够就接受，不足就拒绝      |


[Graph API 文档](https://docs.langchain.com/oss/python/langgraph/graph-api)

**它和 LangChain 是同一生态中的不同层次：**

- **LangChain** 提供模型、工具和现成的 agent 循环。
- **LangGraph** 提供更底层的流程编排，让你自己定义顺序、分支、循环和状态。
- 当前 LangChain 的 agent 抽象建立在 LangGraph 上；但 **LangGraph 可以独立使用，也可以完全不调用 LLM**。[官方关系说明](https://docs.langchain.com/oss/python/langgraph/overview)

例如，你们先实现一个完全 rule-based 的流程：

```
开始 → 查询容量
            ├─ 请求带宽 ≤ 可用容量 → 接受 → 结束
            └─ 请求带宽 > 可用容量 → 拒绝 → 结束
```

对应的简单代码：

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# 各步骤共享的数据
class State(TypedDict, total=False):
    requested_mbps: int
    available_mbps: int
    decision: str

# 节点：查询容量
def read_capacity(state):
    # 演示数据；真实实现改为查询指定链路、时段的容量记录
    return {"available_mbps": 200}

# 分支规则：完全由 Python 判断
def choose_next(state):
    if 0 < state["requested_mbps"] <= state["available_mbps"]:
        return "accept"
    return "reject"

# 节点：记录决定，此处不执行真实资源预约
def accept(state):
    return {"decision": "accepted"}

def reject(state):
    return {"decision": "rejected"}

# 把节点连接成流程图
builder = StateGraph(State)
builder.add_node("read_capacity", read_capacity)
builder.add_node("accept", accept)
builder.add_node("reject", reject)

builder.add_edge(START, "read_capacity")
builder.add_conditional_edges(
    "read_capacity",
    choose_next,
    {"accept": "accept", "reject": "reject"}
)
builder.add_edge("accept", END)
builder.add_edge("reject", END)

app = builder.compile()
result = app.invoke({"requested_mbps": 300})
print(result["decision"])  # 按上述规则得到 rejected
```

这里，节点返回的字典是对 State 的**局部更新**：`read_capacity` 补上可用容量，后续节点读取它，再写入决定。LangGraph 负责传递状态和执行相应分支。[状态更新机制](https://docs.langchain.com/oss/python/langgraph/graph-api)

以后若需要 LLM，可以新增一个“提出替代方案”节点：容量不足时先由模型建议其他路径，再由确定性规则检查方案。**哪些步骤调用 LLM、哪些步骤必须执行规则，由你定义的图来控制。**

### **我的理解**

langchain中的create_agent就可以作为langgraph中的一个节点函数里的具体操作。

更准确地说：`create_agent()` 创建 agent，节点函数里调用它的 `invoke()` 来执行。

通常先在节点外创建，避免每次执行节点都重新创建：

```
from langchain.agents import create_agent

# 假设 llm 和 tools 已经定义
advisor = create_agent(
    model=llm,
    tools=tools,
    system_prompt="根据查询结果分析传输问题。"
)

# LangGraph 的一个节点函数
def analyze_transfer(state):
    result = advisor.invoke({
        "messages": [{
            "role": "user",
            "content": f"请分析传输 {state['transfer_id']} 的状态"
        }]
    })
    return {"analysis": result["messages"][-1].content}

builder.add_node("analyze_transfer", analyze_transfer)
```

这形成了两层流程：

```
外层 LangGraph：
查询状态 → 规则判断 → 必要时进入 analyze_transfer → 后续处理

analyze_transfer 节点内部：
LangChain agent 调用模型 → 执行工具 → 再调用模型 → 返回分析
```

**外层图控制“什么时候让这个 agent 工作”；节点里的 agent 控制“在提供的工具范围内怎样完成分析”。** 当前 LangChain 的 agent 本身也建立在 LangGraph 上，所以这里可以理解为外层流程调用一个内部 agent 流程。[官方框架关系](https://docs.langchain.com/oss/python/langgraph/overview)

---

> 所以在langgraph中，state是一张graph的全局数据？

**基本对，但更准确地说：**`state` **是一张图在某次执行中的共享数据，各节点通过它传递和更新信息。** 它不是整个程序所有任务共用的全局变量。[官方定义](https://docs.langchain.com/oss/python/langgraph/graph-api#state)

比如处理一次带宽请求：

```
state = {
    "link_id": "link-A",
    "requested_mbps": 300,
    "available_mbps": None,
    "approved": None,
}
```

节点依次处理：

```
查询节点：读取 link_id
          返回 {"available_mbps": 200}
                 ↓
判断节点：读取 requested_mbps 和 available_mbps
          返回 {"approved": False}
                 ↓
回复节点：读取 approved，生成结果
```

**节点通常只返回自己更新的字段，由 LangGraph 合并进 state。** 默认更新会覆盖对应字段；也可以配置 reducer，例如把新消息追加到消息列表。

“全局”的范围要注意：

- **同一次图执行内**：节点共享这份状态。
- **不同任务之间**：默认不会因为使用同一个 graph 对象，就共用同一份状态。
- **需要跨次执行保留状态**：可以配置 checkpointer，通过 `thread_id` 延续同一个会话。
- **不同站点的 agent 之间**：各自拥有状态，通过接口交换所需数据，不会自动共享 state。

对 SciNet，可以把它理解成**“当前这次网络请求的处理记录”**。其中的容量字段可以是查询得到的快照；全系统的容量账本仍应由数据库或网络管理服务维护。

---

> 1. “**不同任务之间**：默认不会因为使用同一个 graph 对象，就共用同一份状态。”，不同任务之间有不同state？state是暂时性的吗，一次任务做完就销毁？
> 2. 我的理解是一张图会根据不同的功能存在多个state，每个任务就是根据某个功能对对应的state进行node之间传递和修改？比如link-A的网络容量是一个state，link-B的网络容量是另一个state；一个network agent需要创建多少种state？多少个state？

`state` **更适合理解成“处理某个任务时的工作记录”。link-A、link-B 的容量则是这份记录里可以读取的数据。** 我上一条说“一次任务一份 state”，省略了会话延续的情况，这里展开说明。

**1. state 是暂时的吗？任务结束就销毁？**

取决于是否配置保存：


| 情况                     | 执行结束后                                        |
| ---------------------- | -------------------------------------------- |
| **没有 checkpointer**    | LangGraph 不会自动保存可供下次恢复的状态；返回的结果仍可以由你的代码持有或保存 |
| **使用内存 checkpointer**  | 可以通过同一个 `thread_id` 延续状态，但进程退出后会丢失           |
| **使用数据库 checkpointer** | 状态快照可以跨进程重启保留，直到按保留策略删除                      |


所以，“执行结束”不等于“立即销毁所有数据”。

另外，**一次业务任务可以包含多次图调用**。例如：

```
thread_id = "request-001"

第一次调用：申请带宽 → 得到备选方案 → 结束本次调用
第二次调用：接受备选方案 → 完成预留
```

配置 checkpointer 后，这两次调用可以使用同一个 thread，接着此前保存的状态继续处理。`thread` 是 LangGraph 的会话标识，不是操作系统线程。[官方持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence)

**2. 一张图需要多少种、多少个 state？**

这里分清 **state 的结构**和**实际的数据实例**就容易了。

例如，你为“带宽申请流程”定义一种结构：

```
class RequestState(TypedDict):
    request_id: str
    link_id: str
    requested_mbps: int
    available_mbps: int | None
    approved: bool | None
```

它规定“处理一份申请需要记录哪些字段”。同一张图可以反复使用这套结构，处理不同请求。[官方 state schema 说明](https://docs.langchain.com/oss/python/langgraph/graph-api#state)

实际运行时，可以出现：


| 请求  | 使用的结构          | 该请求的 state 内容      |
| --- | -------------- | ------------------ |
| R1  | `RequestState` | link-A，申请 300 Mbps |
| R2  | `RequestState` | link-B，申请 500 Mbps |
| R3  | `RequestState` | link-A，申请 100 Mbps |


**这里是一种结构、三份独立的任务状态。R1 和 R3 操作同一条链路，仍可以有各自的 state。** 你不需要给每条链路创建一个新的 state 类型，也不需要给每个请求创建一张新图。

而链路容量可以长期保存在数据库或网络管理服务中：

```
长期资源数据
    link-A：总容量、已预留容量……
    link-B：总容量、已预留容量……

同一张“带宽申请图”
    ├─ R1 的 state：查询 link-A，记录查询结果和处理进度
    ├─ R2 的 state：查询 link-B，记录查询结果和处理进度
    └─ R3 的 state：查询 link-A，记录查询结果和处理进度
```

R1、R3 查询的是同一份资源账本，但它们自己的 state 中可能保存了不同时间的容量快照。因此，真正预留时，仍要由资源服务检查最新容量并处理并发申请。

**对第一版 network agent，我建议先定义一种“网络请求 state”。有多少独立请求或会话，就按需维护多少份状态；链路数量由资源数据库管理。** 将来监控、故障处理等流程需要不同字段时，再为那些图定义适合的 state 结构。

---

> langchain和langgraph这个家族项目，是由谁发起的？能否理解为其地位之于agent framework，就像vllm/sglang之于推理引擎？

**发起者：Harrison Chase**

LangChain 最初是 Harrison Chase 的个人项目。他 2022 年 10 月还在 Robust Intelligence 任职时，把它作为开源 Python 包发布，几周后 ChatGPT 上线，项目随之爆红。2023 年初，他和前同事 Ankush Gola 成立了 LangChain Inc.。融资方面，2023 年 Benchmark 领投种子轮，2024 年 Sequoia 领投 A 轮。2025 年 10 月，IVP 领投 1.25 亿美元，估值 12.5 亿美元，同时发布了 LangChain 1.0 和 LangGraph 1.0。

这个家族目前的分工：LangChain 负责模型和工具的集成，以及一个可定制的 agent loop；LangGraph 是自定义工作流的 runtime；Deep Agents 打包了上下文管理、文件、记忆和 subagent，面向长任务。商业化主要靠 LangSmith（可观测性和评测），它也能用于不基于 LangChain 构建的 agent。

**类比：只对一半**

"最流行的开源默认选项"这一点上，类比成立。LangChain 宣称自己是下载量第一的 agent 框架。但在几个关键维度上不像 vLLM/SGLang：

1. **出身与治理不同。** vLLM 来自 UC Berkeley Sky Computing Lab，2025 年成为 PyTorch Foundation 托管项目；SGLang 来自 LMSYS。两者都是学术出身、社区治理。LangChain 从一开始就是 VC 驱动的公司，开源框架主要作为商业产品的获客渠道。
2. **技术护城河不同。** 推理引擎优化的是硬指标（吞吐、延迟、TTFT），靠的是 KV cache 管理、调度、kernel 这类很难复制的系统工作，比如 PagedAttention 和 RadixAttention。agent 框架本质上是对 API 调用的一层薄抽象，核心 loop 自己写也就几百行。Chase 自己也承认早期抽象有问题：prompt 被隐藏、频繁 breaking change、依赖臃肿，后来围绕更简单的 agent loop 重写了框架。
3. **不可替代性不同。** 自己部署开源模型时，基本绕不开 vLLM、SGLang 或 TRT-LLM，格局接近寡头。agent 框架则非常碎片化：OpenAI Agents SDK、Claude Agent SDK、Google ADK、Microsoft Agent Framework、CrewAI、LlamaIndex、Pydantic AI 等都在竞争。很多团队直接手写 loop，最强的那批 agent（Claude Code、Codex）也是厂商自研的 harness，不用 LangChain。这部分是我的判断，不是检索结论。不过确实有大客户采用，比如 Replit 的 coding agent 就跑在 LangGraph 上，用 LangSmith 监控。

**更贴切的类比**

- **LangChain** 更像应用层的 HF `transformers`：价值在集成的广度，而不在性能。
- **LangGraph** 是家族里系统含量最高的部分。它基于 BSP/Pregel 模型，支持带环的工作流和确定性并发，加上 checkpoint 和 human-in-the-loop，更像面向 agent 的 durable workflow engine（类似 Temporal）。
- **LangSmith** 更像 LLM 版的 W&B 或 Datadog，也是公司真正的收入来源。

跟你的方向的交集在于：agent 框架决定了 workload 的形态（多轮、共享前缀、工具调用间隙、并行 subagent），推理引擎负责服务这种 workload。SGLang 在共享前缀的 agent 类负载上明显占优，原因就在这里。

Sources:

- [Fortune – LangChain unicorn](https://fortune.com/2025/10/20/exclusive-early-ai-darling-langchain-is-now-a-unicorn-with-a-fresh-125-million-in-funding/)
- [AI Engineer – Harrison Chase](https://www.ai.engineer/speakers/harrison-chase)
- [AI Engineer – LangChain org](https://www.ai.engineer/orgs/langchain)
- [Sacra – LangChain](https://sacra.com/research/langchain)
- [Rywalker – LangChain research](https://rywalker.com/research/langchain)
- [Revenue Memo – LangChain funding](https://www.revenuememo.com/p/langchain-funding)
- [Wikipedia – vLLM](https://en.wikipedia.org/wiki/VLLM)
- [vLLM GitHub README](https://trendshift.io/admin/repository/ask-ai/1487)
- [Vantaige – vLLM](https://vantaige.io/ai-tool/vllm)

---

> 1. Agent framework届是否有vllm/sglang这种级别出生的、学术级别的、开源的项目？
> 2. LangChain/graph/smith和deep agents这个家族，是否有一个主github仓库或者官网？
> 3. 在这个agent framework下做Genesis mission的SCINET项目，是否合适？比如这个背后是商业公司，不太适合？或者逼格不够？

**1. 有没有 vLLM/SGLang 那种学术出身、开源的 agent framework？**

有学术出身的项目，但没有一个达到 vLLM 在推理引擎里那种"事实标准"的地位。原因和上一条说的一样：agent framework 缺少一个可以硬性 benchmark 的系统问题，学术界很难靠"做得更快"一统江湖。比较接近的几个（这部分是我的已有知识）：

- **DSPy**（Stanford NLP）：把 prompt/pipeline 当成可优化的程序，学术影响力最大。
- **MemGPT → Letta**（Berkeley Sky Computing Lab，和 vLLM 同一个实验室）：主打 agent 记忆管理，后来成立了公司。
- **AutoGen**（Microsoft Research 联合 Penn State、UW，有论文），社区后来分叉出了 AG2。
- **SWE-agent**（Princeton）、**OpenHands**（UIUC/CMU 起家）：偏 coding agent。
- **Academy**（Argonne / UChicago Globus Labs，Ian Foster、Kyle Chard 团队）：和你最相关，下面第 3 条细说。

另外，这些学术项目也大多走上了公司化的路。

**2. 主仓库和官网**

没有单一的 monorepo，但有统一的 GitHub org 和统一的文档站：

- GitHub：`github.com/langchain-ai`，核心是 [langchain](https://github.com/langchain-ai/langchain)、[langgraph](https://github.com/langchain-ai/langgraph)、[deepagents](https://github.com/langchain-ai/deepagents) 三个仓库，各自有 JS 版（`langchainjs`、`langgraphjs`、`deepagentsjs`）。
- 文档：`docs.langchain.com`，三个框架和 LangSmith 的文档都在这里。
- 官网：`langchain.com`。LangSmith 本身是闭源 SaaS（`smith.langchain.com`），开源的只有 SDK。

三者是逐层叠加的关系：Deep Agents 建在 LangChain 之上，LangChain 又建在 LangGraph 之上。

**3. 用它做 SCINet 合不合适？**

我觉得关键不在"商业公司"或"逼格"，而在**架构上不对口**。

- **LangGraph 把 network 藏起来了。** 它的模型是在一个 runtime 里跑一张状态图，agent 之间传递的是进程内的 state。你们在 SCINet 里要做的，恰恰是 agent↔agent、agent↔digital twin 之间的**跨站点流量**：MPQUIC、带 deadline/剩余字节的调度 API、per-stream 公平性。用 LangGraph，就没有可以调度的网络流量了。
- **Academy 正好暴露了你们要插入的那一层。** 它基于 actor 模型，launcher 支持 thread、process、Parsl、Globus Compute；Songran 讲那篇论文时提到的几种 exchange（in-memory、Redis、HTTPS cloud exchange、pass-by-reference）就是 agent 间的通信层，也就是你们用统一 transport 替换 TCP/HTTP/RDMA 那堆协议的天然切入点。论文实验用的是 ZeroMQ、没用 RDMA，这本身就是一个可以做的 gap。
- **生态对齐。** Academy 是 DOE 实验室自己做的，在 Aurora 和 Chameleon 上跑过 materials discovery（MOFA）。Genesis 的合作方对它更熟，演示和叙事都更顺。
- **LangChain 可以用在 agent 内部。** 比如"自动设计新实验"的那个 agent，内部推理可以用 LangChain/LangGraph，外面再包成 Academy agent。注意关掉 LangSmith tracing，否则 trace 会发到他们的 SaaS 上，在 DOE 场景下有数据治理问题。MIT license 本身没问题。
- **关于逼格：** 在 SC 或网络类的 venue，审稿人不会因为你用了哪个 framework 加分或减分。贡献点在 transport/scheduling 和 digital twin 上，framework 只是产生流量的应用层。



建议在下次 PI meeting 上问一句：ORNL（Kiran）那边是否已经有偏好的 agent 框架。她写过科学实验 agent 架构的书，如果他们已有选择，你们直接对齐就好。

Sources:

- [Academy – Globus Labs](https://labs.globus.org/projects/academy.html)
- [Empowering Scientific Workflows with Federated Agents (arXiv)](https://arxiv.org/html/2505.05428v3)
- [Moonlight review of the Academy paper](https://www.themoonlight.io/en/review/empowering-scientific-workflows-with-federated-agents)
- [LangChain docs – contributing](https://docs.langchain.com/oss/python/contributing/code.md)
- [LangChain docs – Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview.md)
- [Neurals – LangChain overview](https://neurals.ca/tech/langchain/)

---

> 我的感受是，langchain和langgraph似乎是目前比较官方的agent frame库，地位就好比vllm之于推理引擎。所以SCINET可以几乎就把langchain和langgraph作为agent framework，在上搭建自己的功能？如果你不同意，是否还有比lang家族更好的agent framework？

**我基本同意：对 SciNet 当前阶段，我会优先选择 LangGraph 作为流程底座，按需使用 LangChain，在上面实现自己的网络功能。** 这是合理的工程起点，无需先遍历所有 agent 框架。

但“官方”更适合理解成“有维护团队、文档和生态”，它们并不是整个 agent 领域统一规定的标准。你与 vLLM 的类比，在“复用通用底座、专注自己的功能”这一点上很准确。

**对 SciNet 来说，我更看重 LangGraph。**

LangGraph 支持明确的状态、节点、分支，以及把普通代码步骤和 LLM 步骤放进同一个流程；它可以独立使用。LangChain 则提供模型、工具调用和 `create_agent` 等较高层接口，其 agent 本身也建立在 LangGraph 上。[官方说明](https://docs.langchain.com/oss/python/langgraph/overview)

因此，我建议这样分工：


| 部分         | 用什么实现                            | SciNet 中的例子                   |
| ---------- | -------------------------------- | ----------------------------- |
| 流程控制       | LangGraph                        | 查询资源 → 判断 → 协商 → 执行 → 检查结果    |
| 需要 LLM 的节点 | LangChain `create_agent`，或直接调用模型 | 理解需求、提出备选方案、解释异常              |
| 项目核心功能     | 自己的普通 Python 模块与 API 服务          | 容量记录、预留规则、telemetry 查询、网络操作接口 |


**这与你之前主张的“先把 rule-based 部分弄清楚并实现”完全兼容。** 第一版 LangGraph 可以全部由普通 Python 函数组成，随后再给某些节点加入 LLM。

例如，我建议的 network agent 流程可以是：

```
接收结构化请求
    ↓
查询 telemetry 与容量记录
    ↓
规则判断
    ├─ 满足条件 → 预留并执行 → 检查结果
    └─ 不满足条件 → LLM 提出备选方案
                         ↓
                    规则再次验证
```

这里框架负责“步骤怎么连接”，你们负责“什么条件允许预留、如何计算容量、怎样操作网络”。**LangGraph 的运行状态也不能自动替代共享容量数据库**：多个 agent 同时预留资源时，仍需要你们实现一致的记录和并发控制。跨机构 agent 之间的消息格式、API 和部署方式，同样需要项目自己定义。

至于有没有“更好的框架”，有值得比较的替代品，但我目前看不到足以让 SciNet 放弃 LangGraph 的明确理由：


| 替代框架                          | 什么时候值得优先考虑                                                                                                                       |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Pydantic AI**               | 主要需求是工具调用、明确的输入输出类型和结构化结果校验；它提供类型化依赖、工具参数与输出验证。[官方文档](https://pydantic.dev/docs/ai/overview/)                                    |
| **Microsoft Agent Framework** | 团队需要 Python/.NET 配合，或已有微软生态；它也提供 agent、工具/MCP 接入和显式 workflow。[官方文档](https://learn.microsoft.com/en-us/agent-framework/overview/) |


这些能力也不是 Lang 家族完全没有；选型要看哪种编程方式更适合团队。

**我的具体建议是：先把 LangGraph 定为本组 network agent 原型的默认框架，LangChain 按需加入。** 容量规则、数据结构和网络 API 封装放在独立模块里。这样可以立即推进功能，也能在以后更换框架时保留最有价值的项目代码。

---

> - **DSPy，MemGPT，AutoGen，SWE-agent，OpenHands，Academy都不如langchain家族吗**
> - langchain家族是否暴露了agent之间跨站点通信的接口？还是只能是本地进程内通信？

**不能说它们都不如 Lang 家族。尤其是 Academy：如果 SciNet 的重点包括跨站点、跨机构的常驻 agent，它比 LangGraph 更直接地针对这类需求。** 我上一条偏重了 agent 内部的流程编排，对整个 SciNet 底座的推荐说得过宽了。

**1. 这些项目解决的问题不同，不能统一排名。**

下面的 Academy 指 [academy-agents/academy](https://academy-agents.org/)；会议转写里的名称是否就是它，仍需核对。


| 项目                        | 主要解决什么                                 | 我对 SciNet 的判断                                                                                          |
| ------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **LangChain / LangGraph** | 模型与工具接入；明确的状态和执行流程                     | 适合组织一个 agent 内部的规则、工具和 LLM 步骤                                                                          |
| **DSPy**                  | 用结构化程序描述 LLM 任务，并根据评价指标优化提示等           | 当你们开始研究“怎样让 LLM 更准确地判断或规划”时，很有价值；它也能构建 agent 循环。[官方说明](https://dspy.ai/)                               |
| **MemGPT / Letta**        | 有长期记忆、持续上下文的 LLM agent                 | 适合需要积累经验的 agent；容量账本和资源预留仍需要明确的数据系统。[官方仓库](https://github.com/letta-ai/letta)                          |
| **AutoGen**               | 多 agent 协作、消息传递，包含本地和分布式 runtime       | 是相关候选；但当前已进入维护模式，官方建议新项目使用 Microsoft Agent Framework。[官方仓库](https://github.com/microsoft/autogen)      |
| **SWE-agent**             | 让模型浏览、修改、执行代码，解决软件工程任务                 | 更适合帮助开发项目；原项目目前推荐使用 mini-swe-agent。[官方文档](https://swe-agent.com/latest/)                               |
| **OpenHands**             | 软件开发 agent，以及代码工具、工作空间、远程执行服务          | 如果任务需要 agent 写代码、跑程序，它很相关；我的判断是它对网络资源协调的针对性较弱。[官方文档](https://docs.openhands.dev/overview/introduction) |
| **Academy**               | 有状态 agent、自主循环、远程动作调用，以及跨分布式研究设施的部署和通信 | **与 SciNet 的跨机构协调需求直接相关，值得重点考虑。** [官方说明](https://academy-agents.org/)                                  |


比如，你希望一个 telemetry agent **一直运行，每隔一段时间检查网络，并向另一个站点的 scheduling agent 报告变化**。这既包含“执行流程”，也包含“常驻服务、远程通信、生命周期管理”。Academy 对后面这些事情提供了专门的抽象，而它的 agent 可以完全由规则代码组成，无需 LLM。

**Academy 和 LangGraph 可以组合使用。** DOE 的框架选择指南也明确把 Academy 定位为分布式运行与协调的 middleware，并与 LangGraph 等框架区分开来。[DOE 指南](https://gear.doe.gov/gm-performers/ai-and-agents/choosing-an-agentic-framework)

一种可考虑的分工是：

```
Academy：agent 在哪里运行、如何远程调用和协调
    └─ LangGraph：每个 agent 内部的步骤、状态和分支
         └─ 普通 Python 规则 / 网络 API / 必要的 LLM 调用
```

这是一种设计建议，尚不能据此认定 SciNet 已采用这套组合。

**2. Lang 家族支持跨站点通信，并非只能在本地进程内运行。**

需要区分“本地编排”和“远程服务”：

- **本地** `StateGraph`：把函数添加为节点，不会自动把它部署到另一台机器。
- **远程调用**：把图部署成服务后，另一台机器可以通过网络调用它。

目前官方提供的相关接口包括：

**①** `RemoteGraph`**：调用另一个部署上的 LangGraph。**

它提供类似本地图的 `invoke()`、`stream()` 等接口，还能作为外层图的节点。因此，UCR 的 scheduling agent 可以调用部署在另一站点的 network agent。[官方文档](https://docs.langchain.com/langsmith/use-remote-graph)

例如，假设远端 Agent Server、鉴权及输入格式已配置好：

```
from langgraph.pregel.remote import RemoteGraph

network_agent = RemoteGraph(
    "network_agent",
    url="https://site-b.example.org",
)

result = network_agent.invoke({
    "link_id": "link-A",
    "requested_mbps": 300,
})
```

这里实际执行的是站点 B 的图；输入字段需要与你们定义的远端图一致。

**② A2A：与采用不同框架的远程 agent 通信。**

Lang 家族的 Agent Server 已提供 `/a2a/{assistant_id}` 接口，支持与其他 A2A-compatible agents 交互；具体支持哪些方法，要按服务版本核对。[官方文档](https://docs.langchain.com/langsmith/server-a2a)

所以，**“LangGraph 能跨站点调用”成立，但不等于“它自动解决了 SciNet 的跨站点协调”。** 请求里的容量单位、预留期限、任务状态，以及超时后是否允许重试，都需要项目定义；通信协议不会替你们决定这些业务规则。

我现在会把建议调整为：**LangGraph 适合作为 network agent 的内部流程底座；跨站点运行与协调应同时认真考察 Academy，优先确认合作方准备共享的框架是否已经包含这一层。**

---

> - LangGraph既然能做跨站点Agent通信了，为什么还需要Academy？
> - 你提到**LangGraph 能跨站点调用，但是这似乎不是两个agent直接对话？是否需要两个agent直接对话？**

**不一定需要 Academy。LangGraph 配合远程服务可以实现 agent 间协作；调用 API 本身也可以是“两个 agent 对话”的实现方式。** 我之前把二者的区别讲得过于绝对了。

**1. 有了 LangGraph，Academy 还能提供什么？**

首先要公平比较：LangGraph 的核心库主要处理执行流程，但 Lang 家族的 **Agent Server** 还提供持久化、任务队列、后台执行和定时任务。因此，不能说这些功能必须靠 Academy 补齐。[Agent Server 官方文档](https://docs.langchain.com/langsmith/agent-server)

两者更主要的区别是组织系统的方式：


| 方案                           | 编程时主要围绕什么组织                                    |
| ---------------------------- | ---------------------------------------------- |
| **LangGraph + Agent Server** | 图、执行步骤、一次次运行，以及跨运行保存的状态                        |
| **Academy**                  | 持有自身状态的 agent 对象、可远程调用的方法、自主循环，以及 agent 的启动和管理 |


Academy 提供 `@action` 暴露远程动作、`@loop` 定义自主循环，通过 handle、mailbox 和 exchange 完成异步通信，并通过 executor 管理不同资源上的执行。[Academy 官方文档](https://docs.academy-agents.org/main/)

例如，一个 telemetry agent 需要：

- 持续监测链路，维护自己的观测状态；
- 接受其他 agent 的查询；
- 发现异常后主动通知 scheduling agent。

Academy 给这些行为提供了一套现成的组织方式。使用 LangGraph 及其服务部署能力也可以构建这套系统，只是代码如何组织、哪些设施需要另外接入，会有所不同。

**所以，Academy 的价值是它提供的分布式 agent 抽象是否能减少你们的工程工作。跨站点通信本身，不构成必须引入它的理由。** 如果现有 Lang 家族方案已经覆盖需求，就可以先用它；也不必为了“分层完整”同时引入两个框架。

**2. 远程调用是否算两个 agent 直接对话？**

**可以算。要区分“谁在交流”和“消息如何传输”。**

假设站点 A 的 scheduling agent 调用站点 B 的 network agent：

```
Scheduling agent → Network agent：
请求在 14:00—14:30 预留 10 Gbps

Network agent → Scheduling agent：
该时段只能提供 6 Gbps；14:30 后可以提供 10 Gbps

Scheduling agent → Network agent：
任务允许延后，改为 14:30 开始

Network agent → Scheduling agent：
预留成功，reservation_id = R123
```



这是两个 agent 进行多轮协商。底层完全可以是几次 HTTP/API 调用，消息也可以全部使用 JSON。**双方都可以通过规则代码决定下一步，无需两个 LLM 用自然语言聊天。**

我之前的 `RemoteGraph.invoke()` 示例只展示了一次请求和响应。把远端图接入调用方的决策流程后，调用方可以根据返回结果再次发起请求，形成上面的多轮交互。官方支持把 `RemoteGraph` 作为另一个图中的节点。[RemoteGraph 官方文档](https://docs.langchain.com/langsmith/use-remote-graph)

“直接”还可能有两种含义：

- **逻辑上直接交流**：A 向 B 提请求，B 自己处理并答复。API 调用可以满足。
- **传输上没有中间服务**：消息必须点对点送达。通常没有必要；Academy 自己也使用 exchange/mailbox 等通信设施。

A2A 则给不同框架实现的 agent 提供统一的通信协议。它帮助双方理解任务和消息的格式；你们仍需定义“带宽请求”“备选方案”“预留确认”等项目语义。[A2A 官方说明](https://a2a-protocol.org/latest/topics/what-is-a2a/)

**对 SciNet，我建议先采用 scheduling agent 协调 network、telemetry 等 agent 的结构，使用明确的结构化消息；需要协商时允许多轮往返。** 当前没有必要要求所有 agent 两两连接，也没有必要先实现自由的 LLM 对话。

---

> langchain可以直接在我本地mac上开始用，即，能否直接在mac上开始搭建network agent

**可以。你完全可以直接在本地 Mac 上开始搭建 network agent，不必先申请 NRP 或 GPU 服务器。** Agent 运行在哪里，与它管理哪个站点的网络资源，可以分开。

LangChain/LangGraph 的 Python 代码可以在 Mac 上运行。LangChain 当前要求 Python 3.10+。[官方安装说明](https://docs.langchain.com/oss/python/langchain/install)

你可以在 Mac 上完成这些部分：


| 部分           | 本地怎么做                                 |
| ------------ | ------------------------------------- |
| **Agent 流程** | 用 LangGraph 定义节点、分支和 state            |
| **规则逻辑**     | 实现容量判断、请求校验、备选方案选择                    |
| **数据记录**     | 用 SQLite 保存模拟容量和预留记录                  |
| **网络工具**     | 先使用模拟接口，再接真实 telemetry / 网络 API       |
| **LLM**      | 调用远程模型服务；也可以用 Ollama 在 Mac 上运行合适大小的模型 |


Ollama 支持 macOS，Apple Silicon 可以使用其 CPU/GPU；本地能运行多大的模型取决于内存。[官方要求](https://docs.ollama.com/macos)

一种可行的开发结构是：

```
你的 Mac
  network agent
  ├─ LangGraph 流程
  ├─ 容量与预留规则
  ├─ 本地数据库
  └─ API 客户端
          ↓ 网络调用
  模拟服务 / Linux 上的 Mininet / 合作方网络服务
```

**需要单独考虑的是网络实验环境。** 如果要用 Mininet 模拟主机、交换机和链路，应把它放在 Linux 虚拟机或远程 Linux 服务器上；Mac 上的 agent 通过接口控制它。Mininet 官方也推荐使用 Ubuntu 虚拟机起步。[官方说明](https://mininet.org/download/)

**我建议第一版就在 Mac 上完成“接收带宽请求 → 查询模拟容量 → 按规则判断 → 记录预留 → 返回结果”这个闭环。** 这一步可以完全不调用 LLM；之后再接入真实网络环境和需要 LLM 的节点。

---

> deep agents我们需要用吗

**目前第一版 network agent，我建议先不用 Deep Agents。** 等出现需要自主拆解、长时间调查的任务，再考虑加入。

Deep Agents 是 Lang 家族更高层的 **agent harness**：基于 LangChain 的组件和 LangGraph 的运行机制，提供文件工具、上下文压缩、记忆、子 agent 委派，以及可选的任务规划等能力。[官方介绍](https://docs.langchain.com/oss/python/deepagents/overview)

它比较适合这样的任务：“调查为什么昨天跨站点传输变慢：读取多份日志和配置，查询不同站点的 telemetry，组织调查步骤，最后形成报告。”

这里调查路径事先不完全明确，需要 LLM 决定接下来查什么，还可能产生大量中间信息。Deep Agents 提供的能力就有用。

但你们当前讨论的第一版流程是：

```
接收带宽请求
    ↓
查询容量
    ↓
按规则判断
    ↓
预留或返回备选方案
```

**普通 LangGraph 就足以组织这个流程。** 容量计算、并发预留、接口格式等关键工作，仍需要你们自己实现；Deep Agents 不会自动提供这些网络功能。

可以按需求选择：


| 需求                    | 我的建议                          |
| --------------------- | ----------------------------- |
| 明确的规则流程、状态和分支         | LangGraph                     |
| 某个步骤需要 LLM 自主选择工具     | 按需使用 LangChain `create_agent` |
| 开放式调查、文件处理、长上下文和子任务委派 | 考虑 Deep Agents                |


**有多个 network、scheduling、telemetry agents，也不意味着必须用 Deep Agents。** 它的子 agent 委派机制，与跨机构常驻 agents 的部署和协调，是不同的需求。

对 SciNet，未来可以把 Deep Agents 用在一个专门的“网络诊断助手”中；当前先把 network agent 的规则和 API 闭环做好。

---

> 当前项目用langchain/graph好，还是直接用开源的codex好？

**当前项目我更建议：用 LangGraph 编排 Network Agent，普通 Python 实现网络规则，LangChain 按需加入。Codex 可以作为诊断节点里的执行引擎。** 这是针对你们当前需求的工程判断。

这里将“直接用开源 Codex”理解为：把 Codex 的 agent harness 嵌入系统，让它读取 telemetry、调用工具并决定下一步。

先澄清一点：**Codex 确实可以承担这种角色。** 它提供上下文管理、工具调用、执行循环和会话能力，可以通过 SDK 或 app-server 集成进自己的应用，并不限于交互式写代码。[OpenAI 官方说明](https://developers.openai.com/blog/codex-as-a-platform)

两者对你们项目的主要区别是：


| 当前需求                                  | 我的选择及理由                                         |
| ------------------------------------- | ----------------------------------------------- |
| quote → reserve → commit，失败后 rollback | **LangGraph + Python**：明确规定执行顺序、条件和状态转换         |
| 容量扣减、TTL、并发预留、重复请求处理                  | **独立的 Python 服务和存储**：两种框架都需要你们实现这些语义            |
| 分析日志，决定查哪个指标、做哪个 probe                | **Codex 或 LangChain agent 都适合**：可以让模型根据工具反馈组织调查 |
| 比较规则与 AI，验证 AI 带来的收益                  | **LangGraph 更方便组织对照**：保持外层流程一致，只替换某个决策节点        |


LangGraph 官方定位就包括在同一张图里混合确定性代码和 LLM 决策，而且可以独立于 LangChain 使用。[LangGraph 文档](https://docs.langchain.com/oss/python/langgraph/overview)

你们尤其需要回答 KK 的问题：**AI 究竟在哪一步增加了价值？** 用明确的外层流程，可以把这个问题落实到具体节点。例如：

```
检测到 deadline 风险
  → 调查原因：规则策略 / LLM agent / Codex
  → 返回诊断、证据和建议
  → Python 检查方案是否可行
  → 执行修复或报告 at_risk
```

这样，Codex 仍然可以自主查询 telemetry、分析日志、选择下一步探测；容量修改和 commitment 状态转换则通过明确的接口执行。若直接把整个流程交给 Codex，你们仍要补上这些接口、事务规则和状态管理。

**如果研究重心收敛成“开放式根因调查”，Codex 会是很值得优先尝试的底座；按现在 planning、runtime、learning 三张图的范围，我会先选 LangGraph。** LangChain 只在需要模型接入和工具调用循环时使用，不必整套引入。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/overview)

具体下一步：先把现有图中的 `diagnose / probe planning` 留成可替换接口，外层按 LangGraph 实现，后续就能接入 Codex，而不用重写网络控制逻辑。

