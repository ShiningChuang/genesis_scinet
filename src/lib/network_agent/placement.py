"""报价的放置搜索:在账本上为一条传输,沿一条路径找 (开始时间, 恒定速率) 方案(slide 7、slide 19 P1)。

只读账本,不写;不调用 SENSE。第一版用三条规则,各产出一个方案(以后可换成可替换的 policy):

    earliest_start  最早能开始的时刻,用从那时起能维持的最大速率      → slide 7 的 a1
    max_rate        整个窗口内能达到的最高速率,取最早能达到它的时刻  → a2
    min_rate        从最早时刻起,刚好赶上 latest_finish 的最低速率   → a3

三条规则代表 slide 7 说的取舍:早开始、短占用、少占容量。network agent 只列出,不替
scheduling agent 选。速率按 rate_step_gbps 取整。容量检查和 ledger.pending 用同一套槽换算,
所以报得出的方案在 reserve 时一定订得上(前提是期间账本没变)。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from .ledger import EPS_GBPS, CapacityLedger
from .schemas import RejectReason, TransferRequest
from .topology import Path

BITS_PER_BYTE = 8
BITS_PER_GBIT = 1e9

Strategy = Literal["earliest_start", "max_rate", "min_rate"]
BlockedBy = Literal["own_commitment", "foreign_traffic"]


@dataclass(frozen=True)
class Placement:
    transfer_id: str
    path: Path
    start: datetime
    end: datetime
    gbps: float
    strategy: Strategy
    blocked_by: BlockedBy | None    # 速率没能更高,是被我们自己的预订挡住,还是被外部流量挡住


def dedupe(placements: list[Placement]) -> list[Placement]:
    """开始时间和速率都相同的方案,对 scheduling agent 来说没有区别(它看不到路径):只保留先出现的。"""
    seen, out = set(), []
    for p in placements:
        if (p.start, p.gbps) not in seen:
            seen.add((p.start, p.gbps))
            out.append(p)
    return out


def duration(nbytes: int, gbps: float) -> timedelta:
    return timedelta(seconds=nbytes * BITS_PER_BYTE / (gbps * BITS_PER_GBIT))


def _fits(ledger: CapacityLedger, path: Path, start: datetime, end: datetime, gbps: float,
          ignore_own: bool = False) -> bool:
    """[start, end) 碰到的每个槽,路径都能给出 gbps。ignore_own=True 时假装我们自己一笔预订都没有。"""
    for i in ledger.slots_covering(start, end):
        if ignore_own:
            room = min(ledger.observed(link, i).gbps for link in path)
        else:
            room, _ = ledger.path_available(path, i)
        if room + EPS_GBPS < gbps:
            return False
    return True


def _max_rate_at(ledger: CapacityLedger, path: Path, nbytes: int, start: datetime, deadline: datetime,
                 rates: list[float], ignore_own: bool = False) -> float | None:
    """从 start 开始、在 deadline 前传完,能维持的最大速率;一档都不行返回 None。"""
    for r in reversed(rates):
        end = start + duration(nbytes, r)
        if end <= deadline and _fits(ledger, path, start, end, r, ignore_own):
            return r
    return None


def search(ledger: CapacityLedger, path: Path, req: TransferRequest, now: datetime,
           rate_step: float) -> list[Placement] | RejectReason:
    earliest = max(req.window.earliest_start, now, ledger.origin)
    deadline = min(req.window.latest_finish, ledger.horizon_end)
    if earliest >= ledger.horizon_end:
        return RejectReason(cause="beyond_horizon", detail=f"window starts after ledger horizon {ledger.horizon_end}")
    if earliest >= deadline:
        return RejectReason(cause="no_capacity", detail="window has already passed")

    cap = min(ledger.topology.links[link].capacity_gbps for link in path)
    rates = [k * rate_step for k in range(1, int(cap // rate_step) + 1)]
    starts = [earliest] + [ledger.slot_start(i) for i in ledger.slots_covering(earliest, deadline)
                           if ledger.slot_start(i) > earliest]
    best = {s: r for s in starts if (r := _max_rate_at(ledger, path, req.bytes, s, deadline, rates))}
    if not best:
        return RejectReason(cause="no_capacity", detail="no start time in the window has enough room")

    def blocked(start: datetime, gbps: float) -> BlockedBy | None:
        if gbps >= rates[-1]:
            return None                     # 已经是这条路径的最高档,没被挡
        free = _max_rate_at(ledger, path, req.bytes, start, deadline, rates, ignore_own=True)
        return "own_commitment" if free and free > gbps else "foreign_traffic"

    def make(start: datetime, gbps: float, strategy: Strategy, b: BlockedBy | None) -> Placement:
        return Placement(req.id, path, start, start + duration(req.bytes, gbps), gbps, strategy, b)

    s1 = min(best)
    top = max(best.values())
    s2 = min(s for s, r in best.items() if r == top)
    r3 = next(r for r in rates if r <= best[s1] and s1 + duration(req.bytes, r) <= deadline
              and _fits(ledger, path, s1, s1 + duration(req.bytes, r), r))
    found = [make(s1, best[s1], "earliest_start", blocked(s1, best[s1])),
             make(s2, top, "max_rate", blocked(s2, top)),
             make(s1, r3, "min_rate", None)]          # 低速是主动选的,不算被挡

    unique = dedupe(found)
    if req.min_useful_rate_gbps is not None:
        useful = [p for p in unique if p.gbps + EPS_GBPS >= req.min_useful_rate_gbps]
        if not useful:
            return RejectReason(cause="below_min_useful_rate",
                                detail=f"best rate {top} Gbps < min useful {req.min_useful_rate_gbps}")
        unique = useful
    return unique
