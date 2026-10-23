"""Step 2:拓扑与容量账本。"""

import pytest
from pydantic import ValidationError

from ..config import load_config
from ..ledger import CapacityLedger, InsufficientCapacity, OutOfHorizon
from ..schemas import LinkSample, RateSegment
from ..topology import Topology
from .helpers import ALT, CFG, DST, L1, L2, L4, MAIN, SRC, TOPO, t


@pytest.fixture
def topo():
    return Topology.from_dict(TOPO)


@pytest.fixture
def ledger(topo):
    return CapacityLedger(topo, load_config(CFG), origin=t(9, 5))  # 09:05 → 对齐到 09:00


def seg(h0, m0, h1, m1, gbps):
    return [RateSegment(start=t(h0, m0), end=t(h1, m1), gbps=gbps)]


# ── 拓扑 ──────────────────────────────────────────────────────────────────

def test_paths_shortest_first(topo):
    assert topo.paths(SRC, DST, k=3) == [MAIN, ALT]
    assert topo.paths(SRC, DST, k=1) == [MAIN]


def test_links_are_directed(topo):
    back = topo.paths(DST, SRC, k=1)[0]
    assert back[0] == "L3:ornl-n01>esnet-chi"


def test_unknown_node(topo):
    with pytest.raises(KeyError):
        topo.paths(SRC, "nowhere", k=1)


@pytest.mark.parametrize("bad", [
    {**TOPO, "links": TOPO["links"] + [{"id": "L9", "a": SRC, "b": "mars", "capacity_gbps": 1}]},
    {**TOPO, "links": TOPO["links"] + [TOPO["links"][0]]},                     # 重复链路 id
    {**TOPO, "links": [{"id": "L9", "a": "esnet-chi", "b": "esnet-chi", "capacity_gbps": 1}]},
])
def test_bad_topology(bad):
    with pytest.raises(ValidationError):
        Topology.from_dict(bad)


# ── 账本:时间槽 ───────────────────────────────────────────────────────────

def test_origin_aligned_and_horizon(ledger):
    assert ledger.origin == t(9)
    assert ledger.n_slots == 96
    assert ledger.horizon_end == t(9, day=21)


def test_partial_slot_counts_whole(ledger):
    """13:00–13:07 只用了 7 分钟,但占满 13:00 那一整个 15 分钟槽(量化误差)。"""
    assert list(ledger.slots_covering(t(13), t(13, 7))) == [16]
    assert list(ledger.slots_covering(t(12), t(13, 7))) == [12, 13, 14, 15, 16]


def test_out_of_horizon(ledger):
    with pytest.raises(OutOfHorizon):
        ledger.slots_covering(t(8), t(10))
    with pytest.raises(OutOfHorizon):
        ledger.pending("b", MAIN, [RateSegment(start=t(8, day=21), end=t(10, day=21), gbps=1)])


# ── 账本:observed / own / available ─────────────────────────────────────

def test_seeded_from_topology(ledger):
    o = ledger.observed(L2, 0)
    assert (o.gbps, o.source) == (100, "topology")
    assert ledger.available(L2, 0) == 100


def test_slide23_table(ledger):
    """复现 slide 23 的表:observed 100,100,100,40,40,40;own 40,40,0,0,25,25 → available 60,60,100,40,15,15。"""
    ledger.apply([LinkSample(link_id=L2, start=t(9, 45), end=t(10, 30), up=True, available_gbps=40,
                             sampled_at=t(9), valid_until=t(9, 10), source="sense")])
    ledger.pending("own-a", (L2,), seg(9, 0, 9, 30, 40))
    ledger.pending("own-b", (L2,), seg(10, 0, 10, 30, 25))
    slots = range(6)  # 09:00 … 10:15
    assert [ledger.observed(L2, i).gbps for i in slots] == [100, 100, 100, 40, 40, 40]
    assert [ledger.own(L2, i) for i in slots] == [40, 40, 0, 0, 25, 25]
    assert [ledger.available(L2, i) for i in slots] == [60, 60, 100, 40, 15, 15]
    assert ledger.observed(L2, 3).source == "sense"


def test_path_available_is_min_with_bottleneck(ledger):
    assert ledger.path_available(ALT, 0) == (40, L4)


def test_shared_link_couples_paths(ledger):
    """按链路记账的意义:MAIN 和 ALT 共用 L1,在 MAIN 上预订会挤占 ALT。"""
    ledger.pending("b1", MAIN, seg(9, 0, 10, 0, 80))
    assert ledger.path_available(ALT, 0) == (20, L1)


# ── 账本:pending → confirm / rollback / release ──────────────────────────

def test_pending_visible_immediately(ledger):
    ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 30))
    assert ledger.available(L2, 0) == 70
    assert ledger.booking("b1").state == "pending"


def test_confirm_then_release(ledger):
    ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 30))
    ledger.confirm("b1")
    assert ledger.available(L2, 0) == 70
    with pytest.raises(ValueError):
        ledger.rollback("b1")                     # 已转正,不能 rollback
    ledger.release("b1")
    assert ledger.available(L2, 0) == 100


def test_rollback_restores(ledger):
    ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 30))
    ledger.rollback("b1")
    assert ledger.available(L2, 0) == 100
    with pytest.raises(KeyError):
        ledger.confirm("b1")


def test_duplicate_booking_id(ledger):
    ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 30))
    with pytest.raises(ValueError):
        ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 30))


def test_insufficient_is_atomic_and_located(ledger):
    """ALT 第二跳 L4 只有 40;要 50 时失败,并指出是 L4、被外部容量限制;L1 上什么都没写。"""
    with pytest.raises(InsufficientCapacity) as e:
        ledger.pending("b1", ALT, seg(9, 0, 9, 30, 50))
    assert (e.value.link_id, e.value.blocked_by) == (L4, "foreign_traffic")
    assert ledger.available(ALT[0], 0) == 100


def test_blocked_by_own_commitment(ledger):
    ledger.pending("b1", MAIN, seg(9, 0, 9, 30, 70))
    with pytest.raises(InsufficientCapacity) as e:
        ledger.pending("b2", MAIN, seg(9, 0, 9, 30, 50))
    assert e.value.blocked_by == "own_commitment"   # 不算我们自己的 70,100 本来够 50
