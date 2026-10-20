"""SENSE 接口:network agent 往下只通过 ``SenseAdapter`` 配置网络(slide 8)。

slide 8 把这里叫做 swap point:背后是真实 SENSE-O、NDT 还是 Mininet,上面的图都不用改。
采用 SENSE 的两阶段流程(workflow_phased):

    propagate  预留资源,不下发配置          ← reserve(slides 中的 hold)
    commit     下发配置,失败则 SENSE 回滚    ← commit
    cancel     归还资源                    ← release / reserve 到期
    (modify 在第 5b 步加)

调用失败一律抛 ``SenseError``;图 A 的 sense_call 节点据此走 rollback 分支。
"""

from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from typing import Literal, Protocol

from .ledger import EPS_GBPS
from .schemas import ServiceIntent, ServiceState
from .sim import MockNetwork

Op = Literal["propagate", "commit", "cancel"]


class SenseError(Exception):
    def __init__(self, op: Op, reason: Literal["insufficient_capacity", "invalid_state", "not_found",
                                                "no_vlan", "injected"], detail: str = ""):
        self.op, self.reason = op, reason
        super().__init__(f"{op} failed: {reason} {detail}".rstrip())


class SenseAdapter(Protocol):
    def propagate(self, intent: ServiceIntent, now: datetime) -> ServiceState: ...
    def commit(self, instance_id: str, now: datetime) -> ServiceState: ...
    def cancel(self, instance_id: str, now: datetime) -> ServiceState: ...
    def state(self, instance_id: str) -> ServiceState: ...


@dataclass
class MockSense:
    """对照 MockNetwork 的真实容量做准入;可以人为注入失败,用来测试 rollback。"""

    network: MockNetwork
    vlan_range: tuple[int, int]                       # VLAN 池 [first, last]
    _states: dict[str, ServiceState] = field(init=False, default_factory=dict)
    _fail: dict[str, int] = field(init=False, default_factory=dict)
    _ids: count = field(init=False, default_factory=lambda: count(1))

    def fail_next(self, op: Op, times: int = 1) -> None:
        """接下来 times 次 op 调用直接失败(模拟 SENSE 或设备侧出错)。"""
        self._fail[op] = self._fail.get(op, 0) + times

    def propagate(self, intent: ServiceIntent, now: datetime) -> ServiceState:
        self._maybe_fail("propagate")
        gbps = intent.capacity_mbps / 1000
        room = self.network.headroom(tuple(intent.path_inclusion), intent.start, intent.end)
        if gbps > room + EPS_GBPS:
            raise SenseError("propagate", "insufficient_capacity", f"need {gbps} Gbps, headroom {room}")
        vlan = self._free_vlan()
        instance_id = f"si-{next(self._ids)}"
        self.network.add_ours(instance_id, tuple(intent.path_inclusion), intent.start, intent.end, gbps)
        return self._set(ServiceState(instance_id=instance_id, alias=intent.alias, state="reserved",
                                      vlan=vlan, changed_at=now))

    def commit(self, instance_id: str, now: datetime) -> ServiceState:
        s = self._expect("commit", instance_id, "reserved")
        self._maybe_fail("commit")
        return self._set(s.model_copy(update={"state": "committed", "changed_at": now}))

    def cancel(self, instance_id: str, now: datetime) -> ServiceState:
        s = self._expect("cancel", instance_id, "reserved", "committed")
        self._maybe_fail("cancel")
        self.network.remove_ours(instance_id)
        return self._set(s.model_copy(update={"state": "cancelled", "vlan": None, "changed_at": now}))

    def state(self, instance_id: str) -> ServiceState:
        return self._states[instance_id]

    # ── 内部 ──────────────────────────────────────────────────────────────

    def _maybe_fail(self, op: Op) -> None:
        if self._fail.get(op, 0) > 0:
            self._fail[op] -= 1
            raise SenseError(op, "injected")

    def _expect(self, op: Op, instance_id: str, *allowed: str) -> ServiceState:
        s = self._states.get(instance_id)
        if s is None:
            raise SenseError(op, "not_found", instance_id)
        if s.state not in allowed:
            raise SenseError(op, "invalid_state", f"{instance_id} is {s.state}")
        return s

    def _free_vlan(self) -> int:
        used = {s.vlan for s in self._states.values() if s.vlan is not None}
        first, last = self.vlan_range
        for v in range(first, last + 1):
            if v not in used:
                return v
        raise SenseError("propagate", "no_vlan", f"pool {first}-{last} exhausted")

    def _set(self, s: ServiceState) -> ServiceState:
        self._states[s.instance_id] = s
        return s
