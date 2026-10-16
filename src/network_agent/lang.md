# Example of LangChain

- **LangChain** provides model integrations, tools, and a ready-to-use agent loop.

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama

@tool
def check_capacity(link_id: str, requested_mbps: float) -> dict:
    """Check whether the specified link can accommodate an additional bandwidth request, in Mbps."""

    # Demo: capacity records for the same reservation window
    records = {
        "link-A": {"capacity_mbps": 1000, "reserved_mbps": 800}
    }
    link = records[link_id]

    # Deterministic rule: calculate capacity in Python rather than asking the LLM to estimate it
    available = link["capacity_mbps"] - link["reserved_mbps"]
    return {
        "available_mbps": available,
        "can_allocate": 0 < requested_mbps <= available
    }

agent = create_agent(
    model=ChatOllama(model="gpt-oss:20b", temperature=0),
    tools=[check_capacity],
    system_prompt=(
        "Call the tool before answering capacity questions. "
        "Base your answer on the tool's output; do not guess the capacity."
    ),
)

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Can link-A accommodate an additional 300 Mbps?"
    }]
})

print(result["messages"][-1].content)
```

Expected execution flow:

```
User asks: Can link-A accommodate an additional 300 Mbps?
    ↓
The model requests a tool call:
check_capacity(link_id="link-A", requested_mbps=300)
    ↓
LangChain executes the Python function:
Returns available_mbps=200, can_allocate=False
    ↓
LangChain passes the result back to the model
    ↓
The model answers: Only 200 Mbps is available in this time window,
so the additional 300 Mbps request cannot be accommodated.
```



# Example of LangGraph

- **LangGraph** provides lower-level workflow orchestration, allowing to define execution order, branches, loops, and state.
- Its three core concepts are:

  | Concept   | Meaning                             |
  | --------- | ----------------------------------- |
  | **State** | Data shared across workflow steps   |
  | **Node**  | A function that performs one step   |
  | **Edge**  | Determines which node executes next |


```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# Data shared across workflow steps
class State(TypedDict, total=False):
    requested_mbps: int
    available_mbps: int
    decision: str

# Node: query available capacity
def read_capacity(state):
    # Demo data; a real implementation would query capacity records for the specified link and time window
    return {"available_mbps": 200}

# Branching rule: evaluated entirely in Python
def choose_next(state):
    if 0 < state["requested_mbps"] <= state["available_mbps"]:
        return "accept"
    return "reject"

# Nodes: record the decision without making an actual resource reservation
def accept(state):
    return {"decision": "accepted"}

def reject(state):
    return {"decision": "rejected"}

# Connect the nodes to build the workflow graph
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
print(result["decision"])  # Prints "rejected" under the rules above
```

