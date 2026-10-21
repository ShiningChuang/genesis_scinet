"""三张图共用的运行环境(LangGraph runtime context)。

图的 state 只记"这一次执行"的工作记录;账本、拓扑、外部接口这些长期存在、所有请求共用的东西
放在 context 里,由调用方构造一次、每次 invoke 时传入(10/14 设计:ledger 不进 state)。
"""

from dataclasses import dataclass, field

from .config import NetAgentConfig
from .estimate import RateModel
from .ledger import CapacityLedger
from .placement import Placement
from .telemetry import TelemetrySource
from .topology import Topology


@dataclass
class AgentContext:
    cfg: NetAgentConfig
    topology: Topology
    ledger: CapacityLedger
    telemetry: TelemetrySource
    rate_model: RateModel
    offer_book: dict[str, Placement] = field(default_factory=dict)  # offer_id → 方案;第 5a 步 reserve 时按 id 取回路径
