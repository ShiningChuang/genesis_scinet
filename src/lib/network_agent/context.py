"""Runtime environment shared by the three graphs (the LangGraph runtime context).

A graph's state only records the work of "this one execution". Long-lived objects shared by all
requests — the ledger, the topology, external interfaces — live in the context instead: the caller
builds it once and passes it on every invoke (by design, the ledger stays out of state).
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
    offer_book: dict[str, Placement] = field(default_factory=dict)  # offer_id → placement; reserve (step 5a) looks the path up by id
