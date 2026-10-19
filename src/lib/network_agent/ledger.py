"""容量账本:每条有向链路 × 每个时间槽,available = observed − own(slide 23)。

- observed:不算我们自己的预订时可用的容量(口径见 schemas.LinkSample)。初始为拓扑配置容量,
  之后由 ``apply()`` 写入 telemetry 样本;每个数都带来源、采样时间和过期时间
  (slide 12:"every number carries its source")。
- own:我们自己的预订之和。预订分两种状态:pending(reserve 时预扣)与 confirmed(commit 后)。
  pending 一写入就计入 own,下一次 quote 立刻能看到(slide 19)。

"accept 之后容量在哪里扣减":在 ``pending()``。失败时 ``rollback()`` 退回,
成功后 ``confirm()`` 转正,不再需要时 ``release()`` 归还。

时间槽:第 i 槽覆盖 [origin + i·slot, origin + (i+1)·slot)。一段预订只要碰到某个槽,
就按该段速率占满整个槽——这就是 slide 23 说的量化误差:槽越大,零头浪费越多。
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from .config import NetAgentConfig
from .schemas import LinkSample, RateSegment
from .topology import Path, Topology

EPS_GBPS = 1e-9  # 浮点比较容差,不是业务参数


class OutOfHorizon(ValueError):
    """时间落在账本覆盖范围之外(早于 origin 或晚于 horizon)。"""


class InsufficientCapacity(Exception):
    """某条链路的某个槽容量不够。带上是哪一跳、缺多少、被谁挡住,供 offer 的 blocked_by 和 runtime 定位拥塞用。"""

    def __init__(self, link_id: str, slot_start: datetime, need: float, available: float,
                 blocked_by: Literal["own_commitment", "foreign_traffic"]):
        self.link_id, self.slot_start, self.need, self.available, self.blocked_by = (
            link_id, slot_start, need, available, blocked_by)
        super().__init__(f"{link_id} @ {slot_start:%H:%M}: need {need} Gbps, available {available} ({blocked_by})")


@dataclass(frozen=True)
class Observation:
    gbps: float
    source: str           # "topology" | "sense" | "telemetry" | ...
    at: datetime          # 采样时间
    valid_until: datetime  # 过期时间;拓扑初值在 origin 即过期,第一次报价前就会被刷新


@dataclass
class Booking:
    id: str
    path: Path
    slot_gbps: dict[int, float]                     # 槽号 → 该槽占用速率
    state: Literal["pending", "confirmed"] = "pending"


@dataclass
class CapacityLedger:
    topology: Topology
    cfg: NetAgentConfig
    origin: datetime                                # 第 0 槽的开始;构造时对齐到槽边界
    _observed: dict[str, list[Observation]] = field(init=False)
    _bookings: dict[str, Booking] = field(init=False, default_factory=dict)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)

    def __post_init__(self):
        slot = self.cfg.slot_seconds
        epoch = self.origin.timestamp()
        self.origin = self.origin - timedelta(seconds=epoch % slot)  # 向下对齐到槽边界
        self._observed = {d.id: [Observation(d.capacity_gbps, "topology", self.origin, self.origin)] * self.n_slots
                          for d in self.topology.links.values()}

    # ── 时间槽 ────────────────────────────────────────────────────────────

    @property
    def n_slots(self) -> int:
        return self.cfg.horizon_seconds // self.cfg.slot_seconds

    @property
    def horizon_end(self) -> datetime:
        return self.slot_start(self.n_slots)

    def slot_start(self, i: int) -> datetime:
        return self.origin + timedelta(seconds=i * self.cfg.slot_seconds)

    def slots_covering(self, start: datetime, end: datetime) -> range:
        """与 [start, end) 有交集的所有槽号。"""
        if start < self.origin or end > self.horizon_end:
            raise OutOfHorizon(f"[{start}, {end}) outside ledger [{self.origin}, {self.horizon_end})")
        slot = self.cfg.slot_seconds
        first = int((start - self.origin).total_seconds() // slot)
        last = int(-(-(end - self.origin).total_seconds() // slot))  # 向上取整
        return range(first, last)

    # ── 读 ────────────────────────────────────────────────────────────────

    def observed(self, link_id: str, i: int) -> Observation:
        return self._observed[link_id][i]

    def own(self, link_id: str, i: int) -> float:
        return sum(b.slot_gbps.get(i, 0.0) for b in self._bookings.values() if link_id in b.path)

    def available(self, link_id: str, i: int) -> float:
        return max(0.0, self.observed(link_id, i).gbps - self.own(link_id, i))

    def path_available(self, path: Path, i: int) -> tuple[float, str]:
        """路径在第 i 槽的可用容量 = 沿途各链路的最小值;同时返回瓶颈是哪一跳。"""
        return min((self.available(link, i), link) for link in path)

    def is_stale(self, link_id: str, i: int, now: datetime) -> bool:
        return self.observed(link_id, i).valid_until <= now

    def booking(self, booking_id: str) -> Booking:
        return self._bookings[booking_id]

    # ── 写 ────────────────────────────────────────────────────────────────

    def apply(self, samples: list[LinkSample]) -> None:
        """把一批 telemetry 样本写进 observed。样本超出账本范围的部分裁掉。

        一个槽若被同一批里的多个样本覆盖(样本边界落在槽中间),取最小值:
        槽内任一时刻的可用容量都不应被高估。
        """
        per_slot: dict[tuple[str, int], Observation] = {}
        for s in samples:
            start, end = max(s.start, self.origin), min(s.end, self.horizon_end)
            if start >= end:
                continue
            obs = Observation(s.available_gbps, s.source, s.sampled_at, s.valid_until)
            for i in self.slots_covering(start, end):
                prev = per_slot.get((s.link_id, i))
                if prev is None or obs.gbps < prev.gbps:
                    per_slot[(s.link_id, i)] = obs
        with self._lock:
            for (link_id, i), obs in per_slot.items():
                self._observed[link_id][i] = obs

    def pending(self, booking_id: str, path: Path, profile: list[RateSegment]) -> None:
        """预扣:先检查沿途每条链路每个槽都够,全部够了才写入;任何一处不够就什么都不写。"""
        slot_gbps: dict[int, float] = {}
        for seg in profile:
            for i in self.slots_covering(seg.start, seg.end):
                slot_gbps[i] = max(slot_gbps.get(i, 0.0), seg.gbps)  # 同一预订的相邻段落在同一槽:取大者,不重复计
        with self._lock:
            if booking_id in self._bookings:
                raise ValueError(f"booking {booking_id!r} already exists")
            for link in path:
                for i, need in slot_gbps.items():
                    avail = self.available(link, i)
                    if need > avail + EPS_GBPS:
                        # 若不算我们自己的预订就够 → 被自己的承诺挡住;否则是外部流量
                        blocked = "own_commitment" if self.observed(link, i).gbps + EPS_GBPS >= need else "foreign_traffic"
                        raise InsufficientCapacity(link, self.slot_start(i), need, avail, blocked)
            self._bookings[booking_id] = Booking(booking_id, path, slot_gbps)

    def confirm(self, booking_id: str) -> None:
        with self._lock:
            b = self._require(booking_id, "pending")
            b.state = "confirmed"

    def rollback(self, booking_id: str) -> None:
        """撤销一笔 pending(例如 SENSE 调用失败)。已 confirmed 的要用 release。"""
        with self._lock:
            self._require(booking_id, "pending")
            del self._bookings[booking_id]

    def release(self, booking_id: str) -> None:
        with self._lock:
            self._require(booking_id, "confirmed")
            del self._bookings[booking_id]

    def _require(self, booking_id: str, state: str) -> Booking:
        b = self._bookings.get(booking_id)
        if b is None:
            raise KeyError(f"no booking {booking_id!r}")
        if b.state != state:
            raise ValueError(f"booking {booking_id!r} is {b.state}, expected {state}")
        return b
