"""模拟网络:digital twin 的替身,用来在没有 Mininet / VIT / SENSE 时驱动 agent。

它持有"真实情况":拓扑、他人占用的容量(按时段)、链路中断(按时段),
以及我们经 SENSE 预留的容量。mock telemetry(第 3a 步)从这里读,
mock SENSE(第 3b 步)读写这里,两者看到的是同一个网络。以后换成 Mininet 时,替换的就是这一层。

"他人占用"和"我们的预留"分开存:SENSE 做准入检查时两者都要算;
telemetry 报告时只算他人(口径见 schemas.LinkSample),我们的预留由账本的 own 负责。
"""

from dataclasses import dataclass, field
from datetime import datetime

from .topology import Path, Topology


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    gbps: float = 0.0


@dataclass
class MockNetwork:
    topology: Topology
    _foreign: dict[str, list[Interval]] = field(init=False)  # 有向链路 → 他人占用
    _outages: dict[str, list[Interval]] = field(init=False)  # 有向链路 → 中断时段
    _ours: dict[str, tuple[Path, Interval]] = field(init=False, default_factory=dict)  # SENSE 实例 → (路径, 预留)

    def __post_init__(self):
        self._foreign = {link: [] for link in self.topology.links}
        self._outages = {link: [] for link in self.topology.links}

    def add_foreign(self, link_id: str, start: datetime, end: datetime, gbps: float) -> None:
        """他人在 [start, end) 占用某个方向 gbps 的容量。"""
        self._foreign[link_id].append(Interval(start, end, gbps))

    def add_outage(self, physical_link_id: str, start: datetime, end: datetime) -> None:
        """物理链路中断(如光纤被挖断),两个方向同时不可用。"""
        directed = [d.id for d in self.topology.links.values() if d.link_id == physical_link_id]
        if not directed:
            raise KeyError(f"unknown link {physical_link_id!r}")
        for link in directed:
            self._outages[link].append(Interval(start, end))

    def add_ours(self, instance_id: str, path: Path, start: datetime, end: datetime, gbps: float) -> None:
        """我们经 SENSE 预留的容量(mock SENSE 在 propagate 时调用)。"""
        self._ours[instance_id] = (path, Interval(start, end, gbps))

    def remove_ours(self, instance_id: str) -> None:
        del self._ours[instance_id]

    def segments(self, link_id: str, start: datetime, end: datetime,
                 include_ours: bool = False) -> list[tuple[datetime, datetime, bool, float]]:
        """把 [start, end) 切成"状态不变"的若干段,每段给出 (起, 止, 是否 up, 可用容量)。

        include_ours=False(telemetry 口径):可用容量 = 容量 − 他人占用。
        include_ours=True (SENSE 准入口径):再减去我们经 SENSE 的预留。
        """
        cap = self.topology.links[link_id].capacity_gbps
        used = list(self._foreign[link_id])
        if include_ours:
            used += [iv for path, iv in self._ours.values() if link_id in path]
        events = used + self._outages[link_id]
        cuts = sorted({start, end} | {t for iv in events for t in (iv.start, iv.end) if start < t < end})
        out = []
        for a, b in zip(cuts, cuts[1:]):
            up = not any(iv.start < b and a < iv.end for iv in self._outages[link_id])
            taken = sum(iv.gbps for iv in used if iv.start < b and a < iv.end)
            out.append((a, b, up, max(0.0, cap - taken) if up else 0.0))
        return out

    def headroom(self, path: Path, start: datetime, end: datetime) -> float:
        """SENSE 准入用:整条路径在 [start, end) 内任一时刻都还能再给出的最大速率。"""
        return min(gbps for link in path for *_, gbps in self.segments(link, start, end, include_ours=True))
